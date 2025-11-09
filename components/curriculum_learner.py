"""
Curriculum Learner for Progressive Training
Implements curriculum learning: train on easy examples first, then progressively
introduce harder examples for faster convergence and better final quality.

Strategy:
- Stage 1 (Easy): Simple artifacts, short inputs, high validation scores
- Stage 2 (Medium): Mix of easy and medium difficulty
- Stage 3 (Hard): Full difficulty spectrum including complex artifacts

Progression triggers:
- Advance when model achieves target performance on current stage
- Auto-detect when to progress based on performance metrics
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class CurriculumStage(Enum):
    """Curriculum learning stages"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"  # Full spectrum


@dataclass
class FeedbackEvent:
    """Minimal feedback event structure for curriculum"""
    timestamp: float
    input_data: str
    ai_output: str
    validation_score: float
    artifact_type: str
    reward_signal: float
    context: Dict


class DifficultyEstimator:
    """Estimate difficulty of training examples"""
    
    # Artifact complexity (0-1, higher = harder)
    ARTIFACT_COMPLEXITY = {
        'erd': 0.3,
        'jira': 0.4,
        'api_docs': 0.5,
        'data_flow': 0.5,
        'user_flow': 0.5,
        'api_sequence': 0.5,
        'system_overview': 0.6,
        'components_diagram': 0.6,
        'workflows': 0.6,
        'architecture': 0.7,
        'visual_prototype_dev': 0.7,
        'code_prototype': 0.8,
    }
    
    def estimate(self, example: FeedbackEvent) -> float:
        """
        Estimate difficulty (0-1) based on:
        1. Artifact complexity
        2. Input length
        3. Context size
        4. Generation difficulty (inverse of validation score)
        """
        # Artifact complexity
        artifact_complexity = self.ARTIFACT_COMPLEXITY.get(example.artifact_type, 0.5)
        
        # Input complexity (longer = harder)
        input_length = len(example.input_data)
        input_complexity = min(1.0, input_length / 5000)
        
        # Context complexity (more context = harder)
        context_size = len(str(example.context))
        context_complexity = min(1.0, context_size / 10000)
        
        # Generation difficulty (lower score = harder to generate)
        generation_difficulty = 1.0 - (example.validation_score / 100.0)
        
        # Weighted average
        difficulty = (
            artifact_complexity * 0.4 +
            generation_difficulty * 0.3 +
            input_complexity * 0.2 +
            context_complexity * 0.1
        )
        
        return max(0.0, min(1.0, difficulty))


class CurriculumLearner:
    """
    Progressive curriculum learning from easy to hard.
    
    Workflow:
    1. Organize examples by difficulty (easy/medium/hard)
    2. Start training on easy examples
    3. Monitor performance
    4. Progress to next stage when ready
    5. Eventually train on full spectrum
    """
    
    def __init__(
        self,
        easy_threshold: float = 0.35,      # Difficulty <= 0.35 = easy
        medium_threshold: float = 0.65,    # 0.35 < difficulty <= 0.65 = medium
        progression_score: float = 75.0    # Score needed to progress to next stage
    ):
        """
        Initialize curriculum learner.
        
        Args:
            easy_threshold: Max difficulty for easy examples
            medium_threshold: Max difficulty for medium examples
            progression_score: Validation score needed to progress
        """
        self.easy_threshold = easy_threshold
        self.medium_threshold = medium_threshold
        self.progression_score = progression_score
        
        self.difficulty_estimator = DifficultyEstimator()
        self.current_stage = CurriculumStage.EASY
        
        # Track performance on each stage
        self.stage_performance: Dict[CurriculumStage, List[float]] = {
            CurriculumStage.EASY: [],
            CurriculumStage.MEDIUM: [],
            CurriculumStage.HARD: [],
            CurriculumStage.MIXED: []
        }
    
    def organize_by_curriculum(
        self,
        examples: List[FeedbackEvent]
    ) -> Dict[CurriculumStage, List[FeedbackEvent]]:
        """
        Organize examples into curriculum stages by difficulty.
        
        Args:
            examples: All available training examples
        
        Returns:
            Dict mapping stage to examples in that difficulty range
        """
        stages = {
            CurriculumStage.EASY: [],
            CurriculumStage.MEDIUM: [],
            CurriculumStage.HARD: []
        }
        
        for example in examples:
            difficulty = self.difficulty_estimator.estimate(example)
            
            if difficulty <= self.easy_threshold:
                stages[CurriculumStage.EASY].append(example)
            elif difficulty <= self.medium_threshold:
                stages[CurriculumStage.MEDIUM].append(example)
            else:
                stages[CurriculumStage.HARD].append(example)
        
        print(f"[CURRICULUM] Organized examples:")
        print(f"  Easy: {len(stages[CurriculumStage.EASY])} examples (difficulty <= {self.easy_threshold})")
        print(f"  Medium: {len(stages[CurriculumStage.MEDIUM])} examples ({self.easy_threshold} < difficulty <= {self.medium_threshold})")
        print(f"  Hard: {len(stages[CurriculumStage.HARD])} examples (difficulty > {self.medium_threshold})")
        
        return stages
    
    def get_next_training_batch(
        self,
        curriculum_stages: Dict[CurriculumStage, List[FeedbackEvent]],
        batch_size: int
    ) -> Tuple[List[FeedbackEvent], CurriculumStage]:
        """
        Get next training batch following curriculum progression.
        
        Stage 1 (Easy): 100% easy examples
        Stage 2 (Medium): 70% easy, 30% medium
        Stage 3 (Hard): 50% easy, 30% medium, 20% hard
        Stage 4 (Mixed): 40% easy, 30% medium, 30% hard
        
        Args:
            curriculum_stages: Examples organized by difficulty
            batch_size: Desired batch size
        
        Returns:
            Tuple of (batch_examples, current_stage)
        """
        if self.current_stage == CurriculumStage.EASY:
            # Stage 1: All easy
            batch = self._sample_examples(
                curriculum_stages[CurriculumStage.EASY],
                batch_size
            )
            stage_name = "EASY (100% easy)"
        
        elif self.current_stage == CurriculumStage.MEDIUM:
            # Stage 2: Mix easy + medium
            easy_count = int(batch_size * 0.7)
            medium_count = batch_size - easy_count
            
            easy_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.EASY],
                easy_count
            )
            medium_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.MEDIUM],
                medium_count
            )
            
            batch = easy_samples + medium_samples
            stage_name = "MEDIUM (70% easy, 30% medium)"
        
        elif self.current_stage == CurriculumStage.HARD:
            # Stage 3: Mix all with emphasis on easy/medium
            easy_count = int(batch_size * 0.5)
            medium_count = int(batch_size * 0.3)
            hard_count = batch_size - easy_count - medium_count
            
            easy_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.EASY],
                easy_count
            )
            medium_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.MEDIUM],
                medium_count
            )
            hard_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.HARD],
                hard_count
            )
            
            batch = easy_samples + medium_samples + hard_samples
            stage_name = "HARD (50% easy, 30% medium, 20% hard)"
        
        else:  # MIXED
            # Stage 4: Balanced mix
            easy_count = int(batch_size * 0.4)
            medium_count = int(batch_size * 0.3)
            hard_count = batch_size - easy_count - medium_count
            
            easy_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.EASY],
                easy_count
            )
            medium_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.MEDIUM],
                medium_count
            )
            hard_samples = self._sample_examples(
                curriculum_stages[CurriculumStage.HARD],
                hard_count
            )
            
            batch = easy_samples + medium_samples + hard_samples
            stage_name = "MIXED (40% easy, 30% medium, 30% hard)"
        
        # Shuffle batch for randomness
        import random
        random.shuffle(batch)
        
        print(f"[CURRICULUM] Created batch for stage: {stage_name}")
        print(f"  Batch size: {len(batch)} examples")
        
        return batch, self.current_stage
    
    def _sample_examples(
        self,
        examples: List[FeedbackEvent],
        n: int
    ) -> List[FeedbackEvent]:
        """Sample N examples from list (with replacement if needed)"""
        if not examples:
            return []
        
        if len(examples) >= n:
            # Enough examples - sample without replacement
            import random
            return random.sample(examples, n)
        else:
            # Not enough - use all and repeat some
            import random
            result = examples.copy()
            remaining = n - len(examples)
            result.extend(random.choices(examples, k=remaining))
            return result
    
    def record_performance(
        self,
        stage: CurriculumStage,
        validation_score: float
    ):
        """
        Record performance on a stage.
        Used to decide when to progress to next stage.
        
        Args:
            stage: Current curriculum stage
            validation_score: Validation score (0-100)
        """
        self.stage_performance[stage].append(validation_score)
    
    def should_progress(
        self,
        min_evaluations: int = 3,
        score_threshold: Optional[float] = None
    ) -> bool:
        """
        Check if model should progress to next curriculum stage.
        
        Criteria:
        - Evaluated at least `min_evaluations` times on current stage
        - Average score meets or exceeds threshold
        
        Args:
            min_evaluations: Minimum evaluations before progression
            score_threshold: Score threshold (default: self.progression_score)
        
        Returns:
            bool: True if should progress, False otherwise
        """
        if score_threshold is None:
            score_threshold = self.progression_score
        
        current_performance = self.stage_performance[self.current_stage]
        
        if len(current_performance) < min_evaluations:
            return False  # Not enough evaluations yet
        
        # Check last N evaluations
        recent_scores = current_performance[-min_evaluations:]
        avg_score = np.mean(recent_scores)
        
        if avg_score >= score_threshold:
            print(f"[CURRICULUM] Stage {self.current_stage.value} mastered (avg score: {avg_score:.1f})")
            return True
        
        return False
    
    def progress_stage(self):
        """Progress to next curriculum stage"""
        if self.current_stage == CurriculumStage.EASY:
            self.current_stage = CurriculumStage.MEDIUM
            print("[CURRICULUM] Progressed to MEDIUM stage")
        elif self.current_stage == CurriculumStage.MEDIUM:
            self.current_stage = CurriculumStage.HARD
            print("[CURRICULUM] Progressed to HARD stage")
        elif self.current_stage == CurriculumStage.HARD:
            self.current_stage = CurriculumStage.MIXED
            print("[CURRICULUM] Progressed to MIXED stage (final)")
        else:
            print("[CURRICULUM] Already at final stage (MIXED)")
    
    def reset(self):
        """Reset to beginning of curriculum"""
        self.current_stage = CurriculumStage.EASY
        for stage in self.stage_performance:
            self.stage_performance[stage].clear()
        print("[CURRICULUM] Reset to EASY stage")
    
    def get_statistics(self) -> Dict:
        """Get curriculum learning statistics"""
        return {
            'current_stage': self.current_stage.value,
            'stage_performance': {
                stage.value: {
                    'evaluations': len(scores),
                    'avg_score': float(np.mean(scores)) if scores else 0.0,
                    'best_score': float(np.max(scores)) if scores else 0.0
                }
                for stage, scores in self.stage_performance.items()
            }
        }


# Example usage
if __name__ == "__main__":
    import time
    import random
    import json
    
    learner = CurriculumLearner()
    
    print("="*80)
    print("CURRICULUM LEARNER - TEST")
    print("="*80)
    
    # Create sample examples with varying difficulty
    examples = []
    for i in range(100):
        # Mix of artifact types
        artifact_types = ['erd', 'jira', 'code_prototype', 'architecture']
        artifact_type = random.choice(artifact_types)
        
        # Vary input length and validation score
        input_length = random.randint(100, 3000)
        validation_score = random.uniform(60, 95)
        
        example = FeedbackEvent(
            timestamp=time.time() + i,
            input_data="x" * input_length,
            ai_output="output",
            validation_score=validation_score,
            artifact_type=artifact_type,
            reward_signal=validation_score / 100 - 0.3,
            context={"rag": "x" * random.randint(100, 5000)}
        )
        examples.append(example)
    
    # Organize by curriculum
    print("\n" + "-" * 40)
    curriculum_stages = learner.organize_by_curriculum(examples)
    
    # Simulate progression through stages
    print("\n" + "="*80)
    print("SIMULATING CURRICULUM PROGRESSION")
    print("="*80)
    
    for iteration in range(12):
        print(f"\nIteration {iteration + 1}:")
        
        # Get batch for current stage
        batch, stage = learner.get_next_training_batch(curriculum_stages, batch_size=30)
        
        # Simulate training and validation
        # Performance improves as model trains
        base_score = 70 + iteration * 2 + random.uniform(-2, 2)
        learner.record_performance(stage, base_score)
        
        print(f"  Validation score: {base_score:.1f}")
        
        # Check if should progress
        if learner.should_progress():
            learner.progress_stage()
    
    # Show final statistics
    print("\n" + "="*80)
    print("FINAL STATISTICS")
    print("="*80)
    stats = learner.get_statistics()
    print(json.dumps(stats, indent=2))

