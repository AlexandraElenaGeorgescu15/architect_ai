"""
Cache management API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, Optional
import logging

from backend.core.cache import get_cache_manager
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get("/stats", summary="Get cache statistics")
async def get_cache_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get cache statistics including backend type and memory usage."""
    cache = get_cache_manager()
    stats = cache.get_stats()
    return {"success": True, "stats": stats}


@router.post("/invalidate", summary="Invalidate cache entries")
@limiter.limit("10/minute")
async def invalidate_cache(
    request: Request,
    pattern: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Invalidate cache entries.
    
    Query parameters:
    - pattern: Optional pattern to match (e.g., "context:*" to invalidate all context caches)
    """
    cache = get_cache_manager()
    
    if pattern:
        count = cache.invalidate_pattern(pattern)
        return {
            "success": True,
            "message": f"Invalidated {count} cache entries matching pattern '{pattern}'"
        }
    else:
        # Invalidate all (use with caution)
        count = cache.invalidate_pattern("*")
        return {
            "success": True,
            "message": f"Invalidated {count} cache entries"
        }


@router.delete("/{key:path}", summary="Delete specific cache entry")
async def delete_cache_entry(
    key: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Delete a specific cache entry by key."""
    cache = get_cache_manager()
    cache.delete(key)
    return {"success": True, "message": f"Cache entry '{key}' deleted"}



