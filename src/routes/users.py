from fastapi import APIRouter, Depends, HTTPException, status, Form, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from src.schemas import UserCreate, UserRead, UserLogin, PasswordResetRequest, PasswordReset
from src.repository import users as user_repo
from src.database.db import get_db
from src.auth_jwt import create_access_token
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from fastapi import Request
from src.limiter import limiter, REGISTER_LIMIT, ME_LIMIT
from src.dependencies import get_current_user
from src.services.cloudinary_service import upload_avatar
from src.services.redis_service import redis_client

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(REGISTER_LIMIT)
def register(request: Request, user: UserCreate, db: Session = Depends(get_db), background_tasks: BackgroundTasks = None):
    """
    Register a new user and send a verification email.

    Args:
        request (Request): FastAPI request object.
        user (UserCreate): Data for the new user.
        db (Session): SQLAlchemy database session.
        background_tasks (BackgroundTasks, optional): FastAPI background tasks for sending email.

    Returns:
        UserRead: The created user instance.
    """
    db_user = user_repo.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    created_user = user_repo.create_user(db, user, background_tasks)
    if not created_user:
        raise HTTPException(status_code=409, detail="User creation failed (possibly duplicate email)")
    return created_user

@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and return a JWT access token.

    Args:
        username (str): The user's email address.
        password (str): The user's password.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Access token and token type if authentication is successful.
    """
    db_user = user_repo.authenticate_user(db, username, password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your email to verify your account.")
    token = create_access_token({"sub": db_user.email, "user_id": db_user.id})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify a user's email address using a verification token.

    Args:
        token (str): The verification token sent to the user's email.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Success message if the token is valid.
    """
    user = db.query(user_repo.User).filter(user_repo.User.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    user.is_verified = True
    user.verification_token = None
    db.commit()
    return {"message": "Email successfully verified! You can now log in."}

@router.get("/me")
@limiter.limit(ME_LIMIT)
def get_me(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    Retrieve the currently authenticated user's profile.

    Args:
        request (Request): FastAPI request object.
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.

    Returns:
        User: The current user instance.
    """
    return current_user

@router.patch("/avatar", response_model=UserRead)
def update_avatar(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    file: UploadFile = File(...)
):
    """
    Update the avatar for the currently authenticated user.

    Args:
        db (Session): SQLAlchemy database session.
        current_user (User): The currently authenticated user.
        file (UploadFile): The new avatar image file.

    Returns:
        UserRead: The updated user instance with the new avatar URL.
    """
    # Upload to Cloudinary
    result = upload_avatar(file.file, public_id=f"user_{current_user.id}")
    avatar_url = result.get("secure_url")
    user = user_repo.update_user_avatar(db, current_user.id, avatar_url)
    return user

@router.post("/request-password-reset", status_code=200)
async def request_password_reset(request: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Request a password reset. Sends a reset token to the user's email if the user exists.

    Args:
        request (PasswordResetRequest): The request containing the user's email.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending email.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Success message (always, to prevent user enumeration).
    """
    user = user_repo.get_user_by_email(db, request.email)
    if user:
        token = await user_repo.create_password_reset_token(user.email)
        background_tasks.add_task(user_repo.send_password_reset_email, user.email, token)
    # Always return success to avoid leaking user existence
    return {"message": "If this email is registered, a password reset link has been sent."}

@router.post("/reset-password", status_code=200)
async def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    """
    Reset the user's password using a valid reset token.

    Args:
        data (PasswordReset): The request containing the reset token and new password.
        db (Session): SQLAlchemy database session.

    Returns:
        dict: Success or error message.
    """
    email = await user_repo.verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    ok = await user_repo.reset_user_password(db, email, data.new_password)
    await user_repo.consume_password_reset_token(data.token)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password has been reset successfully. You can now log in."}
