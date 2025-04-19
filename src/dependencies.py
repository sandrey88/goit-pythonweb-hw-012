from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from .auth_jwt import verify_access_token
from .database.db import get_db
from .repository import users as user_repo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_access_token(token)
    if payload is None:
        raise credentials_exception
    user = user_repo.get_user_by_email(db, payload.get("sub"))
    if user is None:
        raise credentials_exception
    return user
