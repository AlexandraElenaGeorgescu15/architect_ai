"""
Authentication endpoints.
"""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.core.auth import (
    create_access_token,
    get_current_user,
    get_jwt_settings,
    get_password_hash,  # In a real app we'd verify against DB
    verify_password,
    generate_api_key
)
from backend.core.config import settings
from backend.models.dto import UserPublic

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

@router.post("/token", response_model=Dict[str, Any])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint - DEPRECATED/DISABLED.
    Authentication is now bypassed for local development.
    Returns a dummy token for compatibility.
    """
    # Return dummy token to satisfy frontend clients that might still call this
    return {
        "access_token": "admin-bypass-token",
        "token_type": "bearer",
        "expires_in": 3600
    }

@router.get("/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
    """Get current logged in user."""
    return current_user

@router.post("/api-key", response_model=Dict[str, str])
async def create_api_key(current_user: UserPublic = Depends(get_current_user)):
    """Generate a new API key."""
    api_key = generate_api_key()
    return {"api_key": api_key}
