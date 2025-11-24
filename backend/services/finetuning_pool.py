"""
Finetuning Pool Service - Collects high-quality examples for automatic finetuning.

Features:
- Collects examples with 85+ validation scores
- Groups examples by artifact type
- Auto-triggers finetuning when 50 examples collected
- Tracks finetuning progress
- Maps finetuned models to artifact types
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import ArtifactType

logger = logging.getLogger(__name__)

# Optional imports for finetuning
try:
    from components.finetuning_dataset_builder import FineTuningDatasetBuilder
    from components.ollama_finetuning import OllamaFinetuningManager
    FINETUNING_AVAILABLE = True
except ImportError:
    FINETUNING_AVAILABLE = False
    logger.warning("Finetuning components not available. Finetuning pool will be limited.")


class FinetuningPool:
    """
    Manages the pool of high-quality examples for finetuning.
    
    Collects examples with 85+ validation scores and automatically
    triggers finetuning when enough examples are collected.
    """
    
    def __init__(self):
        """Initialize Finetuning Pool."""
        # Use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.pool_dir = project_root / "data" / "finetuning_pool"
        self.pool_dir.mkdir(parents=True, exist_ok=True)
        
        # Per-artifact-type pools
        self.pools: Dict[str, List[Dict[str, Any]]] = {}
        
        # Finetuning thresholds
        self.incremental_finetuning_threshold = 50  # Examples for incremental finetuning
        self.major_finetuning_threshold = 2000  # Examples for major finetuning (user-triggered)
        self.min_score_threshold = 85.0  # Minimum validation score to include
        
        # Load existing pools
        self._load_pools()
        
        # Finetuning manager
        self.finetuning_manager = OllamaFinetuningManager() if FINETUNING_AVAILABLE else None
        
        # 🔧 FIX: Initialize dataset builder (was None, causing auto-finetuning to fail)
        try:
            if FINETUNING_AVAILABLE:
                self.dataset_builder = FineTuningDatasetBuilder(
                    project_root=project_root,
                    output_dir=project_root / "data" / "finetuning_datasets"
                )
                logger.info("Dataset builder initialized successfully")
            else:
                self.dataset_builder = None
                logger.warning("Dataset builder not available - finetuning components missing")
        except Exception as e:
            logger.error(f"Error initializing dataset builder: {e}")
            self.dataset_builder = None
        
        logger.info("Finetuning Pool initialized")
    
    def _load_pools(self):
        """Load existing pools from disk."""
        for artifact_type in ArtifactType:
            pool_file = self.pool_dir / f"{artifact_type.value}_pool.json"
            if pool_file.exists():
                try:
                    with open(pool_file, 'r', encoding='utf-8') as f:
                        self.pools[artifact_type.value] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading pool for {artifact_type.value}: {e}")
                    self.pools[artifact_type.value] = []
            else:
                self.pools[artifact_type.value] = []
    
    def _save_pool(self, artifact_type: str):
        """Save pool for an artifact type to disk."""
        pool_file = self.pool_dir / f"{artifact_type}_pool.json"
        try:
            with open(pool_file, 'w', encoding='utf-8') as f:
                json.dump(self.pools.get(artifact_type, []), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving pool for {artifact_type}: {e}")
    
    def add_example(
        self,
        artifact_type: str,
        content: str,
        meeting_notes: str,
        validation_score: float,
        model_used: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add an example to the finetuning pool if it meets quality threshold.
        
        Args:
            artifact_type: Type of artifact
            content: Generated content
            meeting_notes: Meeting notes used for generation
            validation_score: Validation score (must be >= 85.0)
            model_used: Model that generated the content
            context: Optional additional context
        
        Returns:
            True if example was added, False if score too low
        """
        # Quality gate: only accept 85+ scores
        if validation_score < self.min_score_threshold:
            logger.debug(f"Example rejected: score {validation_score:.1f} < {self.min_score_threshold}")
            return False
        
        # Initialize pool for artifact type if needed
        if artifact_type not in self.pools:
            self.pools[artifact_type] = []
        
        # Create example entry
        example = {
            "artifact_type": artifact_type,
            "content": content,
            "meeting_notes": meeting_notes,
            "validation_score": validation_score,
            "model_used": model_used,
            "context": context or {},
            "added_at": datetime.now().isoformat()
        }
        
        # Add to pool
        self.pools[artifact_type].append(example)
        self._save_pool(artifact_type)
        
        pool_size = len(self.pools[artifact_type])
        logger.info(f"Added example to {artifact_type} pool (score: {validation_score:.1f}, total: {pool_size})")
        
        # Get source breakdown for smart decisions
        breakdown = self.get_source_breakdown(artifact_type)
        
        # Check if we should trigger incremental finetuning (auto-triggered at 50)
        if pool_size >= self.incremental_finetuning_threshold:
            logger.info(f"Pool for {artifact_type} reached incremental threshold ({pool_size} >= {self.incremental_finetuning_threshold})")
            logger.info(f"Training data: {breakdown['real_examples']} real + {breakdown['synthetic_examples']} synthetic = {breakdown['total_examples']} total ({breakdown['synthetic_percentage']}% synthetic)")
            asyncio.create_task(self._trigger_finetuning(artifact_type, incremental=True))
        
        # Check if graduation to pure real data is possible
        elif breakdown['ready_for_graduation']:
            logger.info(f"🎓 {artifact_type} ready for graduation: {breakdown['real_examples']} real examples (can remove {breakdown['synthetic_examples']} synthetic)")
        
        # Check if bootstrap is needed
        elif breakdown['needs_bootstrap'] and validation_score >= self.min_score_threshold:
            logger.info(f"⚠️  {artifact_type} has low training data: {pool_size} examples (bootstrap recommended)")
        
        return True
    
    async def _trigger_finetuning(self, artifact_type: str, incremental: bool = True):
        """
        Trigger finetuning for an artifact type when threshold is reached.
        
        Args:
            artifact_type: Type of artifact to finetune for
            incremental: If True, uses incremental threshold (50), else major (2000)
        """
        if not FINETUNING_AVAILABLE:
            logger.warning("Finetuning components not available, cannot trigger finetuning")
            return
        
        pool = self.pools.get(artifact_type, [])
        threshold = self.incremental_finetuning_threshold if incremental else self.major_finetuning_threshold
        if len(pool) < threshold:
            logger.warning(f"Pool for {artifact_type} has {len(pool)} examples, need {threshold}")
            return
        
        try:
            logger.info(f"Starting finetuning for {artifact_type} with {len(pool)} examples...")
            
            # Build dataset from pool
            if self.dataset_builder:
                dataset_path = await asyncio.to_thread(
                    self.dataset_builder.create_dataset_from_examples,
                    pool,
                    artifact_type
                )
                logger.info(f"Dataset created at {dataset_path}")
            else:
                logger.warning("Dataset builder not available, skipping dataset creation")
                return
            
            # Get model to finetune (from model routing)
            from backend.services.model_service import get_service as get_model_service
            model_service = get_model_service()
            routing = model_service.get_routing_for_artifact(ArtifactType(artifact_type))
            
            if not routing or not routing.primary_model:
                logger.warning(f"No model routing found for {artifact_type}, cannot finetune")
                return
            
            model_name = routing.primary_model
            
            # Start finetuning
            if self.finetuning_manager:
                job_id = await self.finetuning_manager.start_finetuning(
                    model_name=model_name,
                    dataset_path=dataset_path,
                    artifact_type=artifact_type
                )
                logger.info(f"Finetuning job started: {job_id} for {artifact_type}")
            else:
                logger.warning("Finetuning manager not available, cannot start finetuning")
            
        except Exception as e:
            logger.error(f"Error triggering finetuning for {artifact_type}: {e}", exc_info=True)
    
    def get_pool_stats(self, artifact_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the finetuning pool.
        
        Args:
            artifact_type: Optional artifact type to filter by
        
        Returns:
            Dictionary with pool statistics
        """
        if artifact_type:
            pool = self.pools.get(artifact_type, [])
            return {
                "artifact_type": artifact_type,
                "count": len(pool),
                "incremental_threshold": self.incremental_finetuning_threshold,
                "major_threshold": self.major_finetuning_threshold,
                "ready_for_incremental": len(pool) >= self.incremental_finetuning_threshold,
                "ready_for_major": len(pool) >= self.major_finetuning_threshold,
                "min_score": min([e["validation_score"] for e in pool]) if pool else 0.0,
                "max_score": max([e["validation_score"] for e in pool]) if pool else 0.0,
                "avg_score": sum([e["validation_score"] for e in pool]) / len(pool) if pool else 0.0
            }
        else:
            # Aggregate stats
            total_examples = sum(len(pool) for pool in self.pools.values())
            ready_types = [
                atype for atype, pool in self.pools.items()
                if len(pool) >= self.incremental_finetuning_threshold
            ]
            
            return {
                "total_examples": total_examples,
                "artifact_types": len(self.pools),
                "ready_for_finetuning": len(ready_types),
                "ready_types": ready_types,
                        "incremental_threshold": self.incremental_finetuning_threshold,
                        "major_threshold": self.major_finetuning_threshold,
                "min_score_threshold": self.min_score_threshold,
                "per_type": {
                    atype: {
                        "count": len(pool),
                        "ready_for_incremental": len(pool) >= self.incremental_finetuning_threshold,
                        "ready_for_major": len(pool) >= self.major_finetuning_threshold
                    }
                    for atype, pool in self.pools.items()
                }
            }
    
    def get_examples(self, artifact_type: str) -> List[Dict[str, Any]]:
        """
        Get all examples for an artifact type.
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            Copy of examples list
        """
        return self.pools.get(artifact_type, []).copy()
    
    def get_source_breakdown(self, artifact_type: str) -> Dict[str, Any]:
        """
        Get breakdown of examples by source (synthetic vs feedback).
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            Dictionary with source breakdown
        """
        examples = self.pools.get(artifact_type, [])
        
        real_count = 0
        synthetic_count = 0
        
        for example in examples:
            source = example.get('context', {}).get('source', 'feedback')
            if source == 'synthetic':
                synthetic_count += 1
            else:
                real_count += 1
        
        total = real_count + synthetic_count
        synthetic_pct = (synthetic_count / total * 100) if total > 0 else 0
        
        return {
            'artifact_type': artifact_type,
            'real_examples': real_count,
            'synthetic_examples': synthetic_count,
            'total_examples': total,
            'synthetic_percentage': round(synthetic_pct, 1),
            'ready_for_training': total >= self.incremental_finetuning_threshold,
            'ready_for_graduation': real_count >= 200,  # Can remove synthetic
            'needs_bootstrap': total < 20  # Suggest synthetic generation
        }
    
    def remove_synthetic(self, artifact_type: str) -> int:
        """
        Remove synthetic examples, keeping only real feedback examples.
        Use this when enough real data has been collected.
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            Number of synthetic examples removed
        """
        if artifact_type not in self.pools:
            return 0
        
        original_count = len(self.pools[artifact_type])
        
        # Filter to keep only real examples
        self.pools[artifact_type] = [
            ex for ex in self.pools[artifact_type]
            if ex.get('context', {}).get('source', 'feedback') != 'synthetic'
        ]
        
        removed_count = original_count - len(self.pools[artifact_type])
        
        if removed_count > 0:
            self._save_pool(artifact_type)
            logger.info(f"Removed {removed_count} synthetic examples from {artifact_type}, {len(self.pools[artifact_type])} real examples remain")
        
        return removed_count
    
    def clear_pool(self, artifact_type: str) -> bool:
        """
        Clear the pool for an artifact type (after finetuning completes).
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            True if pool was cleared
        """
        if artifact_type in self.pools:
            self.pools[artifact_type] = []
            self._save_pool(artifact_type)
            logger.info(f"Cleared pool for {artifact_type}")
            return True
        return False


# Global pool instance
_pool: Optional[FinetuningPool] = None

def get_pool() -> FinetuningPool:
    """Get or create global Finetuning Pool instance."""
    global _pool
    if _pool is None:
        _pool = FinetuningPool()
    return _pool

