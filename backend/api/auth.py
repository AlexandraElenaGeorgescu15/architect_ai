"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from backend.core.auth import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    generate_api_key
)
from backend.core.config import settings
from backend.core.middleware import limiter
from slowapi import Limiter

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class APIKeyResponse(BaseModel):
    """API key response model."""
    api_key: str
    message: str = "Store this API key securely. It will not be shown again."


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    """
    Login endpoint (placeholder - implement user database lookup).
    
    TODO: Implement actual user authentication against database.
    """
    # Placeholder: In production, verify against user database
    # For now, accept any username/password (demo only)
    if not body.username or not body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create token (in production, include user ID, roles, etc.)
    access_token = create_access_token(
        data={"sub": body.username, "username": body.username}
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expiration_hours * 3600
    )


@router.post("/api-key", response_model=APIKeyResponse)
async def create_api_key(
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a new API key for the authenticated user.
    
    TODO: Store API key in database associated with user.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    api_key = generate_api_key()
    
    # TODO: Store API key in database
    # db.execute("INSERT INTO api_keys (user_id, key_hash) VALUES ...")
    
    return APIKeyResponse(api_key=api_key)


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return current_user



