from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database.db import get_db
from ..dependencies import get_current_user
from ..repository import contacts as repository
from ..schemas import Contact, ContactCreate, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.post("/", response_model=Contact)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Create a new contact for the current user.

    Args:
        contact (ContactCreate): Data for the new contact.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        Contact: The created contact instance.
    """
    contact.user_id = current_user.id
    return repository.create_contact(db=db, contact=contact)

@router.get("/", response_model=List[Contact])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Retrieve all contacts belonging to the current user.

    Args:
        skip (int): Number of records to skip.
        limit (int): Maximum number of records to return.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        List[Contact]: List of user's contacts.
    """
    contacts = repository.get_contacts(db, skip=skip, limit=limit)
    # Only return contacts that belong to the current user
    return [c for c in contacts if c.user_id == current_user.id]

@router.get("/birthdays/next7days", response_model=List[Contact])
def upcoming_birthdays(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Retrieve contacts with birthdays in the next 7 days for the current user.

    Args:
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        List[Contact]: List of contacts with upcoming birthdays.
    """
    contacts = repository.get_upcoming_birthdays(db)
    return [c for c in contacts if c.user_id == current_user.id]

@router.get("/find", response_model=List[Contact])
def find_contacts(q: str = Query(..., min_length=1, description="Search query"), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Search for contacts belonging to the current user by query string.

    Args:
        q (str): Search query string.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        List[Contact]: List of matching contacts.
    """
    contacts = repository.search_contacts(db, search_query=q)
    return [c for c in contacts if c.user_id == current_user.id]

@router.get("/{contact_id}", response_model=Contact)
def read_contact(contact_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Retrieve a contact by ID for the current user.

    Args:
        contact_id (int): The ID of the contact to retrieve.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        Contact: The contact instance if found.
    """
    db_contact = repository.get_contact(db, contact_id=contact_id)
    if db_contact is None or db_contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@router.put("/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Update a contact by ID for the current user.

    Args:
        contact_id (int): The ID of the contact to update.
        contact (ContactUpdate): Data to update the contact with.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        Contact: The updated contact instance if found.
    """
    db_contact = repository.get_contact(db, contact_id=contact_id)
    if db_contact is None or db_contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    db_contact = repository.update_contact(db, contact_id=contact_id, contact=contact)
    return db_contact

@router.delete("/{contact_id}", response_model=Contact)
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Delete a contact by ID for the current user.

    Args:
        contact_id (int): The ID of the contact to delete.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        Contact: The deleted contact instance if found.
    """
    db_contact = repository.get_contact(db, contact_id=contact_id)
    if db_contact is None or db_contact.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Contact not found")
    db_contact = repository.delete_contact(db, contact_id=contact_id)
    return db_contact
