"""
Enhanced Adaptive Learning Loop - Next-Generation Self-Improving AI System

This is the ENHANCED version with all optimization components:
1. Enhanced reward calculation (temporal decay, difficulty weighting)
2. Advanced similarity metrics (edit distance, BLEU, embeddings)
3. Dynamic batch sizing (adaptive per artifact)
4. Performance tracking (train/val split, metrics)
5. Curriculum learning (easy → hard progression)
6. Active learning (informative example selection)
7. Hyperparameter optimization (Bayesian search)
8. Preference learning (RLHF-style)
9. Data augmentation (2-3x dataset expansion)
10. Hard negative mining (edge case focus)

WORKFLOW:
User Request → AI Generation → Validation → Enhanced Feedback →
  Curriculum Organization → Active Selection → Data Augmentation →
    Dynamic Batch Creation → Hyperparameter Optimization → Fine-tune Model →
      Performance Tracking → Improvement Loop

The system learns INTELLIGENTLY from every interaction with state-of-the-art ML techniques.
"""

import sys
# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum

# Import all enhanced components
from components.reward_calculator_enhanced import (
    EnhancedRewardCalculator,
    FeedbackType,
    FeedbackEvent as RewardFeedbackEvent
)
from components.similarity_metrics import SimilarityCalculator, calculate_similarity
from components.batch_manager_adaptive import AdaptiveBatchManager
from components.performance_tracker import PerformanceTracker, PerformanceMetrics
from components.curriculum_learner import CurriculumLearner, CurriculumStage
from components.active_learner import ActiveLearner
from components.hyperparameter_optimizer import HyperparameterOptimizer, HyperparameterConfig
from components.preference_learner import PreferenceLearner, PreferencePair
from components.data_augmenter import DataAugmenter, TrainingExample as AugmentedExample
from components.hard_negative_miner import HardNegativeMiner, FailureCase


@dataclass
class FeedbackEvent:
    """Single feedback event from production (compatible with enhanced components)"""
    timestamp: float
    feedback_type: FeedbackType
    input_data: str
    ai_output: str
    corrected_output: Optional[str]
    context: Dict[str, Any]
    validation_score: float
    artifact_type: str
    model_used: str
    reward_signal: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_training_example(self) -> Dict[str, str]:
        """Convert to training example format"""
        target = self.corrected_output if self.corrected_output else self.ai_output
        return {
            'instruction': f"Generate {self.artifact_type}",
            'input': self.input_data,
            'output': target,
            'context': json.dumps(self.context),
            'quality_score': self.validation_score
        }


@dataclass
class TrainingBatch:
    """Batch of training examples ready for fine-tuning"""
    batch_id: str
    created_at: float
    examples: List[Dict[str, str]]
    priority: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    hyperparameters: Optional[HyperparameterConfig] = None  # NEW: Include optimal hyperparams


class EnhancedAdaptiveLearningLoop:
    """
    Enhanced adaptive learning system with all optimizations.
    
    Features:
    - Enhanced reward calculation with temporal decay and difficulty weighting
    - Advanced similarity metrics for better correction detection
    - Dynamic batch sizing based on artifact statistics
    - Performance tracking with train/val split
    - Curriculum learning for faster convergence
    - Active learning for sample efficiency
    - Hyperparameter optimization
    - Preference learning (RLHF-style)
    - Data augmentation for dataset expansion
    - Hard negative mining for edge case improvement
    """
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        enable_curriculum: bool = True,
        enable_active_learning: bool = True,
        enable_augmentation: bool = True,
        enable_preference_learning: bool = False,  # Optional, requires multiple generations
        enable_hard_negative_mining: bool = True
    ):
        """
        Initialize enhanced adaptive learning loop.
        
        Args:
            storage_dir: Base directory for all storage
            enable_curriculum: Use curriculum learning
            enable_active_learning: Use active learning
            enable_augmentation: Use data augmentation
            enable_preference_learning: Use preference learning (RLHF)
            enable_hard_negative_mining: Track and learn from failures
        """
        self.storage_dir = storage_dir or Path("training_jobs/adaptive_learning_enhanced")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Feature flags
        self.enable_curriculum = enable_curriculum
        self.enable_active_learning = enable_active_learning
        self.enable_augmentation = enable_augmentation
        self.enable_preference_learning = enable_preference_learning
        self.enable_hard_negative_mining = enable_hard_negative_mining
        
        # Core feedback storage
        self.feedback_events: List[FeedbackEvent] = []
        self.training_batches: List[TrainingBatch] = []
        
        # Initialize all enhanced components
        print("[ENHANCED_ADAPTIVE] Initializing enhanced components...")
        
        # 1. Enhanced Reward Calculator
        self.reward_calculator = EnhancedRewardCalculator()
        print("  ✓ Enhanced Reward Calculator")
        
        # 2. Similarity Calculator
        self.similarity_calculator = SimilarityCalculator()
        print("  ✓ Advanced Similarity Metrics")
        
        # 3. Adaptive Batch Manager
        self.batch_manager = AdaptiveBatchManager(storage_dir=self.storage_dir / "batch_manager")
        print("  ✓ Dynamic Batch Manager")
        
        # 4. Performance Tracker
        self.performance_tracker = PerformanceTracker(storage_dir=self.storage_dir / "performance")
        print("  ✓ Performance Tracker")
        
        # 5. Curriculum Learner (optional)
        if self.enable_curriculum:
            self.curriculum_learner = CurriculumLearner()
            print("  ✓ Curriculum Learner (enabled)")
        else:
            self.curriculum_learner = None
            print("  - Curriculum Learner (disabled)")
        
        # 6. Active Learner (optional)
        if self.enable_active_learning:
            self.active_learner = ActiveLearner()
            print("  ✓ Active Learner (enabled)")
        else:
            self.active_learner = None
            print("  - Active Learner (disabled)")
        
        # 7. Hyperparameter Optimizer
        self.hparam_optimizer = HyperparameterOptimizer(storage_dir=self.storage_dir / "hyperparams")
        print("  ✓ Hyperparameter Optimizer")
        
        # 8. Preference Learner (optional)
        if self.enable_preference_learning:
            self.preference_learner = PreferenceLearner(storage_dir=self.storage_dir / "preferences")
            print("  ✓ Preference Learner (enabled)")
        else:
            self.preference_learner = None
            print("  - Preference Learner (disabled)")
        
        # 9. Data Augmenter (optional)
        if self.enable_augmentation:
            self.data_augmenter = DataAugmenter(augmentation_factor=2)
            print("  ✓ Data Augmenter (enabled)")
        else:
            self.data_augmenter = None
            print("  - Data Augmenter (disabled)")
        
        # 10. Hard Negative Miner (optional)
        if self.enable_hard_negative_mining:
            self.hard_negative_miner = HardNegativeMiner(storage_dir=self.storage_dir / "hard_negatives")
            print("  ✓ Hard Negative Miner (enabled)")
        else:
            self.hard_negative_miner = None
            print("  - Hard Negative Miner (disabled)")
        
        # Configuration
        self.min_reward_threshold = 0.3
        self.priority_weights = {
            FeedbackType.USER_CORRECTION: 10,
            FeedbackType.EXPLICIT_POSITIVE: 8,
            FeedbackType.SUCCESS: 5,
            FeedbackType.VALIDATION_FAILURE: 3,
            FeedbackType.EXPLICIT_NEGATIVE: 1
        }
        
        # Load existing feedback
        self._load_feedback()
        
        print("[ENHANCED_ADAPTIVE] Initialization complete! 🚀")
    
    def record_feedback(
        self,
        input_data: str,
        ai_output: str,
        artifact_type: str,
        model_used: str,
        validation_score: float,
        feedback_type: FeedbackType,
        corrected_output: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> Optional[FeedbackEvent]:
        """
        Record feedback with enhanced processing.
        
        Uses:
        - Enhanced reward calculation
        - Hard negative mining (for failures)
        - Automatic batch creation with dynamic sizing
        """
        # QUALITY GATE: Discard low-quality feedback
        if validation_score < 70.0:
            print(f"[ENHANCED_ADAPTIVE] ⛔ Discarded low-quality feedback (score: {validation_score:.1f} < 70.0)")
            return None
        
        is_generic_content = context.get('is_generic_content', False) if context else False
        if is_generic_content:
            print(f"[ENHANCED_ADAPTIVE] ⛔ Discarded generic content")
            return None
        
        if feedback_type == FeedbackType.SUCCESS and validation_score < 80.0:
            print(f"[ENHANCED_ADAPTIVE] ⛔ Discarded 'success' with score < 80.0 ({validation_score:.1f})")
            return None
        
        # Create feedback event
        event = FeedbackEvent(
            timestamp=time.time(),
            feedback_type=feedback_type,
            input_data=input_data,
            ai_output=ai_output,
            corrected_output=corrected_output,
            context=context or {},
            validation_score=validation_score,
            artifact_type=artifact_type,
            model_used=model_used,
            reward_signal=0.0
        )
        
        # Calculate ENHANCED reward
        event.reward_signal = self.reward_calculator.calculate_reward(event)
        
        # Store event
        self.feedback_events.append(event)
        self._save_feedback_event(event)
        
        print(f"[ENHANCED_ADAPTIVE] ✅ Recorded feedback: {feedback_type.value}, "
              f"reward={event.reward_signal:.2f}, validation={validation_score:.1f}")
        
        # HARD NEGATIVE MINING: Track failures
        if self.enable_hard_negative_mining and validation_score < 75.0:
            self.hard_negative_miner.record_failure(
                input_data=input_data,
                output=ai_output,
                validation_score=validation_score,
                artifact_type=artifact_type,
                expected_output=corrected_output,
                metadata=context
            )
        
        # Check if we should create a training batch
        self._check_and_create_batch()
        
        return event
    
    def _check_and_create_batch(self):
        """
        Check if we should create a training batch with intelligent selection.
        
        Uses:
        - Dynamic batch sizing
        - Curriculum learning
        - Active learning
        - Data augmentation
        """
        # Filter high-quality feedback
        high_quality = [
            e for e in self.feedback_events
            if e.reward_signal >= self.min_reward_threshold
        ]
        
        # Group by (artifact_type, model_used) pairs
        from collections import defaultdict
        pairs: Dict[Tuple[str, str], List[FeedbackEvent]] = defaultdict(list)
        for event in high_quality:
            pair_key = (event.artifact_type, event.model_used)
            pairs[pair_key].append(event)
        
        # Check each pair
        for (artifact_type, model_used), events in pairs.items():
            # DYNAMIC BATCH SIZING: Calculate optimal batch size
            avg_quality = sum(e.reward_signal for e in events) / len(events)
            optimal_batch_size = self.batch_manager.calculate_optimal_batch_size(
                artifact_type=artifact_type,
                available_examples=len(events),
                avg_quality=avg_quality
            )
            
            if optimal_batch_size == 0:
                continue  # Not enough examples yet
            
            if len(events) >= optimal_batch_size:
                print(f"\n[ENHANCED_ADAPTIVE] Creating batch for {artifact_type} + {model_used}")
                print(f"  Available: {len(events)}, Optimal batch: {optimal_batch_size}")
                
                # Select examples intelligently
                selected_events = self._select_training_examples(
                    events,
                    optimal_batch_size,
                    artifact_type
                )
                
                # Create and store batch
                self._create_training_batch_for_pair(
                    artifact_type,
                    model_used,
                    selected_events
                )
                
                # Remove used events
                for event in selected_events:
                    if event in self.feedback_events:
                        self.feedback_events.remove(event)
    
    def _select_training_examples(
        self,
        candidates: List[FeedbackEvent],
        batch_size: int,
        artifact_type: str
    ) -> List[FeedbackEvent]:
        """
        Intelligently select training examples using curriculum and active learning.
        
        Returns:
            Selected examples (batch_size count)
        """
        # STEP 1: CURRICULUM LEARNING (organize by difficulty)
        if self.enable_curriculum and self.curriculum_learner:
            curriculum_stages = self.curriculum_learner.organize_by_curriculum(candidates)
            curriculum_batch, current_stage = self.curriculum_learner.get_next_training_batch(
                curriculum_stages,
                batch_size * 2  # Get 2x for active learning selection
            )
            candidates_pool = curriculum_batch
            print(f"  [Curriculum] Selected from stage: {current_stage.value}")
        else:
            candidates_pool = candidates
        
        # STEP 2: ACTIVE LEARNING (select most informative)
        if self.enable_active_learning and self.active_learner and len(candidates_pool) > batch_size:
            selected, metadata = self.active_learner.select_informative_examples(
                candidates_pool,
                budget=batch_size
            )
            print(f"  [Active Learning] Selected {len(selected)} most informative examples")
        else:
            # Fallback: random sample
            import random
            selected = random.sample(candidates_pool, min(batch_size, len(candidates_pool)))
        
        # STEP 3: ADD HARD NEGATIVES (if available)
        if self.enable_hard_negative_mining and self.hard_negative_miner:
            hard_negatives = self.hard_negative_miner.get_hard_negatives(
                artifact_type=artifact_type,
                limit=batch_size // 4  # 25% hard negatives
            )
            if hard_negatives:
                print(f"  [Hard Negatives] Adding {len(hard_negatives)} challenging examples")
                # Convert FailureCase to FeedbackEvent
                for failure in hard_negatives:
                    hard_event = FeedbackEvent(
                        timestamp=failure.timestamp,
                        feedback_type=FeedbackType.VALIDATION_FAILURE,
                        input_data=failure.input_data,
                        ai_output=failure.output,
                        corrected_output=failure.expected_output,
                        context={},
                        validation_score=failure.validation_score,
                        artifact_type=failure.artifact_type,
                        model_used="unknown",
                        reward_signal=-0.5
                    )
                    selected.append(hard_event)
        
        return selected[:batch_size]  # Ensure we don't exceed batch size
    
    def _create_training_batch_for_pair(
        self,
        artifact_type: str,
        model_used: str,
        events: List[FeedbackEvent]
    ):
        """
        Create training batch with data augmentation and hyperparameter optimization.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{artifact_type}_{model_used.replace(':', '_')}_{timestamp}"
        
        # Convert to training examples
        base_examples = [e.to_training_example() for e in events]
        
        # DATA AUGMENTATION (optional)
        if self.enable_augmentation and self.data_augmenter:
            # Convert to AugmentedExample format
            aug_examples = [
                AugmentedExample(
                    input_data=ex['input'],
                    output=ex['output'],
                    context=json.loads(ex['context']),
                    artifact_type=artifact_type,
                    quality_score=ex['quality_score']
                )
                for ex in base_examples
            ]
            
            # Augment (2x expansion)
            augmented = self.data_augmenter.augment_dataset(aug_examples)
            
            # Convert back
            training_examples = [
                {
                    'instruction': f"Generate {ex.artifact_type}",
                    'input': ex.input_data,
                    'output': ex.output,
                    'context': json.dumps(ex.context),
                    'quality_score': ex.quality_score
                }
                for ex in augmented
            ]
            
            print(f"  [Data Augmentation] Expanded from {len(base_examples)} to {len(training_examples)} examples")
        else:
            training_examples = base_examples
        
        # HYPERPARAMETER OPTIMIZATION: Load best hyperparameters (or use default)
        best_params = self.hparam_optimizer.load_best_params(artifact_type)
        if best_params is None:
            best_params = self.hparam_optimizer.get_default_config()
            print(f"  [Hyperparams] Using default configuration")
        else:
            print(f"  [Hyperparams] Using optimized configuration (LR: {best_params.learning_rate:.2e})")
        
        # Calculate priority
        avg_reward = sum(e.reward_signal for e in events) / len(events)
        priority = int(avg_reward * 10)
        
        # Create batch
        batch = TrainingBatch(
            batch_id=batch_id,
            created_at=time.time(),
            examples=training_examples,
            priority=priority,
            hyperparameters=best_params,
            metadata={
                'artifact_type': artifact_type,
                'model_used': model_used,
                'base_examples': len(base_examples),
                'total_examples': len(training_examples),
                'avg_reward': avg_reward,
                'curriculum_stage': self.curriculum_learner.current_stage.value if self.curriculum_learner else None,
                'used_augmentation': self.enable_augmentation,
                'used_active_learning': self.enable_active_learning
            }
        )
        
        self.training_batches.append(batch)
        self._save_training_batch(batch)
        
        # Record batch creation in batch manager
        self.batch_manager.record_batch_creation(
            artifact_type=artifact_type,
            batch_size=len(events),
            avg_quality=avg_reward,
            timestamp=time.time()
        )
        
        # Trigger fine-tuning
        self._trigger_finetuning_for_pair(batch, artifact_type, model_used)
        
        print(f"\n[ENHANCED_ADAPTIVE] ✅ Batch '{batch_id}' created and queued for fine-tuning")
    
    def _trigger_finetuning_for_pair(
        self,
        batch: TrainingBatch,
        artifact_type: str,
        model_used: str
    ):
        """
        Trigger fine-tuning with hyperparameters.
        """
        job_file = self.storage_dir / "finetuning_jobs" / f"{batch.batch_id}.json"
        job_file.parent.mkdir(parents=True, exist_ok=True)
        
        job = {
            'job_id': batch.batch_id,
            'artifact_type': artifact_type,
            'model_used': model_used,
            'base_model': model_used,
            'batch_id': batch.batch_id,
            'batch_size': len(batch.examples),
            'priority': batch.priority,
            'status': 'pending',
            'created_at': batch.created_at,
            'metadata': batch.metadata,
            'hyperparameters': batch.hyperparameters.to_dict() if batch.hyperparameters else None
        }
        
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job, f, indent=2)
        
        print(f"[ENHANCED_ADAPTIVE] 📝 Fine-tuning job created: {job_file}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            'feedback_events': len(self.feedback_events),
            'training_batches': len(self.training_batches),
            'reward_calculator': self.reward_calculator.get_statistics(),
            'batch_manager': self.batch_manager.get_summary(),
            'performance_tracker': self.performance_tracker.get_summary(),
        }
        
        if self.curriculum_learner:
            stats['curriculum'] = self.curriculum_learner.get_statistics()
        
        if self.hard_negative_miner:
            stats['hard_negatives'] = self.hard_negative_miner.analyze_failure_patterns()
        
        return stats
    
    def _save_feedback_event(self, event: FeedbackEvent):
        """Save single feedback event"""
        events_dir = self.storage_dir / "feedback_events"
        events_dir.mkdir(parents=True, exist_ok=True)
        
        event_file = events_dir / f"{int(event.timestamp)}.json"
        with open(event_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(event), f, indent=2)
    
    def _save_training_batch(self, batch: TrainingBatch):
        """Save training batch"""
        batches_dir = self.storage_dir / "training_batches"
        batches_dir.mkdir(parents=True, exist_ok=True)
        
        batch_file = batches_dir / f"{batch.batch_id}.json"
        batch_dict = asdict(batch)
        if batch.hyperparameters:
            batch_dict['hyperparameters'] = batch.hyperparameters.to_dict()
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch_dict, f, indent=2)
    
    def _load_feedback(self):
        """Load existing feedback"""
        events_dir = self.storage_dir / "feedback_events"
        if not events_dir.exists():
            return
        
        for event_file in events_dir.glob("*.json"):
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Reconstruct event
                # ... (implementation details)
            except Exception as e:
                print(f"[WARN] Could not load feedback event: {e}")


# Convenience function for backward compatibility
def create_adaptive_learning_loop(**kwargs) -> EnhancedAdaptiveLearningLoop:
    """Create enhanced adaptive learning loop"""
    return EnhancedAdaptiveLearningLoop(**kwargs)


if __name__ == "__main__":
    # Test the enhanced system
    print("="*80)
    print("ENHANCED ADAPTIVE LEARNING - SYSTEM TEST")
    print("="*80)
    
    loop = EnhancedAdaptiveLearningLoop()
    
    print("\n✅ Enhanced adaptive learning system initialized successfully!")
    print("\nEnabled features:")
    print(f"  - Enhanced Reward Calculation: ✓")
    print(f"  - Advanced Similarity Metrics: ✓")
    print(f"  - Dynamic Batch Sizing: ✓")
    print(f"  - Performance Tracking: ✓")
    print(f"  - Curriculum Learning: {'' if loop.enable_curriculum else ''}")
    print(f"  - Active Learning: {'' if loop.enable_active_learning else ''}")
    print(f"  - Hyperparameter Optimization: ✓")
    print(f"  - Preference Learning: {'' if loop.enable_preference_learning else ''}")
    print(f"  - Data Augmentation: {'' if loop.enable_augmentation else ''}")
    print(f"  - Hard Negative Mining: {'✓' if loop.enable_hard_negative_mining else ''}")

