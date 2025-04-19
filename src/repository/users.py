from sqlalchemy.orm import Session
from src.database.models import User
from src.schemas import UserCreate
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from uuid import uuid4
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

async def send_verification_email(email: str, token: str):
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
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate, background_tasks=None):
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
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user

def update_user_avatar(db: Session, user_id: int, avatar_url: str):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.avatar_url = avatar_url
        db.commit()
        db.refresh(user)
    return user
