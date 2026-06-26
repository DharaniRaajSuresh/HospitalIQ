"""
JWT authentication module for HospitalIQ API.
Uses bcrypt for password hashing (FAANG-standard), JWT with HS256.
Supports httpOnly cookies (primary) + Bearer header fallback for API clients.
Google OAuth via Authlib for "Sign in with Google".
"""
import os, logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User

logger = logging.getLogger(__name__)

from backend.config import settings

SECRET_KEY = settings.secret_key or os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set via JWT_SECRET_KEY env var or config secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
BCRYPT_ROUNDS = 12

security = HTTPBearer(auto_error=False)
TOKEN_COOKIE_NAME = "hospitaliq_token"

# Authlib OAuth client for Google Sign-In
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.warning("Password verification failed: %s", e)
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def set_token_cookie(response: Response, token: str):
    # secure=True in production (HTTPS only) — critical for banking-grade security.
    # secure=False in development (HTTP localhost). Controlled by ENVIRONMENT env var.
    is_production = settings.environment == "production"
    response.set_cookie(
        key=TOKEN_COOKIE_NAME, value=token,
        httponly=True, samesite="lax", secure=is_production,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/",
    )



def clear_token_cookie(response: Response):
    response.delete_cookie(key=TOKEN_COOKIE_NAME, path="/")


def _extract_token(request: Request, bearer: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if bearer is not None:
        return bearer.credentials
    if request is not None:
        return request.cookies.get(TOKEN_COOKIE_NAME)
    return None


async def get_current_user(
    request: Request,
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_token(request, bearer)
    if token is None:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    email = payload.get("sub")
    if email is None:
        return None
    return db.query(User).filter(User.email == email).first()


def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
