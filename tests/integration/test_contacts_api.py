import os
os.environ["MAIL_USERNAME"] = "fake"
os.environ["MAIL_PASSWORD"] = "fake"
os.environ["MAIL_SERVER"] = "fake"
os.environ["MAIL_FROM"] = "fake@example.com"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["ALGORITHM"] = "HS256"

import pytest
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from unittest.mock import AsyncMock
import src.repository.users
src.repository.users.send_verification_email = AsyncMock()

import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from src.database.db import Base, get_db
from src.main import app

# Use a separate SQLite file-based DB for integration tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)

# Override FastAPI's get_db dependency to use the test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def verify_user_in_db(email):
    db = TestingSessionLocal()
    db.execute(text("UPDATE users SET is_verified = 1 WHERE email = :email"), {"email": email})
    db.commit()
    db.close()

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_db():
    # Clean all tables before each test, but do not delete the file!
    with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

@pytest_asyncio.fixture(scope="module")
async def transport_and_lifespan():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        yield transport

@pytest_asyncio.fixture(scope="module")
async def user_token(transport_and_lifespan):
    email = "apitestuser@example.com"
    password = "testpassword"
    async with AsyncClient(base_url="http://test", transport=transport_and_lifespan) as ac:
        await ac.post("/auth/register", json={"email": email, "password": password})

    verify_user_in_db(email)

    async with AsyncClient(base_url="http://test", transport=transport_and_lifespan) as ac:
        resp = await ac.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return token

async def test_create_contact_api(user_token, transport_and_lifespan):
    headers = {"Authorization": f"Bearer {user_token}"}
    contact_data = {
        "first_name": "API",
        "last_name": "Contact",
        "email": "apicontact@example.com",
        "phone": "1234567890",
        "birthday": "2000-01-01",
        "additional_data": "API test contact"
    }
    async with AsyncClient(base_url="http://test", transport=transport_and_lifespan) as ac:
        resp = await ac.post("/contacts/", json=contact_data, headers=headers)
    assert resp.status_code == 200 or resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "API"
    assert data["email"] == "apicontact@example.com"
    assert "id" in data

async def test_protected_route_no_token(transport_and_lifespan):
    async with AsyncClient(base_url="http://test", transport=transport_and_lifespan) as ac:
        resp = await ac.get("/contacts/")
    assert resp.status_code == 401 or resp.status_code == 403
