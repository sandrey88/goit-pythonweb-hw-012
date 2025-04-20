import os
os.environ["MAIL_USERNAME"] = "fake"
os.environ["MAIL_PASSWORD"] = "fake"
os.environ["MAIL_SERVER"] = "fake"
os.environ["MAIL_FROM"] = "fake@example.com"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["ALGORITHM"] = "HS256"

import pytest
from unittest.mock import AsyncMock
import src.repository.users
src.repository.users.send_verification_email = AsyncMock()

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.main import app
from src.database.db import Base, get_db

# Use a separate SQLite file-based DB for integration tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables in the test DB
Base.metadata.create_all(bind=test_engine)

# Override FastAPI's get_db dependency to use the test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_db():
    yield
    if os.path.exists("./test_api.db"):
        os.remove("./test_api.db")

@pytest.fixture(scope="module")
def user_token():
    # Register user
    email = "apitestuser@example.com"
    password = "testpassword"
    client.post("/auth/register", json={"email": email, "password": password})

    # Верифікуємо користувача напряму у тестовій БД
    db = TestingSessionLocal()
    db.execute(text("UPDATE users SET is_verified = 1 WHERE email = :email"), {"email": email})
    db.commit()
    db.close()

    # Login
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return token

def test_create_contact_api(user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    contact_data = {
        "first_name": "API",
        "last_name": "Contact",
        "email": "apicontact@example.com",
        "phone": "1234567890",
        "birthday": "2000-01-01",
        "additional_data": "API test contact"
    }
    resp = client.post("/contacts/", json=contact_data, headers=headers)
    assert resp.status_code == 200 or resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "API"
    assert data["email"] == "apicontact@example.com"
    assert "id" in data

def test_get_contacts_api(user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = client.get("/contacts/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(c["email"] == "apicontact@example.com" for c in data)

def test_protected_route_no_token():
    resp = client.get("/contacts/")
    assert resp.status_code == 401 or resp.status_code == 403
