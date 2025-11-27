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
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis/patterns", tags=["pattern-mining"])

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
    
    # Estimate duration (rough: 1 second per file)
    directory = Path(body.repo_id) if Path(body.repo_id).exists() else Path(".")
    files = list(directory.rglob("*.py")) if directory.exists() else []
    estimated_seconds = len(files) // 10  # Rough estimate
    
    # Store job
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "repo_id": body.repo_id,
        "detectors": body.detectors,
        "created_at": datetime.now().isoformat()
    }
    
    # Run analysis in background
    def analyze_task():
        try:
            _jobs[job_id]["status"] = "running"
            miner = get_miner()
            directory = Path(body.repo_id) if Path(body.repo_id).exists() else Path(".")
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

