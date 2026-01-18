"""
Authentication utilities

Password hashing and JWT token management.
"""

import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.environ.get("GLEAN_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None
    username: Optional[str] = None


class UserCreate(BaseModel):
    """User registration model."""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """User login model."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response model (no password)."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: Optional[str] = None


def _prepare_password(password: str) -> str:
    """Pre-hash password if longer than bcrypt's 72-byte limit."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        # SHA-256 hash and base64 encode to stay under 72 bytes
        return base64.b64encode(hashlib.sha256(password_bytes).digest()).decode("ascii")
    return password


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(_prepare_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(_prepare_password(plain_password), hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        username: str = payload.get("username")
        if sub is None:
            return None
        user_id = int(sub)  # Convert string back to int
        return TokenData(user_id=user_id, username=username)
    except JWTError:
        return None
