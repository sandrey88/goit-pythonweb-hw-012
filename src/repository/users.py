from sqlalchemy.orm import Session
from src.database.models import User
from src.schemas import UserCreate
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
import os
from src.services.redis_service import redis_client
import secrets
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

RESET_TOKEN_PREFIX = "reset_token:"
RESET_TOKEN_TTL = 1800  # 30 minutes


async def send_verification_email(email: str, token: str):
    """
    Send a verification email with a tokenized link to the user.

    Args:
        email (str): The recipient's email address.
        token (str): The verification token to include in the link.
    """
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
    conf = ConnectionConfig(
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
        MAIL_FROM=os.environ.get("MAIL_FROM"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", 465)),
        MAIL_SERVER=os.environ.get("MAIL_SERVER"),
        MAIL_STARTTLS=os.environ.get("MAIL_STARTTLS", "False") == "True",
        MAIL_SSL_TLS=os.environ.get("MAIL_SSL_TLS", "True") == "True",
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    verification_link = f"http://localhost:8000/auth/verify-email?token={token}"
    message = MessageSchema(
        subject="Verify your email",
        recipients=[email],
        body=f"Please verify your email by clicking the following link: {verification_link}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


def get_user_by_email(db: Session, email: str):
    """
    Retrieve a user by their email address.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): The user's email address.

    Returns:
        User or None: The user instance if found, else None.
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """
    Retrieve a user by their ID.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): The user's ID.

    Returns:
        User or None: The user instance if found, else None.
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate, background_tasks=None):
    """
    Create a new user with email verification and hashed password.

    Args:
        db (Session): SQLAlchemy database session.
        user (UserCreate): Data for the new user.
        background_tasks (BackgroundTasks, optional): FastAPI background tasks for sending email.

    Returns:
        User or None: The created user instance if successful, else None.
    """
    hashed_password = pwd_context.hash(user.password)
    verification_token = str(uuid4())
    db_user = User(email=user.email, hashed_password=hashed_password, verification_token=verification_token)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
        if background_tasks is not None:
            background_tasks.add_task(send_verification_email, db_user.email, verification_token)
        return db_user
    except IntegrityError:
        db.rollback()
        return None


def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user by email and password.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): The user's email address.
        password (str): The user's password (plain text).

    Returns:
        User or None: The authenticated user if credentials are valid, else None.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user


def update_user_avatar(db: Session, user_id: int, avatar_url: str):
    """
    Update the avatar URL for a user.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): The ID of the user to update.
        avatar_url (str): The new avatar URL.

    Returns:
        User or None: The updated user instance if found, else None.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
    return user


def verify_user_email(db: Session, token: str):
    """
    Verify a user's email using a verification token.

    Args:
        db (Session): SQLAlchemy database session.
        token (str): The verification token.

    Returns:
        User or None: The verified user instance if found and token matches, else None.
    """
    user = db.query(User).filter(User.verification_token == token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.commit()
        db.refresh(user)
    return user


async def send_password_reset_email(email: str, token: str):
    """
    Send a password reset email with a tokenized link to the user.

    Args:
        email (str): The recipient's email address.
        token (str): The password reset token to include in the link.
    """
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
    conf = ConnectionConfig(
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
        MAIL_FROM=os.environ.get("MAIL_FROM"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", 465)),
        MAIL_SERVER=os.environ.get("MAIL_SERVER"),
        MAIL_STARTTLS=os.environ.get("MAIL_STARTTLS", "False") == "True",
        MAIL_SSL_TLS=os.environ.get("MAIL_SSL_TLS", "True") == "True",
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    reset_link = f"http://localhost:8000/auth/reset-password?token={token}"
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"To reset your password, click the following link (valid for 30 minutes): {reset_link}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def create_password_reset_token(email: str) -> str:
    """
    Generate and store a password reset token in Redis for the given email.

    Args:
        email (str): The user's email address.

    Returns:
        str: The generated token.
    """
    token = secrets.token_urlsafe(32)
    await redis_client.set(f"{RESET_TOKEN_PREFIX}{token}", email, ex=RESET_TOKEN_TTL)
    return token


async def verify_password_reset_token(token: str) -> str | None:
    """
    Verify a password reset token and return the associated email if valid.

    Args:
        token (str): The password reset token.

    Returns:
        Optional[str]: The email if the token is valid, else None.
    """
    email = await redis_client.get(f"{RESET_TOKEN_PREFIX}{token}")
    return email


async def consume_password_reset_token(token: str):
    """
    Remove a password reset token from Redis after use.
    """
    await redis_client.delete(f"{RESET_TOKEN_PREFIX}{token}")


async def reset_user_password(db: Session, email: str, new_password: str):
    """
    Set a new password for the user with the given email.

    Args:
        db (Session): SQLAlchemy database session.
        email (str): The user's email address.
        new_password (str): The new password to set.
    """
    user = get_user_by_email(db, email)
    if not user:
        return False
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    db.refresh(user)
    return True
