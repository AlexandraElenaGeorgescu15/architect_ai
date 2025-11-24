"""
Validation API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Any
import logging

from backend.models.dto import (
    ValidationResultDTO, ArtifactType
)
from backend.services.validation_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/validation", tags=["validation"])


@router.post("/validate", response_model=ValidationResultDTO)
@limiter.limit("30/minute")
async def validate_artifact(
    request: Request,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Validate an artifact.
    
    Request body:
    {
        "artifact_type": "mermaid_erd",
        "content": "erDiagram\n...",
        "meeting_notes": "Optional meeting notes for context"
    }
    """
    artifact_type_str = body.get("artifact_type")
    content = body.get("content", "")
    meeting_notes = body.get("meeting_notes")
    
    if not artifact_type_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_type is required"
        )
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content is required"
        )
    
    try:
        artifact_type = ArtifactType(artifact_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact_type: {artifact_type_str}"
        )
    
    service = get_service()
    result = await service.validate_artifact(
        artifact_type=artifact_type,
        content=content,
        meeting_notes=meeting_notes
    )
    
    return result


@router.post("/validate-batch", response_model=List[ValidationResultDTO])
@limiter.limit("10/minute")
async def validate_batch(
    request: Request,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Validate multiple artifacts in batch.
    
    Request body:
    {
        "artifacts": [
            {
                "type": "mermaid_erd",
                "content": "...",
                "meeting_notes": "..."
            },
            ...
        ]
    }
    """
    artifacts = body.get("artifacts", [])
    
    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifacts list is required"
        )
    
    if len(artifacts) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 artifacts per batch"
        )
    
    service = get_service()
    results = service.validate_batch(artifacts)
    
    return results


@router.get("/stats", response_model=Dict[str, Any])
async def get_validation_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get validation service statistics."""
    # Placeholder for validation stats
    return {
        "total_validations": 0,
        "average_score": 0.0,
        "validation_rate": 0.0
    }



