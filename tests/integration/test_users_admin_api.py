import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from src.main import app
from src.database.db import Base, get_db
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.schemas import UserCreate
import asyncio

# Use a separate SQLite file-based DB for integration tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_users_admin_api.db"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def verify_user_in_db(email, role=None):
    db = TestingSessionLocal()
    db.execute(text("UPDATE users SET is_verified = 1{} WHERE email = :email".format(
        ", role = 'admin'" if role == "admin" else ""
    )), {"email": email})
    db.commit()
    db.close()

@pytest.mark.asyncio
async def test_set_default_avatar_admin_and_user():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(base_url="http://test", transport=transport) as ac:
            # Register admin
            admin_email = "apitestadmin@example.com"
            admin_password = "adminpass"
            await ac.post("/auth/register", json={"email": admin_email, "password": admin_password})
            verify_user_in_db(admin_email, role="admin")
            # Login as admin
            resp = await ac.post("/auth/login", data={"username": admin_email, "password": admin_password})
            assert resp.status_code == 200
            admin_token = resp.json()["access_token"]
            # Try PATCH /auth/avatar/default as admin
            headers = {"Authorization": f"Bearer {admin_token}"}
            resp = await ac.patch("/auth/avatar/default", headers=headers)
            assert resp.status_code == 200
            assert "avatar_url" in resp.json()

            # Register user
            user_email = "apitestuser2@example.com"
            user_password = "userpass"
            await ac.post("/auth/register", json={"email": user_email, "password": user_password})
            verify_user_in_db(user_email)
            # Login as user
            resp = await ac.post("/auth/login", data={"username": user_email, "password": user_password})
            assert resp.status_code == 200
            user_token = resp.json()["access_token"]
            # Try PATCH /auth/avatar/default as user
            headers = {"Authorization": f"Bearer {user_token}"}
            resp = await ac.patch("/auth/avatar/default", headers=headers)
            assert resp.status_code == 403 or resp.status_code == 401

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_db():
    # Clean all tables before each test, but do not delete the file!
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
