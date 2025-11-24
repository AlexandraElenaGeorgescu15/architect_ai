"""
Analysis API endpoints for pattern mining and dataset building.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from typing import Optional
import logging

from backend.models.dto import UserPublic
from backend.services.analysis_service import get_service
from backend.core.auth import get_current_user
from backend.core.middleware import limiter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class PatternAnalysisRequest(BaseModel):
    """Request for pattern analysis."""
    project_root: Optional[str] = None
    include_design_patterns: bool = True
    include_anti_patterns: bool = True
    include_code_smells: bool = True
    cache_key: Optional[str] = None


class DatasetBuildRequest(BaseModel):
    """Request for dataset building."""
    feedback_file: Optional[str] = None
    include_repository_context: bool = True
    min_quality_score: float = 0.7
    max_examples: Optional[int] = None


# NOTE: The /patterns/current endpoint has been moved to backend/api/pattern_mining.py
# to resolve routing conflict. Pattern mining router owns /api/analysis/patterns/* routes.


@router.post("/patterns")
@limiter.limit("10/minute")
async def analyze_patterns(
    request: Request,
    body: PatternAnalysisRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Analyze codebase for patterns (design patterns, anti-patterns, code smells).
    
    Request body:
    {
        "project_root": "optional/path/to/project",
        "include_design_patterns": true,
        "include_anti_patterns": true,
        "include_code_smells": true,
        "cache_key": "optional-cache-key"
    }
    """
    service = get_service()
    
    try:
        result = await service.analyze_patterns(
            project_root=body.project_root,
            include_design_patterns=body.include_design_patterns,
            include_anti_patterns=body.include_anti_patterns,
            include_code_smells=body.include_code_smells,
            cache_key=body.cache_key
        )
        
        return {
            "success": True,
            "analysis": result
        }
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze patterns: {str(e)}"
        )


@router.post("/dataset")
@limiter.limit("5/minute")
async def build_dataset(
    request: Request,
    body: DatasetBuildRequest,
    background_tasks: BackgroundTasks,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Build training dataset from feedback and repository context.
    
    Request body:
    {
        "feedback_file": "optional/path/to/feedback.jsonl",
        "include_repository_context": true,
        "min_quality_score": 0.7,
        "max_examples": 1000
    }
    """
    service = get_service()
    
    try:
        # Build dataset in background
        result = await service.build_dataset(
            feedback_file=body.feedback_file,
            include_repository_context=body.include_repository_context,
            min_quality_score=body.min_quality_score,
            max_examples=body.max_examples
        )
        
        return {
            "success": True,
            "job_id": result["job_id"],
            "status": result["status"],
            "message": "Dataset building started"
        }
    except Exception as e:
        logger.error(f"Error building dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build dataset: {str(e)}"
        )


@router.get("/jobs")
async def list_analysis_jobs(
    status: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """List all analysis jobs, optionally filtered by status."""
    service = get_service()
    jobs = service.list_jobs(status=status)
    return {
        "success": True,
        "jobs": jobs,
        "count": len(jobs)
    }


@router.get("/jobs/{job_id}")
async def get_analysis_job(
    job_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get status of an analysis job."""
    service = get_service()
    job = service.get_job_status(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return {
        "success": True,
        "job": job
    }

