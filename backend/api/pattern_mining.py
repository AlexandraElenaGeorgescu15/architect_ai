"""
Pattern Mining API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.models.dto import PatternMiningRequest, PatternMiningResponse, PatternReportDTO
from backend.services.pattern_mining import get_miner
from backend.core.middleware import limiter
from backend.core.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis/patterns", tags=["pattern-mining"])


def _get_target_directory(provided_path: Optional[str] = None) -> Path:
    """
    Get the target directory for analysis.
    Priority: provided_path > settings.target_repo_path > user project directories
    
    IMPORTANT: This should NEVER return the Architect.AI tool directory.
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    # If path is provided and exists, use it
    if provided_path:
        provided = Path(provided_path)
        if provided.exists():
            logger.info(f"Using provided directory: {provided}")
            return provided
    
    # Use configured target repo path if set
    if settings.target_repo_path:
        target = Path(settings.target_repo_path)
        if target.exists():
            logger.info(f"Using configured target_repo_path: {target}")
            return target
    
    # Get user project directories (siblings of tool)
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    logger.info(f"🔍 [TARGET_DIR] Tool directory: {tool_dir}")
    logger.info(f"🔍 [TARGET_DIR] Found {len(user_dirs)} sibling directories")
    
    if user_dirs:
        # Score directories to find the most likely "main" project
        scored_dirs = []
        for d in user_dirs:
            if d == tool_dir or not d.exists():
                continue
            
            score = 0
            name_lower = d.name.lower()
            
            # Deprioritize utility/shared directories
            if name_lower in ['agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs']:
                score -= 100
            
            # Prioritize directories with project markers
            if (d / 'package.json').exists():
                score += 50  # Node.js/Angular/React project
            if (d / 'angular.json').exists():
                score += 60  # Angular project (higher priority)
            if (d / 'pom.xml').exists() or (d / 'build.gradle').exists():
                score += 50  # Java project
            if (d / 'Cargo.toml').exists():
                score += 50  # Rust project
            if (d / 'go.mod').exists():
                score += 50  # Go project
            if (d / 'requirements.txt').exists() or (d / 'setup.py').exists():
                score += 40  # Python project
            if (d / '.csproj').exists() or any(d.glob('*.csproj')):
                score += 50  # .NET project
            if any(d.glob('*.sln')):
                score += 55  # .NET solution
            if (d / 'src').is_dir():
                score += 30  # Has src directory
            if (d / 'frontend').is_dir():
                score += 20  # Has frontend
            if (d / 'backend').is_dir():
                score += 20  # Has backend
            
            # Prioritize directories with "project" or "final" in name
            if 'project' in name_lower or 'final' in name_lower:
                score += 25
            
            scored_dirs.append((d, score))
            logger.debug(f"🔍 [TARGET_DIR] Scored {d.name}: {score}")
        
        if scored_dirs:
            # Sort by score descending and pick the best
            scored_dirs.sort(key=lambda x: x[1], reverse=True)
            best_dir, best_score = scored_dirs[0]
            logger.info(f"✅ [TARGET_DIR] Selected user project: {best_dir} (score: {best_score})")
            return best_dir
    
    # Fallback to parent of tool (the "mother project")
    if tool_dir:
        parent = tool_dir.parent
        logger.warning(f"⚠️ [TARGET_DIR] Falling back to tool parent directory: {parent}")
        return parent
    
    # Last resort - this should NOT happen
    logger.error("❌ [TARGET_DIR] Could not determine target directory - falling back to cwd (THIS MAY BE WRONG)")
    return Path.cwd()

# In-memory job storage (replace with database in production)
_jobs: Dict[str, Dict[str, Any]] = {}


@router.get("/current")
async def get_current_patterns():
    """
    Get the most recent pattern analysis results.
    Returns the cached pattern mining results if available.
    """
    try:
        # First try to get from analysis service (which includes cached results)
        from backend.services.analysis_service import get_service
        
        service = get_service()
        result = await service.get_current_patterns()
        
        if result and result.get("patterns"):
            # Analysis service returned data - use it
            return {
                "success": True,
                "patterns": result.get("patterns", []),
                "summary": result.get("summary", {
                    "total_patterns": len(result.get("patterns", [])),
                    "confidence_avg": 0
                })
            }
        
        # Fallback to pattern miner directly
        miner = get_miner()
        
        if not miner.patterns_detected:
            try:
                miner.load_cached_results()
            except Exception as e:
                logger.debug(f"Could not load cached results: {e}")
        
        if not miner.patterns_detected:
            logger.info("No pattern analysis available")
            return {
                "success": False,
                "patterns": [],
                "summary": {
                    "total_patterns": 0,
                    "confidence_avg": 0
                }
            }
        
        # Extract patterns from miner
        patterns = []
        total_confidence = 0
        
        for pattern in miner.patterns_detected[:50]:  # Limit to first 50
            pattern_data = {
                "id": f"{pattern.pattern_name}_{pattern.location}",
                "name": pattern.details.get("class_name") or pattern.details.get("function_name") or "Unnamed",
                "pattern_type": pattern.pattern_name,
                "file": pattern.location.split(':')[0] if hasattr(pattern, 'location') else "",
                "confidence": pattern.confidence if hasattr(pattern, 'confidence') else 0.5,
                "description": pattern.details.get("description", f"{pattern.pattern_name} pattern detected") if hasattr(pattern, 'details') else ""
            }
            patterns.append(pattern_data)
            total_confidence += pattern_data["confidence"]
        
        avg_confidence = total_confidence / len(patterns) if patterns else 0
        
        return {
            "success": True,
            "patterns": patterns,
            "summary": {
                "total_patterns": len(miner.patterns_detected),
                "confidence_avg": avg_confidence
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting patterns: {e}", exc_info=True)
        return {
            "success": False,
            "patterns": [],
            "summary": {
                "total_patterns": 0,
                "confidence_avg": 0
            },
            "error": str(e)
        }


@router.post("/", response_model=PatternMiningResponse)
@limiter.limit("5/minute")
async def start_pattern_mining(
    request: Request,
    body: PatternMiningRequest,
    background_tasks: BackgroundTasks
):
    """
    Start pattern mining analysis.
    
    Request body:
    {
        "repo_id": "user-repo-123",
        "detectors": ["singleton", "factory", "observer"]  # optional
    }
    """
    job_id = f"pattern_mining_{uuid.uuid4().hex[:8]}"
    
    # Get target directory - use user project, not the tool itself
    directory = _get_target_directory(body.repo_id if body.repo_id else None)
    logger.info(f"🔍 [PATTERN] Mining patterns from: {directory}")
    
    # Estimate duration (rough: 1 second per file)
    files = list(directory.rglob("*.py")) if directory.exists() else []
    estimated_seconds = len(files) // 10  # Rough estimate
    
    # Store job
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "repo_id": str(directory),  # Store actual directory being analyzed
        "detectors": body.detectors,
        "created_at": datetime.now().isoformat()
    }
    
    # Run analysis in background
    def analyze_task():
        try:
            _jobs[job_id]["status"] = "running"
            miner = get_miner()
            result = miner.analyze_directory(directory, recursive=True, detectors=body.detectors)
            miner.cache_results()
            
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["result"] = result
            _jobs[job_id]["completed_at"] = datetime.now().isoformat()
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)
            logger.error(f"Pattern mining job {job_id} failed: {e}", exc_info=True)
    
    background_tasks.add_task(analyze_task)
    
    return PatternMiningResponse(
        job_id=job_id,
        status="queued",
        estimated_duration_seconds=estimated_seconds
    )


@router.get("/{job_id}", response_model=PatternReportDTO)
async def get_pattern_mining_results(job_id: str):
    """
    Get pattern mining results.
    
    Path parameters:
    - job_id: Job identifier
    """
    if job_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = _jobs[job_id]
    
    if job["status"] == "queued" or job["status"] == "running":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Job {job_id} is still {job['status']}"
        )
    
    if job["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=job.get("error", "Analysis failed")
        )
    
    result = job.get("result", {})
    
    return PatternReportDTO(
        patterns_detected=result.get("patterns_detected", []),
        code_smells=result.get("code_smells", []),
        security_issues=result.get("security_issues", []),
        statistics=result.get("statistics", {})
    )


@router.get("/", response_model=List[dict])
async def list_pattern_mining_jobs():
    """List all pattern mining jobs."""
    return list(_jobs.values())


@router.post("/analyze-file", response_model=dict)
@limiter.limit("30/minute")
async def analyze_single_file(request: Request, body: dict):
    """
    Analyze a single file for patterns.
    
    Request body:
    {
        "file_path": "/path/to/file.py"
    }
    """
    file_path = Path(body.get("file_path", ""))
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )
    
    miner = get_miner()
    result = miner.analyze_file(file_path)
    
    return result

