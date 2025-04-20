import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.db import Base
from src.repository import users as users_repo
from src.schemas import UserCreate
from src.database.models import User

# Use in-memory SQLite for testing
test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=test_engine)


def test_create_user(db):
    user_in = UserCreate(
        email="testuser@example.com",
        password="secretpassword"
    )
    # background_tasks is not used in repo for test simplicity
    user = users_repo.create_user(db, user_in, background_tasks=None)
    assert user.id is not None
    assert user.email == "testuser@example.com"
    assert user.hashed_password != "secretpassword"
    assert user.is_verified is False


def test_get_user_by_email(db):
    user = users_repo.get_user_by_email(db, "testuser@example.com")
    assert user is not None
    assert user.email == "testuser@example.com"


def test_authenticate_user_success(db):
    user = users_repo.authenticate_user(db, "testuser@example.com", "secretpassword")
    assert user is not None
    assert user.email == "testuser@example.com"


def test_authenticate_user_fail(db):
    user = users_repo.authenticate_user(db, "testuser@example.com", "wrongpassword")
    assert user is None


def test_get_user_by_id(db):
    user = users_repo.get_user_by_email(db, "testuser@example.com")
    user_by_id = users_repo.get_user_by_id(db, user.id)
    assert user_by_id is not None
    assert user_by_id.email == user.email


def test_update_user_avatar(db):
    user = users_repo.get_user_by_email(db, "testuser@example.com")
    new_avatar_url = "http://example.com/avatar.png"
    updated_user = users_repo.update_user_avatar(db, user.id, new_avatar_url)
    assert updated_user.avatar_url == new_avatar_url


def test_verify_user_email(db):
    user = users_repo.get_user_by_email(db, "testuser@example.com")
    user.verification_token = "sometoken"
    db.commit()
    verified_user = users_repo.verify_user_email(db, "sometoken")
    assert verified_user is not None
    assert verified_user.is_verified is True
    assert verified_user.verification_token is None


def test_update_user_avatar(db):
    from src.schemas import UserCreate
    from src.repository.users import create_user, update_user_avatar, get_user_by_id
    user = create_user(db, UserCreate(email="avataruser@example.com", password="password"), background_tasks=None)
    avatar_url = "http://example.com/avatar.png"
    updated = update_user_avatar(db, user.id, avatar_url)
    assert updated.avatar_url == avatar_url
    fetched = get_user_by_id(db, user.id)
    assert fetched.avatar_url == avatar_url


def test_search_users_by_email(db):
    from src.schemas import UserCreate
    from src.repository.users import create_user, get_user_by_email
    email = "searchuser@example.com"
    create_user(db, UserCreate(email=email, password="password"), background_tasks=None)
    found = get_user_by_email(db, email)
    assert found is not None
    assert found.email == email
