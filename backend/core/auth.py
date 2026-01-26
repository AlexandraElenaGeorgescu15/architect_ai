"""
Authentication stub - Bypassed for local POC.
"""
from fastapi import Security
from fastapi.security import HTTPBearer, APIKeyHeader
from backend.models.dto import UserPublic
from typing import Optional

# No-op security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_jwt_settings():
    return {"secret_key": "bypass", "algorithm": "HS256"}

async def get_current_user(token: Optional[str] = Security(bearer_scheme)):
    """Always return admin user."""
    return UserPublic(
        id="admin",
        username="admin",
        email="admin@architect.ai",
        role="admin"
    )

async def get_api_key(api_key: Optional[str] = Security(api_key_header)):
    return api_key

def verify_password(plain, hashed):
    return True

def get_password_hash(password):
    return "hashed_bypass"

def create_access_token(data, expires_delta=None):
    return "bypass_token"

def generate_api_key():
    return "bypass_key"
