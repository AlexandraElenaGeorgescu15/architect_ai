"""
Configuration API endpoints for managing API keys and settings.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pathlib import Path
import os
import logging
from backend.core.dependencies import get_current_user
from backend.models.dto import UserPublic

router = APIRouter(prefix="/api/config", tags=["Configuration"])
logger = logging.getLogger(__name__)

class ApiKeyRequest(BaseModel):
    provider: str
    api_key: str

@router.post("/api-keys")
async def save_api_key(
    request: Request,
    api_key_request: ApiKeyRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Save an API key to the .env file.
    
    Args:
        api_key_request: Provider name and API key
        
    Returns:
        Success status
    """
    provider = api_key_request.provider.lower()
    api_key = api_key_request.api_key.strip()
    
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    
    # Map provider names to env var names
    env_var_map = {
        'groq': 'GROQ_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'google': 'GOOGLE_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'xai': 'XAI_API_KEY',
    }
    
    env_var = env_var_map.get(provider)
    if not env_var:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    # Find .env file (check multiple locations)
    env_paths = [
        Path('.env'),
        Path('backend/.env'),
        Path('../.env'),
        Path('../../.env'),
    ]
    
    env_file = None
    for path in env_paths:
        if path.exists():
            env_file = path
            break
    
    if not env_file:
        # Create .env in backend directory
        env_file = Path('backend/.env')
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.touch()
    
    # Read existing .env
    env_lines = []
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
    
    # Update or add the API key
    found = False
    for i, line in enumerate(env_lines):
        if line.strip().startswith(f'{env_var}='):
            env_lines[i] = f'{env_var}={api_key}\n'
            found = True
            break
    
    if not found:
        env_lines.append(f'{env_var}={api_key}\n')
    
    # Write back to .env
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
        
        logger.info(f"Saved {provider} API key to {env_file}")
        
        # Reload settings dynamically (update runtime settings)
        from backend.core.config import settings
        os.environ[env_var] = api_key  # Update environment variable
        
        # Update settings object
        if provider == 'groq':
            settings.groq_api_key = api_key
        elif provider in ['gemini', 'google']:
            settings.gemini_api_key = api_key
            settings.google_api_key = api_key
        elif provider == 'openai':
            settings.openai_api_key = api_key
        elif provider == 'anthropic':
            settings.anthropic_api_key = api_key
        elif provider == 'xai':
            settings.xai_api_key = api_key
        
        # Refresh model service to update model statuses
        from backend.services.model_service import get_service
        model_service = get_service()
        await model_service._refresh_cloud_models()
        
        logger.info(f"Reloaded settings and refreshed models for {provider}")
        
        return {
            "success": True,
            "message": f"{provider} API key saved successfully",
            "env_file": str(env_file),
            "note": "Settings reloaded successfully. Models are now available."
        }
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save API key: {str(e)}")

