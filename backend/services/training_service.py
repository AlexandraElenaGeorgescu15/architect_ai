"""
Training Service - Handles model fine-tuning jobs and training queue management.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import (
    TrainingJobDTO, TrainingStatus, TrainingQueueDTO, TrainingTriggerRequest,
    ArtifactType
)
from backend.services.feedback_service import get_service as get_feedback_service
from backend.core.websocket import websocket_manager, EventType

logger = logging.getLogger(__name__)

# Optional imports for training (graceful degradation)
try:
    from components.adaptive_learning_enhanced import EnhancedAdaptiveLearningLoop
    from components.local_finetuning import LocalFineTuningSystem
    TRAINING_AVAILABLE = True
except ImportError:
    try:
        from components.adaptive_learning import AdaptiveLearningLoop
        TRAINING_AVAILABLE = True
        EnhancedAdaptiveLearningLoop = None
        LocalFineTuningSystem = None
    except ImportError:
        TRAINING_AVAILABLE = False
        logger.warning("Training components not available. Training service will have limited functionality.")


class TrainingService:
    """
    Training service for managing fine-tuning jobs.
    
    Features:
    - Training job creation and tracking
    - Training queue management
    - Automatic training triggers (50+ examples)
    - Training progress tracking
    - WebSocket progress updates
    """
    
    def __init__(self):
        """Initialize Training Service."""
        self.jobs: Dict[str, TrainingJobDTO] = {}
        self.jobs_file = Path("training_jobs.json")
        
        # Load existing jobs
        self._load_jobs()
        
        # Initialize training systems if available
        if TRAINING_AVAILABLE:
            if EnhancedAdaptiveLearningLoop:
                self.learning_loop = EnhancedAdaptiveLearningLoop()
            else:
                from components.adaptive_learning import AdaptiveLearningLoop
                self.learning_loop = AdaptiveLearningLoop()
            
            if LocalFineTuningSystem:
                self.finetuning_system = LocalFineTuningSystem()
            else:
                self.finetuning_system = None
        else:
            self.learning_loop = None
            self.finetuning_system = None
        
        logger.info("Training Service initialized")
    
    def _load_jobs(self):
        """Load training jobs from file."""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_id, job_data in data.items():
                        # Convert status string to enum
                        job_data['status'] = TrainingStatus(job_data.get('status', 'queued'))
                        # Convert artifact_type string to enum
                        if 'artifact_type' in job_data:
                            job_data['artifact_type'] = ArtifactType(job_data['artifact_type'])
                        self.jobs[job_id] = TrainingJobDTO(**job_data)
                logger.info(f"Loaded {len(self.jobs)} training jobs")
            except Exception as e:
                logger.error(f"Error loading training jobs: {e}")
    
    def _save_jobs(self):
        """Save training jobs to file."""
        try:
            data = {
                job_id: {
                    **job.model_dump(),
                    'status': job.status.value,
                    'artifact_type': job.artifact_type.value
                }
                for job_id, job in self.jobs.items()
            }
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving training jobs: {e}")
    
    async def create_training_job(
        self,
        artifact_type: ArtifactType,
        base_model: str,
        examples_count: int,
        force: bool = False
    ) -> TrainingJobDTO:
        """
        Create a new training job.
        
        Args:
            artifact_type: Type of artifact to train for
            base_model: Base model to fine-tune
            examples_count: Number of training examples
            force: Force training even if < 50 examples
        
        Returns:
            Training job DTO
        """
        # Check if we have enough examples
        if not force and examples_count < settings.training_threshold:
            raise ValueError(
                f"Insufficient examples: {examples_count} < {settings.training_threshold}. "
                "Set force=True to override."
            )
        
        job_id = str(uuid.uuid4())
        
        job = TrainingJobDTO(
            job_id=job_id,
            artifact_type=artifact_type,
            status=TrainingStatus.QUEUED,
            examples_count=examples_count,
            progress=0.0,
            base_model=base_model,
            started_at=None,
            completed_at=None,
            error=None,
            metadata={
                "created_at": datetime.now().isoformat(),
                "force": force
            }
        )
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        logger.info(f"Created training job {job_id} for {artifact_type.value} with {examples_count} examples")
        
        # Emit WebSocket event
        await websocket_manager.emit(
            room_id=job_id,
            event_type=EventType.TRAINING_QUEUED,
            data=job.model_dump_json()
        )
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[TrainingJobDTO]:
        """
        Get training job by ID.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Training job DTO or None
        """
        return self.jobs.get(job_id)
    
    async def list_jobs(
        self,
        status: Optional[TrainingStatus] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[TrainingJobDTO]:
        """
        List training jobs with optional filtering.
        
        Args:
            status: Optional status filter
            artifact_type: Optional artifact type filter
        
        Returns:
            List of training jobs
        """
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        if artifact_type:
            jobs = [j for j in jobs if j.artifact_type == artifact_type]
        
        return jobs
    
    async def get_queue_status(self) -> TrainingQueueDTO:
        """
        Get training queue status.
        
        Returns:
            Training queue DTO with queued and active jobs
        """
        queued = [j for j in self.jobs.values() if j.status == TrainingStatus.QUEUED]
        active = [
            j for j in self.jobs.values()
            if j.status in [TrainingStatus.PREPARING, TrainingStatus.TRAINING, TrainingStatus.CONVERTING]
        ]
        
        # Get examples by artifact type from finetuning pool (real + synthetic)
        try:
            from backend.services.finetuning_pool import get_pool
            pool = get_pool()
            examples_by_artifact: Dict[str, int] = {}
            # Use pool keys so we reflect all artifact types that actually have data
            for atype in pool.pools.keys():
                breakdown = pool.get_source_breakdown(atype)
                examples_by_artifact[atype] = breakdown.get("total_examples", 0)
        except Exception as e:
            logger.warning(f"Failed to load examples from finetuning pool for queue status: {e}")
            examples_by_artifact = {}
        
        return TrainingQueueDTO(
            queued_jobs=queued,
            active_jobs=active,
            examples_by_artifact=examples_by_artifact
        )
    
    async def trigger_training(
        self,
        artifact_type: ArtifactType,
        force: bool = False
    ) -> TrainingJobDTO:
        """
        Trigger training for an artifact type.
        
        Args:
            artifact_type: Artifact type to train for
            force: Force training even if < 50 examples
        
        Returns:
            Created training job
        """
        # Get examples count from finetuning pool (real + synthetic)
        try:
            from backend.services.finetuning_pool import get_pool
            pool = get_pool()
            breakdown = pool.get_source_breakdown(artifact_type.value)
            examples_count = breakdown.get("total_examples", 0)
        except Exception as e:
            logger.warning(f"Failed to load examples from finetuning pool for training: {e}")
            examples_count = 0
        
        # Get base model from routing
        from backend.services.model_service import get_service as get_model_service
        model_service = get_model_service()
        routing = model_service.get_routing_for_artifact(artifact_type)
        base_model = routing.primary_model if routing else "llama3"
        
        # Create training job
        job = await self.create_training_job(
            artifact_type=artifact_type,
            base_model=base_model,
            examples_count=examples_count,
            force=force
        )
        
        # Start training in background (would use Celery/Taskiq in production)
        # For now, we'll just mark it as queued
        logger.info(f"Training job {job.job_id} queued for {artifact_type.value}")
        
        return job
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a training job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if successful
        """
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [TrainingStatus.QUEUED, TrainingStatus.PREPARING, TrainingStatus.TRAINING]:
            job.status = TrainingStatus.CANCELLED
            job.completed_at = datetime.now()
            self._save_jobs()
            
            # Emit WebSocket event
            await websocket_manager.emit(
                room_id=job_id,
                event_type=EventType.TRAINING_ERROR,
                data=job.model_dump_json()
            )
            
            logger.info(f"Cancelled training job {job_id}")
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get training service statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_jobs = len(self.jobs)
        jobs_by_status = {}
        for status in TrainingStatus:
            jobs_by_status[status.value] = sum(
                1 for j in self.jobs.values() if j.status == status
            )
        
        jobs_by_artifact = {}
        for job in self.jobs.values():
            artifact_type = job.artifact_type.value
            jobs_by_artifact[artifact_type] = jobs_by_artifact.get(artifact_type, 0) + 1
        
        return {
            "total_jobs": total_jobs,
            "jobs_by_status": jobs_by_status,
            "jobs_by_artifact": jobs_by_artifact,
            "training_available": TRAINING_AVAILABLE
        }


# Global service instance
_service: Optional[TrainingService] = None


def get_service() -> TrainingService:
    """Get or create global Training Service instance."""
    global _service
    if _service is None:
        _service = TrainingService()
    return _service



