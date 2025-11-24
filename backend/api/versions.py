"""
Versions API endpoints for artifact version tracking.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, Request
from typing import List, Dict, Any, Optional
import logging

from backend.services.version_service import get_version_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("/{artifact_id}", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
async def get_artifact_versions(
    request: Request,
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all versions for an artifact."""
    service = get_version_service()
    versions = service.get_versions(artifact_id)
    return versions


@router.get("/{artifact_id}/current", response_model=Dict[str, Any])
async def get_current_version(
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get the current version of an artifact."""
    service = get_version_service()
    version = service.get_current_version(artifact_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No versions found for artifact {artifact_id}"
        )
    return version


@router.get("/{artifact_id}/{version_number}", response_model=Dict[str, Any])
async def get_version(
    artifact_id: str,
    version_number: int,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get a specific version of an artifact."""
    service = get_version_service()
    version = service.get_version(artifact_id, version_number)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found for artifact {artifact_id}"
        )
    return version


@router.post("/{artifact_id}/compare", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def compare_versions(
    request: Request,
    artifact_id: str,
    version1: int = Query(..., description="First version number"),
    version2: int = Query(..., description="Second version number"),
    current_user: UserPublic = Depends(get_current_user)
):
    """Compare two versions of an artifact."""
    service = get_version_service()
    comparison = service.compare_versions(artifact_id, version1, version2)
    if "error" in comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=comparison["error"]
        )
    return comparison


@router.post("/{artifact_id}/restore/{version_number}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def restore_version(
    request: Request,
    artifact_id: str,
    version_number: int,
    current_user: UserPublic = Depends(get_current_user)
):
    """Restore a previous version of an artifact."""
    service = get_version_service()
    result = service.restore_version(artifact_id, version_number)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    return result

