"""
Analysis Service - Combines Pattern Mining and Dataset Builder
Handles code analysis, pattern detection, and training dataset creation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.pattern_mining import get_miner
from backend.core.config import settings
from backend.core.cache import get_cache_manager
from backend.utils.tool_detector import get_user_project_directories

logger = logging.getLogger(__name__)

# Import dataset builder
try:
    from components.finetuning_dataset_builder import FineTuningDatasetBuilder
    DATASET_BUILDER_AVAILABLE = True
except ImportError:
    DATASET_BUILDER_AVAILABLE = False
    logger.warning("FineTuningDatasetBuilder not available. Dataset creation will be limited.")


class AnalysisService:
    """
    Analysis service for code analysis and dataset building.
    
    Features:
    - Pattern mining (design patterns, anti-patterns, code smells)
    - Dataset building from feedback and repository context
    - Job queue management
    - Analysis caching
    - Progress tracking
    """
    
    def __init__(self):
        """Initialize Analysis Service."""
        self.pattern_miner = get_miner()
        self.dataset_builder = None  # Initialized on-demand with meeting_notes
        self.cache = get_cache_manager()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Analysis Service initialized")
        
        # Store last analysis result for quick retrieval
        self.last_analysis: Optional[Dict[str, Any]] = None
    
    async def get_current_patterns(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent pattern analysis results.
        
        Returns:
            Last analysis results or None if no analysis has been run
        """
        if self.last_analysis:
            return self.last_analysis
        
        # Try to load from cache
        try:
            cached = await self.cache.get_async("last_pattern_analysis")
            if cached:
                self.last_analysis = cached
                return cached
        except Exception as e:
            logger.warning(f"Could not load cached analysis: {e}")
        
        return None
    
    async def analyze_patterns(
        self,
        project_root: Optional[str] = None,
        include_design_patterns: bool = True,
        include_anti_patterns: bool = True,
        include_code_smells: bool = True,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze codebase for patterns.
        
        Args:
            project_root: Optional project root path
            include_design_patterns: Whether to detect design patterns
            include_anti_patterns: Whether to detect anti-patterns
            include_code_smells: Whether to detect code smells
            cache_key: Optional cache key for results
        
        Returns:
            Analysis results with patterns, metrics, and recommendations
        """
        # Check cache
        if cache_key:
            cached = await self.cache.get_async(cache_key)
            if cached:
                logger.info(f"Returning cached analysis for {cache_key}")
                return cached
        
        # Get project directories
        if project_root:
            project_path = Path(project_root)
        else:
            user_dirs = get_user_project_directories()
            project_path = user_dirs[0] if user_dirs else Path.cwd()
        
        # Run pattern mining
        analysis = await asyncio.to_thread(
            self.pattern_miner.analyze_project,
            project_path,
            include_design_patterns=include_design_patterns,
            include_anti_patterns=include_anti_patterns,
            include_code_smells=include_code_smells
        )
        
        result = {
            "analysis_id": f"analysis_{uuid.uuid4().hex[:8]}",
            "project_root": str(project_path),
            "patterns": [
                {
                    "name": p.name,
                    "type": p.pattern_type,
                    "description": p.description,
                    "frequency": p.frequency,
                    "severity": p.severity,
                    "files": p.files[:10],  # Limit file list
                    "suggestions": p.suggestions
                }
                for p in analysis.patterns
            ],
            "metrics": analysis.metrics,
            "recommendations": analysis.recommendations,
            "code_quality_score": analysis.code_quality_score,
            "created_at": datetime.now().isoformat()
        }
        
        # Store as last analysis
        self.last_analysis = result
        await self.cache.set_async("last_pattern_analysis", result, ttl=3600)
        
        # Cache result
        if cache_key:
            await self.cache.set_async(cache_key, result, ttl=3600)  # 1 hour
        
        return result
    
    async def build_dataset(
        self,
        feedback_file: Optional[str] = None,
        include_repository_context: bool = True,
        min_quality_score: float = 0.7,
        max_examples: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build training dataset from feedback and repository context.
        
        Args:
            feedback_file: Optional path to feedback JSONL file
            include_repository_context: Whether to include repository context
            min_quality_score: Minimum quality score for examples
            max_examples: Maximum number of examples to include
        
        Returns:
            Dataset information and statistics
        """
        if not self.dataset_builder:
            raise ValueError("Dataset builder not available")
        
        job_id = f"dataset_{uuid.uuid4().hex[:8]}"
        
        self.active_jobs[job_id] = {
            "job_id": job_id,
            "status": "in_progress",
            "progress": 0.0,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            # Get project root
            user_dirs = get_user_project_directories()
            project_root = user_dirs[0] if user_dirs else Path.cwd()
            
            # Build dataset
            dataset = await asyncio.to_thread(
                self.dataset_builder.build_dataset,
                project_root=str(project_root),
                feedback_file=feedback_file,
                include_repository_context=include_repository_context,
                min_quality_score=min_quality_score,
                max_examples=max_examples
            )
            
            result = {
                "job_id": job_id,
                "status": "completed",
                "dataset_path": str(dataset.get("output_path", "")),
                "statistics": dataset.get("statistics", {}),
                "created_at": datetime.now().isoformat()
            }
            
            self.active_jobs[job_id].update({
                "status": "completed",
                "progress": 100.0,
                "result": result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error building dataset: {e}", exc_info=True)
            self.active_jobs[job_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an analysis job."""
        return self.active_jobs.get(job_id)
    
    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all analysis jobs, optionally filtered by status."""
        jobs = list(self.active_jobs.values())
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        return jobs


# Singleton instance
_analysis_service: Optional[AnalysisService] = None


def get_service() -> AnalysisService:
    """Get singleton Analysis Service instance."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service

