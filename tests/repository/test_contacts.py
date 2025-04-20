import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.db import Base
from src.repository import contacts as contacts_repo
from src.schemas import ContactCreate, ContactUpdate, UserCreate
from src.database.models import Contact
from src.repository.users import create_user

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


def test_create_contact(db):
    from src.schemas import UserCreate
    user = create_user(db, UserCreate(email="testuser@example.com", password="password"), background_tasks=None)
    contact_in = ContactCreate(
        first_name="Test",
        last_name="User",
        email="testuser@example.com",
        phone="1234567890",
        birthday="2000-01-01",
        additional_data="Test contact",
        user_id=user.id
    )
    contact = contacts_repo.create_contact(db, contact_in)
    assert contact.id is not None
    assert contact.first_name == "Test"
    assert contact.email == "testuser@example.com"


def test_get_contacts_empty(db):
    # Should return at least one contact if previous test ran
    contacts = contacts_repo.get_contacts(db)
    assert isinstance(contacts, list)
    assert len(contacts) >= 1


def test_update_contact(db):
    from src.schemas import UserCreate
    user = create_user(db, UserCreate(email="updateuser@example.com", password="password"), background_tasks=None)
    contact_in = ContactCreate(
        first_name="Update",
        last_name="Test",
        email="update@example.com",
        phone="1112223333",
        birthday="1990-05-05",
        additional_data="Before update",
        user_id=user.id
    )
    contact = contacts_repo.create_contact(db, contact_in)
    update_data = ContactUpdate(
        first_name="Updated",
        last_name="Tested",
        email="updated@example.com",
        phone="9998887777",
        birthday="1991-06-06",
        additional_data="After update"
    )
    updated = contacts_repo.update_contact(db, contact.id, update_data)
    assert updated.first_name == "Updated"
    assert updated.email == "updated@example.com"
    assert updated.additional_data == "After update"


def test_delete_contact(db):
    from src.schemas import UserCreate
    user = create_user(db, UserCreate(email="deleteuser@example.com", password="password"), background_tasks=None)
    contact_in = ContactCreate(
        first_name="Delete",
        last_name="Me",
        email="delete@example.com",
        phone="5556667777",
        birthday="1985-12-12",
        additional_data="To be deleted",
        user_id=user.id
    )
    contact = contacts_repo.create_contact(db, contact_in)
    deleted = contacts_repo.delete_contact(db, contact.id)
    assert deleted is not None
    # Should not be found after delete
    from src.repository.contacts import get_contact
    assert get_contact(db, contact.id) is None


def test_search_contacts(db):
    from src.schemas import UserCreate
    user = create_user(db, UserCreate(email="searchuser@example.com", password="password"), background_tasks=None)
    # Ensure at least one contact exists
    contact_in = ContactCreate(
        first_name="Search",
        last_name="Target",
        email="searchtarget@example.com",
        phone="0009998888",
        birthday="2002-02-02",
        additional_data="Searchable",
        user_id=user.id
    )
    contacts_repo.create_contact(db, contact_in)
    results = contacts_repo.search_contacts(db, "Search")
    assert any(c.email == "searchtarget@example.com" for c in results)


def test_get_upcoming_birthdays(db):
    import datetime
    from src.schemas import UserCreate
    user = create_user(db, UserCreate(email="birthdaysuser@example.com", password="password"), background_tasks=None)
    today = datetime.date.today()
    in_3_days = today + datetime.timedelta(days=3)
    in_10_days = today + datetime.timedelta(days=10)
    # Contact with birthday in 3 days (should be in the list)
    contact_soon = ContactCreate(
        first_name="Soon",
        last_name="Birthday",
        email="soon@example.com",
        phone="1231231234",
        birthday=in_3_days.strftime("%Y-%m-%d"),
        additional_data="Soon birthday",
        user_id=user.id
    )
    # Contact with birthday in 10 days (should not be in the list)
    contact_late = ContactCreate(
        first_name="Late",
        last_name="Birthday",
        email="late@example.com",
        phone="3213214321",
        birthday=in_10_days.strftime("%Y-%m-%d"),
        additional_data="Late birthday",
        user_id=user.id
    )
    contacts_repo.create_contact(db, contact_soon)
    contacts_repo.create_contact(db, contact_late)
    results = contacts_repo.get_upcoming_birthdays(db)
    emails = [c.email for c in results]
    assert "soon@example.com" in emails
    assert "late@example.com" not in emails
