"""
Training API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging

from backend.models.dto import (
    TrainingJobDTO, TrainingQueueDTO, TrainingTriggerRequest,
    TrainingStatus, ArtifactType
)
from backend.services.training_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["Training"])


@router.get("/jobs", response_model=List[TrainingJobDTO], summary="List all training jobs")
async def list_training_jobs(
    status: Optional[TrainingStatus] = None,
    artifact_type: Optional[ArtifactType] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List all training jobs with optional filtering.
    
    Query parameters:
    - status: Optional status filter (queued, preparing, training, completed, failed, cancelled)
    - artifact_type: Optional artifact type filter
    """
    service = get_service()
    jobs = await service.list_jobs(status=status, artifact_type=artifact_type)
    return jobs


@router.get("/jobs/{job_id}", response_model=TrainingJobDTO, summary="Get training job details")
async def get_training_job(
    job_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get detailed information about a specific training job."""
    service = get_service()
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training job not found")
    return job


@router.post("/trigger", response_model=TrainingJobDTO, summary="Trigger training for an artifact type")
@limiter.limit("5/minute")
async def trigger_training(
    request: Request,
    body: TrainingTriggerRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Trigger training for a specific artifact type.
    
    This will:
    1. Check if enough examples are collected (50+ by default)
    2. Create a training job
    3. Queue it for execution
    
    Set force=True to override the example threshold.
    """
    service = get_service()
    
    try:
        job = await service.trigger_training(
            artifact_type=body.artifact_type,
            force=body.force
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/queue", response_model=TrainingQueueDTO, summary="Get training queue status")
async def get_training_queue(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get the current training queue status including queued and active jobs."""
    service = get_service()
    queue = await service.get_queue_status()
    return queue


@router.post("/jobs/{job_id}/cancel", summary="Cancel a training job")
async def cancel_training_job(
    job_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Cancel a queued or running training job."""
    service = get_service()
    success = await service.cancel_job(job_id)
    
    if success:
        return {"message": f"Training job {job_id} cancelled"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} cannot be cancelled (not in cancellable state)"
        )


@router.get("/stats", summary="Get training service statistics")
async def get_training_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get statistics about training jobs and service status."""
    service = get_service()
    stats = service.get_stats()
    return {"success": True, "stats": stats}



