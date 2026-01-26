"""
Authentication and authorization utilities.
Supports JWT tokens and API keys.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import secrets
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings (loaded from config)
from backend.core.config import settings

def get_jwt_settings():
    """Get JWT settings from config."""
    return {
        "secret_key": settings.jwt_secret_key,
        "algorithm": settings.jwt_algorithm,
        "expire_minutes": settings.jwt_expiration_hours * 60
    }

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    jwt_settings = get_jwt_settings()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=jwt_settings["expire_minutes"])
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    jwt_settings = get_jwt_settings()
    encoded_jwt = jwt.encode(to_encode, jwt_settings["secret_key"], algorithm=jwt_settings["algorithm"])
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        jwt_settings = get_jwt_settings()
        payload = jwt.decode(token, jwt_settings["secret_key"], algorithms=[jwt_settings["algorithm"]])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
):
    """
    Get current user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        UserPublic model instance or default user if no auth
    """
    from backend.models.dto import UserPublic
    
    if not credentials:
        # Return default user for development (no auth required)
        return UserPublic(
            id="default",
            username="default",
            email="default@example.com",
            role="user"
        )
    
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        # Return default user if token invalid
        return UserPublic(
            id="default",
            username="default",
            email="default@example.com",
            role="user"
        )
    
    # Convert dict to UserPublic
    return UserPublic(
        id=payload.get("id") or payload.get("sub"),
        username=payload.get("username"),
        email=payload.get("email"),
        role=payload.get("role"),
        sub=payload.get("sub"),
        exp=payload.get("exp"),
        iat=payload.get("iat")
    )


async def get_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Get API key from header.
    
    Args:
        api_key: API key from header
    
    Returns:
        API key string or None
    """
    if not api_key:
        return None
    
    # TODO: Validate API key against database
    # For now, just return the key
    return api_key


    """
    Require either JWT token or API key authentication.
    
    Args:
        credentials: HTTP Bearer credentials
        api_key: API key from header
    
    Returns:
        Authentication info (user data or API key)
    
    Raises:
        HTTPException: If authentication fails
    """
    # BYPASS AUTHENTICATION (User Request)
    # Always return admin access
    return {
        "type": "jwt",
        "data": {
            "sub": "admin",
            "username": "admin",
            "role": "admin",
            "id": "admin"
        }
    }
    
    # Original logic disabled below
    # if credentials: ...


def generate_api_key() -> str:
    """
    Generate a new API key.
    
    Returns:
        Random API key string
    """
    return secrets.token_urlsafe(32)

