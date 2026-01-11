"""
API Dependencies

Shared dependencies for API routers.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.database import Database
from web.api.auth import decode_access_token

# Global database instance
_db: Database = None

# Security scheme
security = HTTPBearer(auto_error=False)


def get_db() -> Database:
    """Get database instance."""
    global _db
    if _db is None:
        _db = Database()
        _db.init_schema()
    return _db


def init_db():
    """Initialize database on startup."""
    global _db
    _db = Database()
    _db.init_schema()


def close_db():
    """Close database on shutdown."""
    global _db
    if _db:
        _db.close()
        _db = None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Database = Depends(get_db),
) -> dict:
    """
    Get the current authenticated user from JWT token.
    Raises 401 if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get_user_by_id(token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Database = Depends(get_db),
) -> Optional[dict]:
    """
    Get the current user if authenticated, otherwise return None.
    Does not raise an error if not authenticated.
    """
    if credentials is None:
        return None

    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        return None

    user = db.get_user_by_id(token_data.user_id)
    if user is None or not user.get("is_active"):
        return None

    return user


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Require the current user to be an admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
