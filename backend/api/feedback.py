"""
Feedback API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional, List, Dict, Any
import logging

from datetime import datetime
from backend.models.dto import (
    FeedbackRequest, FeedbackResponse
)
from backend.services.feedback_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Submit feedback on an artifact.
    
    Request body:
    {
        "artifact_id": "artifact-123",
        "score": 85.0,
        "notes": "Good ERD but missing relationships",
        "feedback_type": "correction",
        "corrected_content": "erDiagram\n..."
    }
    """
    # Get artifact details - try to fetch from artifact store
    artifact_type = body.artifact_id.split("-")[0] if "-" in body.artifact_id else "unknown"
    ai_output = body.corrected_content or ""  # Use corrected content if provided
    
    # Try to get original artifact content from artifact store
    try:
        from backend.services.generation_service import get_service as get_gen_service
        gen_service = get_gen_service()
        # Try to find artifact in active jobs or artifact store
        # For now, use corrected_content or empty string
        if not ai_output and hasattr(gen_service, 'active_jobs'):
            for job in gen_service.active_jobs.values():
                if job.get('artifact_id') == body.artifact_id:
                    ai_output = job.get('artifact', {}).get('content', '')
                    artifact_type = job.get('artifact', {}).get('artifact_type', artifact_type)
                    break
    except Exception as e:
        logger.warning(f"Could not fetch artifact content: {e}")
    
    service = get_service()
    
    # Map feedback_type to validation score if not provided
    # Thumbs up = 85+, thumbs down = 60, correction = use provided score or 85
    if body.score:
        validation_score = body.score
    elif body.feedback_type == "positive":
        validation_score = 85.0  # Thumbs up = high quality
    elif body.feedback_type == "correction":
        validation_score = 85.0  # Correction = user improved it, treat as high quality
    elif body.feedback_type == "negative":
        validation_score = 60.0  # Thumbs down = lower quality
    else:
        validation_score = 70.0  # Default
    
    result = await service.record_feedback(
        artifact_id=body.artifact_id,
        artifact_type=artifact_type,
        ai_output=ai_output,
        validation_score=validation_score,
        feedback_type=body.feedback_type,
        score=body.score,
        notes=body.notes,
        corrected_output=body.corrected_content,
        context={
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Get training stats
    stats = service.get_training_stats()
    examples_collected = stats.get("total_feedback_events", 0)
    
    return FeedbackResponse(
        recorded=result.get("event_recorded", False),
        examples_collected=examples_collected,
        training_triggered=result.get("training_triggered", False),
        message=result.get("message", "Feedback processed")
    )


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_feedback_history(
    artifact_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    limit: int = 100,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get feedback history.
    
    Query parameters:
    - artifact_id: Optional artifact ID filter
    - artifact_type: Optional artifact type filter
    - limit: Maximum number of entries (default: 100)
    """
    service = get_service()
    history = service.get_feedback_history(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        limit=limit
    )
    
    return history


@router.get("/stats", response_model=Dict[str, Any])
async def get_feedback_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get feedback and training statistics."""
    service = get_service()
    stats = service.get_training_stats()
    
    return stats


@router.get("/training-ready", response_model=Dict[str, Any])
async def check_training_ready(
    artifact_type: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Check if enough feedback collected to trigger training.
    
    Query parameters:
    - artifact_type: Optional artifact type to check
    """
    service = get_service()
    readiness = service.check_training_ready(artifact_type=artifact_type)
    
    return readiness

