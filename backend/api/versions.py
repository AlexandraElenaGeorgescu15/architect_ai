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


# NOTE: More specific routes MUST come before generic routes like /{artifact_id}


@router.post("/create", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def create_version(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Create a new version for an artifact.
    Used by the Canvas editor to save edited diagrams as new versions.
    
    Request body:
    {
        "artifact_id": "mermaid_erd",
        "artifact_type": "mermaid_erd", 
        "content": "erDiagram...",
        "metadata": { "source": "canvas_editor", ... }
    }
    """
    try:
        body = await request.json()
        artifact_id = body.get("artifact_id")
        artifact_type = body.get("artifact_type")
        content = body.get("content")
        metadata = body.get("metadata", {})
        
        if not artifact_id or not content:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="artifact_id and content are required"
            )
        
        service = get_version_service()
        version = service.create_version(
            artifact_id=artifact_id,
            artifact_type=artifact_type or artifact_id,
            content=content,
            metadata=metadata
        )
        
        logger.info(f"✅ [VERSIONS] Created version {version['version']} for {artifact_id} from canvas editor")
        
        return version
    except Exception as e:
        logger.error(f"❌ [VERSIONS] Failed to create version: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/all", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def get_all_versions(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all versions for all artifacts, grouped by artifact type."""
    service = get_version_service()
    
    # Reload from disk to ensure we have latest
    service._load_versions()
    
    logger.info(f"📋 [VERSIONS] Loading all versions. Service has {len(service.versions)} artifacts tracked.")
    
    # Group by artifact type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    total_versions = 0
    
    for artifact_id, versions in service.versions.items():
        if not versions:
            continue
        
        # Get artifact type from first version
        artifact_type = versions[0].get("artifact_type", "unknown")
        
        if artifact_type not in by_type:
            by_type[artifact_type] = []
        
        # Add all versions with artifact_id included
        for v in versions:
            by_type[artifact_type].append({
                **v,
                "artifact_id": artifact_id
            })
            total_versions += 1
    
    # Sort each type's versions by created_at descending
    for artifact_type in by_type:
        by_type[artifact_type].sort(key=lambda v: v.get("created_at", ""), reverse=True)
    
    logger.info(f"📋 [VERSIONS] Returning {total_versions} total versions across {len(by_type)} artifact types")
    
    return {
        "versions_by_type": by_type,
        "artifact_types": list(by_type.keys()),
        "total_versions": total_versions,
        "total_artifacts": len(service.versions)
    }


@router.get("/by-type/{artifact_type}", response_model=List[Dict[str, Any]])
@limiter.limit("30/minute")
async def get_versions_by_type(
    request: Request,
    artifact_type: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all versions for all artifacts of a given type."""
    service = get_version_service()
    
    # Reload from disk to ensure we have latest
    service._load_versions()
    
    all_versions = []
    
    logger.info(f"📋 [VERSIONS] Loading versions for artifact_type: {artifact_type}")
    logger.info(f"📋 [VERSIONS] Service has {len(service.versions)} artifacts tracked")
    
    # Normalize artifact_type for matching
    artifact_type_normalized = artifact_type.lower().replace("-", "_").replace(" ", "_")
    
    # Iterate through all artifact_ids in the version service
    for artifact_id, versions in service.versions.items():
        if not versions:
            continue
            
        # Check if the versions belong to this type
        first_version = versions[0]
        version_type = first_version.get("artifact_type", "")
        version_type_normalized = version_type.lower().replace("-", "_").replace(" ", "_")
        
        # Match logic:
        # 1. Exact type match (normalized)
        # 2. Artifact ID starts with type (legacy fallback)
        
        is_match = False
        if version_type_normalized == artifact_type_normalized:
            is_match = True
        elif artifact_id.lower().replace("-", "_").startswith(artifact_type_normalized + "_"):
            is_match = True
            
        if is_match:
            # Add all versions, ensuring artifact_id is included
            for v in versions:
                v_with_id = {**v, "artifact_id": artifact_id}
                all_versions.append(v_with_id)
    
    # Sort by created_at descending (newest first)
    all_versions.sort(key=lambda v: v.get("created_at", ""), reverse=True)
    
    logger.info(f"📋 [VERSIONS] Returning {len(all_versions)} versions for {artifact_type}")
    return all_versions


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
    
    # Sync with GenerationService to ensure list_artifacts returns the restored version
    try:
        from backend.services.generation_service import get_service as get_generation_service
        gen_service = get_generation_service()
        # We update the artifact in generation service with the restored content
        gen_service.update_artifact(
            artifact_id=artifact_id,
            content=result.get("content"),
            metadata=result.get("metadata")
        )
        logger.info(f"🔄 [VERSIONS] Synced restored artifact {artifact_id} to GenerationService")
    except Exception as e:
        logger.warning(f"⚠️ [VERSIONS] Failed to sync restore with GenerationService: {e}")
        
    return result


@router.get("/migration/preview", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def preview_migration(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Preview what legacy timestamped artifacts would be migrated.
    
    This helps understand how many artifacts have the old timestamped format
    and would be consolidated into stable artifact IDs.
    """
    service = get_version_service()
    preview = service.get_migration_preview()
    
    logger.info(f"📋 [VERSIONS] Migration preview: needs_migration={preview.get('needs_migration')}, "
                f"legacy_groups={len(preview.get('legacy_groups', {}))}")
    
    return preview


@router.post("/migration/run", response_model=Dict[str, Any])
@limiter.limit("2/minute")
async def run_migration(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Run migration to consolidate legacy timestamped artifacts.
    
    This converts artifacts like 'mermaid_erd_20251209_123456' into stable IDs
    like 'mermaid_erd', allowing proper version tracking (v1, v2, v3, etc.).
    
    WARNING: This is a destructive operation. Legacy artifact files will be deleted.
    """
    service = get_version_service()
    
    # First get a preview
    preview = service.get_migration_preview()
    if not preview.get("needs_migration"):
        return {
            "success": True,
            "message": "No migration needed - all artifacts already use stable IDs",
            "migrated_versions": 0,
            "artifacts_consolidated": 0
        }
    
    # Run migration
    result = service.migrate_legacy_versions()
    
    logger.info(f"✅ [VERSIONS] Migration complete: {result}")
    
    return result


@router.delete("/{artifact_id}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def delete_artifact_versions(
    request: Request,
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Delete all versions for an artifact."""
    service = get_version_service()
    result = service.delete_all_versions(artifact_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    logger.info(f"🗑️ [VERSIONS] Deleted all versions for artifact {artifact_id}")
    return result