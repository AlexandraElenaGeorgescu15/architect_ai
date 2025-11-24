"""
VRAM Management API endpoints.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging

from backend.core.auth import get_current_user
from backend.models.dto import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vram", tags=["VRAM Management"])


@router.get("/usage", summary="Get current VRAM usage")
async def get_vram_usage(
    current_user: UserPublic = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current VRAM usage and model loading status.
    
    Returns:
        Dictionary with VRAM usage stats
    """
    try:
        from ai.ollama_client import get_ollama_client
        
        ollama_client = get_ollama_client()
        vram_info = ollama_client.get_vram_usage()
        
        return {
            "success": True,
            "vram": vram_info
        }
    except Exception as e:
        logger.error(f"Error getting VRAM usage: {e}")
        return {
            "success": False,
            "error": str(e),
            "vram": {
                "used_gb": 0.0,
                "available_gb": 12.0,
                "total_gb": 12.0,
                "active_models": [],
                "persistent_models": [],
                "usage_percent": 0.0
            }
        }

