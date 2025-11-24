"""
Dataset Builder API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging

from datetime import datetime
import uuid
from backend.models.dto import (
    DatasetBuildRequest, DatasetBuildResponse, DatasetStatsDTO
)
from backend.services.dataset_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.post("/build", response_model=DatasetBuildResponse, summary="Build a training dataset")
@limiter.limit("2/minute")
async def build_dataset(
    request: Request,
    body: DatasetBuildRequest,
    background_tasks: BackgroundTasks,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Build a training dataset from repository context and feedback.
    
    This is a long-running operation and runs in the background.
    """
    service = get_service()
    
    # Start dataset building in background
    background_tasks.add_task(
        service.build_dataset,
        repo_id=body.repo_id,
        budget=body.budget,
        artifact_mix=body.artifact_mix
    )
    
    # For now, return immediately (in production, would return job ID)
    # In a real implementation, this would create a job and return job_id
    dataset_id = str(uuid.uuid4())
    
    return DatasetBuildResponse(
        dataset_id=dataset_id,
        stats=DatasetStatsDTO(
            total_examples=0,
            examples_by_artifact={},
            average_score=0.0,
            quality_distribution={}
        ),
        created_at=datetime.now()
    )


@router.get("/{dataset_id}", summary="Get dataset details")
async def get_dataset(
    dataset_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get detailed information about a specific dataset."""
    service = get_service()
    dataset = await service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    return dataset


@router.get("/", summary="List all datasets")
async def list_datasets(
    repo_id: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List all datasets with optional filtering.
    
    Query parameters:
    - repo_id: Optional repository filter
    """
    service = get_service()
    datasets = await service.list_datasets(repo_id=repo_id)
    return datasets


@router.get("/stats", summary="Get dataset service statistics")
async def get_dataset_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get statistics about datasets and the dataset builder service."""
    service = get_service()
    stats = service.get_stats()
    return {"success": True, "stats": stats}

