"""
Authentication Router

Endpoints for user registration, login, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from src.database import Database
from web.api.deps import get_db, get_current_user
from web.api.auth import (
    hash_password,
    verify_password,
    create_access_token,
    Token,
)

router = APIRouter()


class UserRegister(BaseModel):
    """User registration request."""
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response (no password)."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: Optional[str] = None


class SetupStatus(BaseModel):
    """Initial setup status."""
    needs_setup: bool
    user_count: int


def user_to_response(user: dict) -> UserResponse:
    """Convert database user dict to response model."""
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        is_active=bool(user["is_active"]),
        is_admin=bool(user["is_admin"]),
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


@router.get("/setup-status", response_model=SetupStatus)
async def get_setup_status(db: Database = Depends(get_db)):
    """
    Check if initial setup is needed (no users exist).
    """
    user_count = db.get_user_count()
    return SetupStatus(needs_setup=user_count == 0, user_count=user_count)


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Database = Depends(get_db)):
    """
    Register a new user.
    First user automatically becomes admin.
    """
    # Check if username exists
    if db.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    if db.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # First user becomes admin
    is_admin = db.get_user_count() == 0

    # Create user
    password_hash = hash_password(user_data.password)
    try:
        user_id = db.create_user(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            is_admin=is_admin,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

    user = db.get_user_by_id(user_id)
    return user_to_response(user)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Database = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    user = db.get_user_by_username(credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last login
    db.update_last_login(user["id"])

    # Create token
    access_token = create_access_token(
        data={"sub": user["id"], "username": user["username"]}
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return user_to_response(current_user)


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout the current user.
    Since we use stateless JWT, this is just a placeholder.
    The client should discard the token.
    """
    return {"message": "Successfully logged out"}
