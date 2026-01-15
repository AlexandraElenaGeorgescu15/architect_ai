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


def _detect_project_markers(directory: Path) -> List[str]:
    """Detect project type markers in a directory."""
    markers = []
    if (directory / 'package.json').exists():
        markers.append('Node.js')
    if (directory / 'angular.json').exists():
        markers.append('Angular')
    if (directory / 'pom.xml').exists():
        markers.append('Maven')
    if (directory / 'build.gradle').exists():
        markers.append('Gradle')
    if (directory / 'requirements.txt').exists():
        markers.append('Python')
    if (directory / 'Cargo.toml').exists():
        markers.append('Rust')
    if (directory / 'go.mod').exists():
        markers.append('Go')
    # .NET detection - check root, 1 level, and 2 levels deep for .csproj/.sln
    # .NET solutions often have nested project structures
    has_csproj = (any(directory.glob('*.csproj')) or 
                  any(directory.glob('*/*.csproj')) or 
                  any(directory.glob('*/*/*.csproj')))
    has_sln = (any(directory.glob('*.sln')) or 
               any(directory.glob('*/*.sln')) or 
               any(directory.glob('*/*/*.sln')))
    if has_csproj:
        markers.append('.NET')
    if has_sln:
        markers.append('.NET Solution')
    if (directory / 'src').is_dir():
        markers.append('Has src/')
    if (directory / 'frontend').is_dir():
        markers.append('Has frontend/')
    if (directory / 'backend').is_dir():
        markers.append('Has backend/')
    return markers


# Folders that should never appear as user projects (internal/utility folders)
EXCLUDED_FOLDER_NAMES = {
    'agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs',
    'node_modules', '__pycache__', '.git', 'dist', 'build', 'bin', 'obj',
    'archive', 'backup', 'temp', 'tmp', 'cache', '.cache', 'logs',
}


def _is_excluded_folder(directory: Path) -> bool:
    """Check if a folder should be excluded from the project list."""
    name_lower = directory.name.lower()
    return name_lower in EXCLUDED_FOLDER_NAMES


def _score_directory(directory: Path) -> int:
    """Score a directory to determine if it's a main project."""
    score = 0
    name_lower = directory.name.lower()
    
    # Already excluded by _is_excluded_folder, but penalize just in case
    if name_lower in EXCLUDED_FOLDER_NAMES:
        score -= 100
    
    if (directory / 'package.json').exists():
        score += 50
    if (directory / 'angular.json').exists():
        score += 60
    if (directory / 'pom.xml').exists() or (directory / 'build.gradle').exists():
        score += 50
    if (directory / 'Cargo.toml').exists():
        score += 50
    if (directory / 'go.mod').exists():
        score += 50
    if (directory / 'requirements.txt').exists() or (directory / 'setup.py').exists():
        score += 40
    # .NET - check recursively up to 2 levels
    if any(directory.glob('*.csproj')) or any(directory.glob('*/*.csproj')) or any(directory.glob('*/*/*.csproj')):
        score += 50
    if any(directory.glob('*.sln')) or any(directory.glob('*/*.sln')) or any(directory.glob('*/*/*.sln')):
        score += 55
    if (directory / 'src').is_dir():
        score += 30
    if (directory / 'frontend').is_dir():
        score += 20
    if (directory / 'backend').is_dir():
        score += 20
    if 'project' in name_lower or 'final' in name_lower:
        score += 25
    
    return score


def _get_current_target() -> Path:
    """Get the currently selected target directory."""
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    # Priority 1: Configured path
    if settings.target_repo_path:
        target = Path(settings.target_repo_path)
        if target.exists():
            return target
    
    # Priority 2: Auto-detection
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    scored_dirs = []
    for d in user_dirs:
        # Skip tool directory, non-existent, and excluded folder names
        if d == tool_dir or not d.exists() or _is_excluded_folder(d):
            continue
        score = _score_directory(d)
        scored_dirs.append((d, score))
    
    if scored_dirs:
        scored_dirs.sort(key=lambda x: x[1], reverse=True)
        return scored_dirs[0][0]
    
    if tool_dir:
        return tool_dir.parent
    
    return Path.cwd()


@router.get("/", response_model=TargetResponse)
async def get_target_info():
    """
    Get information about the current target project and available alternatives.
    
    This helps users understand which project Architect.AI is analyzing.
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    tool_dir = detect_tool_directory()
    current_target = _get_current_target()
    user_dirs = get_user_project_directories()
    
    # Build list of available projects
    projects = []
    for d in user_dirs:
        # Skip tool directory, non-existent, and excluded folder names (like 'agents')
        if d == tool_dir or not d.exists() or _is_excluded_folder(d):
            continue
        
        score = _score_directory(d)
        markers = _detect_project_markers(d)
        
        projects.append(ProjectInfo(
            path=str(d),
            name=d.name,
            score=score,
            is_selected=(d == current_target),
            markers=markers
        ))
    
    # Sort by score
    projects.sort(key=lambda x: x.score, reverse=True)
    
    return TargetResponse(
        current_target=str(current_target),
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

