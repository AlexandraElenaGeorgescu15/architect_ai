"""
Git API endpoints for artifact git diff functionality.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from typing import Dict, Any, Optional
import logging

from backend.services.git_service import get_git_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/git", tags=["git"])


@router.get("/diff", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def get_file_git_diff(
    request: Request,
    file_path: str = Query(..., description="Path to file (relative to repo root or absolute)"),
    base_ref: Optional[str] = Query(None, description="Base reference (commit, branch, or tag). Defaults to HEAD~1"),
    current_user: UserPublic = Depends(get_current_user)
):
    """Get git diff for a specific file."""
    service = get_git_service()
    result = service.get_file_git_diff(file_path, base_ref)
    
    if result.get("error") and not result.get("diff"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "File not found or not in git repository")
        )
    
    return result


@router.get("/status/{artifact_id}", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def get_artifact_git_status(
    request: Request,
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get git status for an artifact."""
    service = get_git_service()
    result = service.get_artifact_git_status(artifact_id)
    return result


@router.get("/status", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_all_artifacts_git_status(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get git status for all artifacts in outputs directory."""
    service = get_git_service()
    result = service.get_all_artifacts_git_status()
    return result

