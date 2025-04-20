from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .db import Base
from datetime import datetime

class User(Base):
    """
    User model for the application.

    Attributes:
        id (int): Unique identifier of the user.
        email (str): User's email address (unique).
        hashed_password (str): Hashed password for authentication.
        is_verified (bool): Indicates if the user's email is verified.
        verification_token (str): Token for email verification.
        avatar (str): Path to the user's avatar image.
        avatar_url (str): URL to the user's avatar image.
        created_at (datetime): Date and time of user creation.
        contacts (List[Contact]): List of user's contacts.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True, unique=True)
    avatar = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contacts = relationship("Contact", back_populates="user")

class Contact(Base):
    """
    Contact model for the application.

    Attributes:
        id (int): Unique identifier of the contact.
        first_name (str): First name of the contact.
        last_name (str): Last name of the contact.
        email (str): Contact's email address (unique).
        phone (str): Contact's phone number.
        birthday (date): Contact's birthday.
        additional_data (str): Additional information about the contact.
        user_id (int): ID of the user who owns the contact.
        user (User): Reference to the owner user.
    """
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    birthday = Column(Date)
    additional_data = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="contacts")
