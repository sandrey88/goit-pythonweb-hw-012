"""

Налаштування та конфігурація тестів

Усередині директорії з тестами tests створіть файл conftest.py. Він використовується фреймворком pytest для налаштування та конфігурації тестів. Цей файл дозволяє задавати фікстури fixtures для тестів, які створюють і надають необхідні об'єкти та дані для їх виконання.

import asyncio

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from main import app
from src.database.models import Base, User
from src.database.db import get_db
from src.services.auth import create_access_token, Hash

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

test_user = {
    "username": "deadpool",
    "email": "deadpool@example.com",
    "password": "12345678",
}

@pytest.fixture(scope="module", autouse=True)
def init_models_wrap():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as session:
            hash_password = Hash().get_password_hash(test_user["password"])
            current_user = User(
                username=test_user["username"],
                email=test_user["email"],
                hashed_password=hash_password,
                confirmed=True,
                avatar="<https://twitter.com/gravatar>",
            )
            session.add(current_user)
            await session.commit()

    asyncio.run(init_models())

@pytest.fixture(scope="module")
def client():
    # Dependency override

    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception as err:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

@pytest_asyncio.fixture()
async def get_token():
    token = await create_access_token(data={"sub": test_user["username"]})
    return token

"""


"""
Тести для маршрутів автентифікації та авторизації
Створимо файл test_integration_auth.py для тестування функціональності процесів автентифікації вебзастосунку. 


from unittest.mock import Mock

import pytest
from sqlalchemy import select

from src.database.models import User
from tests.conftest import TestingSessionLocal

user_data = {"username": "agent007", "email": "agent007@gmail.com", "password": "12345678"}

def test_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.api.auth.send_email", mock_send_email)
    response = client.post("api/auth/register", json=user_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "hashed_password" not in data
    assert "avatar" in data

def test_repeat_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.api.auth.send_email", mock_send_email)
    response = client.post("api/auth/register", json=user_data)
    assert response.status_code == 409, response.text
    data = response.json()
    assert data["detail"] == "Користувач з таким email вже існує"

def test_not_confirmed_login(client):
    response = client.post("api/auth/login",
                           data={"username": user_data.get("username"), "password": user_data.get("password")})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Електронна адреса не підтверджена"

@pytest.mark.asyncio
async def test_login(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(select(User).where(User.email == user_data.get("email")))
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()

    response = client.post("api/auth/login",
                           data={"username": user_data.get("username"), "password": user_data.get("password")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data

def test_wrong_password_login(client):
    response = client.post("api/auth/login",
                           data={"username": user_data.get("username"), "password": "password"})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Неправильний логін або пароль"

def test_wrong_username_login(client):
    response = client.post("api/auth/login",
                           data={"username": "username", "password": user_data.get("password")})
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == "Неправильний логін або пароль"

def test_validation_error_login(client):
    response = client.post("api/auth/login",
                           data={"password": user_data.get("password")})
    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data



"""



"""
Тести для маршрутів роботи з тегами
def test_create_tag(client, get_token):
    response = client.post(
        "/api/tags",
        json={"name": "test_tag"},
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "test_tag"
    assert "id" in data

def test_get_tag(client, get_token):
    response = client.get(
        "/api/tags/1", headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "test_tag"
    assert "id" in data

def test_get_tag_not_found(client, get_token):
    response = client.get(
        "/api/tags/2", headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 404, response.text
    data = response.json()
    assert data["detail"] == "Tag not found"

def test_get_tags(client, get_token):
    response = client.get("/api/tags", headers={"Authorization": f"Bearer {get_token}"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["name"] == "test_tag"
    assert "id" in data[0]

def test_update_tag(client, get_token):
    response = client.put(
        "/api/tags/1",
        json={"name": "new_test_tag"},
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "new_test_tag"
    assert "id" in data

def test_update_tag_not_found(client, get_token):
    response = client.put(
        "/api/tags/2",
        json={"name": "new_test_tag"},
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 404, response.text
    data = response.json()
    assert data["detail"] == "Tag not found"

def test_delete_tag(client, get_token):
    response = client.delete(
        "/api/tags/1", headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "new_test_tag"
    assert "id" in data

def test_repeat_delete_tag(client, get_token):
    response = client.delete(
        "/api/tags/1", headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 404, response.text
    data = response.json()
    assert data["detail"] == "Tag not found"



"""

"""
Тести для маршрутів роботи з контактами

from unittest.mock import patch

from conftest import test_user

def test_get_me(client, get_token):
    token = get_token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("api/users/me", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "avatar" in data

@patch("src.services.upload_file.UploadFileService.upload_file")
def test_update_avatar_user(mock_upload_file, client, get_token):
    # Мокаємо відповідь від сервісу завантаження файлів
    fake_url = "<http://example.com/avatar.jpg>"
    mock_upload_file.return_value = fake_url

    # Токен для авторизації
    headers = {"Authorization": f"Bearer {get_token}"}

    # Файл, який буде відправлено
    file_data = {"file": ("avatar.jpg", b"fake image content", "image/jpeg")}

    # Відправка PATCH-запиту
    response = client.patch("/api/users/avatar", headers=headers, files=file_data)

    # Перевірка, що запит був успішним
    assert response.status_code == 200, response.text

    # Перевірка відповіді
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert data["avatar"] == fake_url

    # Перевірка виклику функції upload_file з об'єктом UploadFile
    mock_upload_file.assert_called_once()


"""



