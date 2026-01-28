"""
Project Target API - Shows and controls which project is being analyzed.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from backend.core.config import settings
from backend.core.middleware import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project-target", tags=["project-target"])


class ProjectInfo(BaseModel):
    """Information about a detected project."""
    path: str
    name: str
    score: int
    is_selected: bool
    markers: List[str]


class TargetResponse(BaseModel):
    """Response for target project info."""
    current_target: str
    tool_directory: str
    available_projects: List[ProjectInfo]
    configured_path: Optional[str]


class SetTargetRequest(BaseModel):
    """Request to set target project."""
    path: str





@router.get("/", response_model=TargetResponse)
async def get_target_info():
    """
    Get information about the current target project.
    """
    from backend.utils.tool_detector import detect_tool_directory
    from backend.utils.target_project import (
        get_available_projects, 
        get_target_project_path,
        score_directory,
        detect_project_markers
    )
    
    tool_dir = detect_tool_directory()
    current_target = get_target_project_path()
    
    # Get all potential projects
    available_dirs = get_available_projects()
    
    projects = []
    
    for d in available_dirs:
        # Calculate score using unified logic
        score = score_directory(d)
        
        # Get markers
        markers = detect_project_markers(d)
        
        is_target = current_target and d.resolve() == current_target.resolve()
        
        projects.append(ProjectInfo(
            name=d.name,
            path=str(d),
            score=score,
            is_selected=is_target,
            markers=markers
        ))
    
    # Check if target is indexed
    files_indexed = 0
    projects.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"📋 [PROJECT_TARGET] Returning {len(projects)} available projects. Current: {current_target}")
    
    return TargetResponse(
        current_target=str(current_target) if current_target else "",
        tool_directory=str(tool_dir) if tool_dir else "",
        available_projects=projects,
        configured_path=settings.target_repo_path
    )


@router.post("/set")
@limiter.limit("10/minute")
async def set_target_project(request: Request, body: SetTargetRequest):
    """
    Set the target project path.
    
    This sets the TARGET_REPO_PATH setting.
    Note: For persistence, add TARGET_REPO_PATH to your .env file.
    """
    target_path = Path(body.path)
    
    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {body.path}"
        )
    
    if not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {body.path}"
        )
    
    # Update settings (runtime only - for persistence, use .env)
    settings.target_repo_path = body.path
    
    logger.info(f"✅ [PROJECT_TARGET] Set target project to: {body.path}")
    
    return {
        "success": True,
        "message": f"Target project set to: {body.path}",
        "target_path": body.path,
        "note": "For persistence, add TARGET_REPO_PATH={path} to your .env file"
    }


@router.post("/clear-cache")
@limiter.limit("5/minute")
async def clear_analysis_cache(request: Request):
    """
    Clear all cached analysis data (Knowledge Graph, Pattern Mining).
    
    Call this after changing the target project to force re-analysis.
    """
    cache_dir = Path("outputs/.cache")
    cleared_files = []
    
    if cache_dir.exists():
        for cache_file in cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cleared_files.append(cache_file.name)
                logger.info(f"🗑️ [CACHE] Deleted: {cache_file}")
            except Exception as e:
                logger.warning(f"Failed to delete {cache_file}: {e}")
    
    return {
        "success": True,
        "message": f"Cleared {len(cleared_files)} cache files",
        "cleared_files": cleared_files
    }

