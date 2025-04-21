from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from .auth_jwt import verify_access_token
from .database.db import get_db
from .repository import users as user_repo
from src.services.redis_service import redis_client
import json
from datetime import datetime

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Try to get user from Redis cache
    cache_key = f"user_token:{token}"
    cached_user = await redis_client.get(cache_key)
    if cached_user:
        user_data = json.loads(cached_user)
        # Recreate User object from dict (optional: depends on usage)
        from src.database.models import User
        user = User(**user_data)
        return user
    payload = verify_access_token(token)
    if payload is None:
        raise credentials_exception
    user = user_repo.get_user_by_email(db, payload.get("sub"))
    if user is None:
        raise credentials_exception
    # Cache the user (serialize to dict)
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    await redis_client.set(cache_key, json.dumps(user_dict, default=default_serializer), ex=900)  # 15 min TTL
    return user

async def get_current_admin(current_user=Depends(get_current_user)):
    """
    Dependency that checks if the current user has admin privileges.

    Args:
        current_user (User): The currently authenticated user.

    Returns:
        User: The current user instance if admin.

    Raises:
        HTTPException: If the user is not an admin.
    """
    if getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required.")
    return current_user
