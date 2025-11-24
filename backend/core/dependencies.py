"""
Dependency injection for FastAPI.
"""

from typing import Generator, Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.config import settings
from backend.core.auth import get_current_user as _get_current_user_raw
from backend.models.dto import UserPublic


def get_database() -> Generator[Session, None, None]:
    """
    Dependency for database session.
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_database)):
            return db.query(Item).all()
    """
    yield from get_db()


def get_settings():
    """Dependency for application settings."""
    return settings


async def get_current_user(
    user_data = Depends(_get_current_user_raw)
) -> UserPublic:
    """
    Get current user as UserPublic model.
    
    Args:
        user_data: Raw user data from JWT token or UserPublic instance
    
    Returns:
        UserPublic model instance
    
    Note:
        If no user data, returns a default UserPublic with minimal fields.
        In production, you might want to raise HTTPException for unauthenticated requests.
    """
    # If already a UserPublic instance, return it
    if isinstance(user_data, UserPublic):
        return user_data
    
    if user_data is None:
        # Return default user for development (no auth required)
        return UserPublic(
            id="default",
            username="default",
            email="default@example.com",
            role="user"
        )
    
    # Convert dict to UserPublic
    if isinstance(user_data, dict):
        return UserPublic(
            id=user_data.get("id") or user_data.get("sub"),
            username=user_data.get("username"),
            email=user_data.get("email"),
            role=user_data.get("role"),
            sub=user_data.get("sub"),
            exp=user_data.get("exp"),
            iat=user_data.get("iat")
        )
    
    # Fallback to default
    return UserPublic(
        id="default",
        username="default",
        email="default@example.com",
        role="user"
    )

