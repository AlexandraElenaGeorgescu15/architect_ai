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


@router.get("/by-type/{artifact_type}", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
async def get_versions_by_type(
    request: Request,
    artifact_type: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all versions for all artifacts of a given type."""
    service = get_version_service()
    all_versions = []
    
    logger.info(f"📋 [VERSIONS] Loading versions for artifact_type: {artifact_type}")
    logger.info(f"📋 [VERSIONS] Total artifact_ids in service: {len(service.versions)}")
    
    # Normalize artifact_type for matching (handle case and format variations)
    artifact_type_normalized = artifact_type.lower().replace("-", "_").replace(" ", "_")
    
    # Iterate through all artifact_ids in the version service
    matching_artifact_ids = []
    for artifact_id, versions in service.versions.items():
        # Normalize artifact_id for matching
        artifact_id_normalized = artifact_id.lower().replace("-", "_").replace(" ", "_")
        
        # Check if this artifact_id matches the type (starts with artifact_type)
        # This handles cases like "mermaid_erd_20251126_200400" matching "mermaid_erd"
        # Also handle variations like "mermaid_erd" vs "mermaid-erd" vs "Mermaid ERD"
        if (artifact_id_normalized.startswith(artifact_type_normalized + "_") or 
            artifact_id_normalized == artifact_type_normalized or
            artifact_id.startswith(artifact_type + "_") or 
            artifact_id == artifact_type):
            matching_artifact_ids.append(artifact_id)
            logger.info(f"📋 [VERSIONS] Found matching artifact_id: {artifact_id} with {len(versions)} versions")
            # Add all versions from this artifact_id (they should all be of the same type)
            for version in versions:
                # Match by artifact_type field OR by artifact_id prefix (more lenient)
                version_artifact_type = version.get("artifact_type", "")
                version_artifact_type_normalized = version_artifact_type.lower().replace("-", "_").replace(" ", "_")
                
                # Match if types are equal (normalized) OR artifact_id matches prefix
                if (version_artifact_type_normalized == artifact_type_normalized or 
                    version_artifact_type == artifact_type or
                    artifact_id.startswith(artifact_type + "_") or
                    artifact_id_normalized.startswith(artifact_type_normalized + "_")):
                    # Add artifact_id to version for reference
                    version_with_id = {**version, "artifact_id": artifact_id}
                    all_versions.append(version_with_id)
                    logger.debug(f"📋 [VERSIONS] Added version {version.get('version', '?')} from {artifact_id} (type: {version_artifact_type})")
    
    # Sort by created_at descending (newest first)
    all_versions.sort(key=lambda v: v.get("created_at", ""), reverse=True)
    
    logger.info(f"📋 [VERSIONS] Returning {len(all_versions)} versions for {artifact_type} from {len(matching_artifact_ids)} artifact IDs: {matching_artifact_ids[:5]}{'...' if len(matching_artifact_ids) > 5 else ''}")
    return all_versions