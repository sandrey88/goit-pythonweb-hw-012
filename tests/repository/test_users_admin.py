import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.db import Base
from src.repository import users as users_repo
from src.schemas import UserCreate
from src.database.models import User

# Use in-memory SQLite for testing
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)

def test_create_admin_user(db):
    # Create a user
    user_in = UserCreate(email="adminuser@example.com", password="adminpass")
    user = users_repo.create_user(db, user_in, background_tasks=None)
    # Manually set role to admin
    user.role = "admin"
    db.commit()
    db.refresh(user)
    assert user.role == "admin"

    # Fetch and check
    fetched = users_repo.get_user_by_email(db, "adminuser@example.com")
    assert fetched.role == "admin"
