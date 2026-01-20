"""
Dataset Builder Service - Handles training dataset creation from feedback and repository context.
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
    DatasetBuildRequest, DatasetBuildResponse, DatasetStatsDTO,
    ArtifactType
)
from backend.services.feedback_service import get_service as get_feedback_service
from backend.core.websocket import websocket_manager, EventType

logger = logging.getLogger(__name__)

# Optional imports for dataset building (graceful degradation)
try:
    from components.finetuning_dataset_builder import FineTuningDatasetBuilder
    DATASET_BUILDER_AVAILABLE = True
except ImportError:
    DATASET_BUILDER_AVAILABLE = False
    logger.warning("Dataset builder not available. Dataset service will have limited functionality.")


class DatasetService:
    """
    Dataset builder service for creating training datasets.
    
    Features:
    - Dataset building from feedback events
    - Dataset building from repository context
    - Quality filtering and curation
    - Dataset statistics and validation
    - Multiple artifact type support
    """
    
    def __init__(self):
        """Initialize Dataset Service."""
        self.datasets: Dict[str, Dict[str, Any]] = {}
        self.datasets_file = Path("datasets.json")
        
        # Load existing datasets
        self._load_datasets()
        
        # Dataset builder is initialized lazily when needed (requires meeting_notes)
        self.dataset_builder = None
        self._dataset_builder_available = DATASET_BUILDER_AVAILABLE
        
        logger.info("Dataset Service initialized")
    
    def _load_datasets(self):
        """Load datasets from file."""
        if self.datasets_file.exists():
            try:
                with open(self.datasets_file, 'r', encoding='utf-8') as f:
                    self.datasets = json.load(f)
                logger.info(f"Loaded {len(self.datasets)} datasets")
            except Exception as e:
                logger.error(f"Error loading datasets: {e}")
    
    def _save_datasets(self):
        """Save datasets to file."""
        try:
            with open(self.datasets_file, 'w', encoding='utf-8') as f:
                json.dump(self.datasets, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving datasets: {e}")
    
    async def build_dataset(
        self,
        repo_id: str,
        budget: int,
        artifact_mix: Optional[Dict[str, int]] = None
    ) -> DatasetBuildResponse:
        """
        Build a training dataset from repository context and feedback.
        
        Args:
            repo_id: Repository identifier
            budget: Target number of examples
            artifact_mix: Optional artifact type distribution
        
        Returns:
            Dataset build response with statistics
        """
        dataset_id = str(uuid.uuid4())
        
        # Use dataset builder if available
        if self.dataset_builder:
            try:
                # Build dataset using the comprehensive builder
                result = await self._build_with_builder(
                    repo_id=repo_id,
                    budget=budget,
                    artifact_mix=artifact_mix or {}
                )
                
                # Calculate statistics
                examples = result.get("examples", [])
                stats = self._calculate_stats(examples)
                
                # Store dataset
                self.datasets[dataset_id] = {
                    "dataset_id": dataset_id,
                    "repo_id": repo_id,
                    "budget": budget,
                    "artifact_mix": artifact_mix or {},
                    "examples": examples,
                    "stats": stats,
                    "created_at": datetime.now().isoformat()
                }
                self._save_datasets()
                
                logger.info(f"Built dataset {dataset_id} with {len(examples)} examples")
                
                return DatasetBuildResponse(
                    dataset_id=dataset_id,
                    stats=DatasetStatsDTO(**stats),
                    created_at=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error building dataset with builder: {e}", exc_info=True)
                # Fall through to basic dataset building
        
        # Fallback: Build dataset from feedback events
        return await self._build_from_feedback(
            dataset_id=dataset_id,
            repo_id=repo_id,
            budget=budget,
            artifact_mix=artifact_mix or {}
        )
    
    async def _build_with_builder(
        self,
        repo_id: str,
        budget: int,
        artifact_mix: Dict[str, int]
    ) -> Dict[str, Any]:
        """Build dataset using FineTuningDatasetBuilder."""
        # This would call the actual dataset builder
        # For now, return a placeholder structure
        return {
            "examples": [],
            "note": "Dataset builder integration pending"
        }
    
    async def _build_from_feedback(
        self,
        dataset_id: str,
        repo_id: str,
        budget: int,
        artifact_mix: Dict[str, int]
    ) -> DatasetBuildResponse:
        """Build dataset from feedback events."""
        feedback_service = get_feedback_service()
        
        # Get feedback history
        history = feedback_service.get_feedback_history(limit=budget * 2)
        
        # Filter and curate examples
        examples = []
        for feedback in history:
            # Quality filter: only high-quality feedback
            validation_score = feedback.get("validation_score", 0.0)
            if validation_score < 70.0:
                continue
            
            # Check artifact mix if specified
            artifact_type = feedback.get("artifact_type", "")
            if artifact_mix:
                artifact_count = sum(
                    1 for e in examples if e.get("artifact_type") == artifact_type
                )
                if artifact_count >= artifact_mix.get(artifact_type, budget):
                    continue
            
            # Convert to training example format
            example = {
                "instruction": f"Generate {artifact_type}",
                "input": feedback.get("input_data", ""),
                "output": feedback.get("corrected_output") or feedback.get("ai_output", ""),
                "quality_score": validation_score
            }
            examples.append(example)
            
            if len(examples) >= budget:
                break
        
        # Calculate statistics
        stats = self._calculate_stats(examples)
        
        # Store dataset
        self.datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "repo_id": repo_id,
            "budget": budget,
            "artifact_mix": artifact_mix,
            "examples": examples,
            "stats": stats,
            "created_at": datetime.now().isoformat()
        }
        self._save_datasets()
        
        logger.info(f"Built dataset {dataset_id} from feedback with {len(examples)} examples")
        
        return DatasetBuildResponse(
            dataset_id=dataset_id,
            stats=DatasetStatsDTO(**stats),
            created_at=datetime.now()
        )
    
    def _calculate_stats(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate dataset statistics.
        
        Args:
            examples: List of training examples
        
        Returns:
            Dictionary with statistics
        """
        if not examples:
            return {
                "total_examples": 0,
                "examples_by_artifact": {},
                "average_score": 0.0,
                "quality_distribution": {}
            }
        
        # Count by artifact type
        examples_by_artifact = {}
        scores = []
        
        for example in examples:
            # Extract artifact type from instruction
            instruction = example.get("instruction", "")
            artifact_type = "unknown"
            for at in ArtifactType:
                if at.value.replace("_", " ") in instruction.lower():
                    artifact_type = at.value
                    break
            
            examples_by_artifact[artifact_type] = examples_by_artifact.get(artifact_type, 0) + 1
            
            # Collect quality scores
            quality_score = example.get("quality_score", 0.0)
            scores.append(quality_score)
        
        # Quality distribution
        quality_distribution = {
            "0-50": sum(1 for s in scores if 0 <= s < 50),
            "50-70": sum(1 for s in scores if 50 <= s < 70),
            "70-85": sum(1 for s in scores if 70 <= s < 85),
            "85-100": sum(1 for s in scores if 85 <= s <= 100)
        }
        
        return {
            "total_examples": len(examples),
            "examples_by_artifact": examples_by_artifact,
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "quality_distribution": quality_distribution
        }
    
    async def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset by ID.
        
        Args:
            dataset_id: Dataset identifier
        
        Returns:
            Dataset dictionary or None
        """
        return self.datasets.get(dataset_id)
    
    async def list_datasets(
        self,
        repo_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all datasets with optional filtering.
        
        Args:
            repo_id: Optional repository filter
        
        Returns:
            List of dataset summaries
        """
        datasets = list(self.datasets.values())
        
        if repo_id:
            datasets = [d for d in datasets if d.get("repo_id") == repo_id]
        
        # Return summaries (without full examples)
        return [
            {
                "dataset_id": d["dataset_id"],
                "repo_id": d.get("repo_id"),
                "budget": d.get("budget"),
                "stats": d.get("stats"),
                "created_at": d.get("created_at")
            }
            for d in datasets
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get dataset service statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_datasets = len(self.datasets)
        total_examples = sum(
            d.get("stats", {}).get("total_examples", 0)
            for d in self.datasets.values()
        )
        
        return {
            "total_datasets": total_datasets,
            "total_examples": total_examples,
            "dataset_builder_available": DATASET_BUILDER_AVAILABLE
        }


# Global service instance
_service: Optional[DatasetService] = None


def get_service() -> DatasetService:
    """Get or create global Dataset Service instance."""
    global _service
    if _service is None:
        _service = DatasetService()
    return _service



