"""
Finetuning Pool API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional, Dict, Any
import logging

from backend.services.finetuning_pool import get_pool
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/finetuning-pool", tags=["Finetuning Pool"])


@router.get("/stats", summary="Get finetuning pool statistics")
async def get_pool_stats(
    artifact_type: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get statistics about the finetuning pool."""
    pool = get_pool()
    stats = pool.get_pool_stats(artifact_type)
    return {"success": True, "stats": stats}


@router.post("/trigger-major/{artifact_type}", summary="Trigger major finetuning for artifact type")
@limiter.limit("2/minute")
async def trigger_major_finetuning(
    request: Request,
    artifact_type: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Trigger major finetuning (2000 examples) for an artifact type."""
    pool = get_pool()
    stats = pool.get_pool_stats(artifact_type)
    
    if not stats.get("ready_for_major", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough examples for major finetuning. Need {pool.major_finetuning_threshold}, have {stats.get('count', 0)}"
        )
    
    # Trigger major finetuning
    await pool._trigger_finetuning(artifact_type, incremental=False)
    
    return {
        "success": True,
        "message": f"Major finetuning triggered for {artifact_type}",
        "examples_used": stats.get("count", 0)
    }


@router.post("/clear/{artifact_type}", summary="Clear pool for artifact type")
@limiter.limit("5/minute")
async def clear_pool(
    request: Request,
    artifact_type: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Clear the finetuning pool for an artifact type (after finetuning completes)."""
    pool = get_pool()
    success = pool.clear_pool(artifact_type)
    if success:
        return {"success": True, "message": f"Pool cleared for {artifact_type}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pool found for {artifact_type}"
        )

