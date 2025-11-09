"""
Enhanced Reward Calculator for Adaptive Learning
Implements sophisticated reward calculation with:
1. Continuous score mapping (not discrete buckets)
2. Temporal decay (recent feedback more important)
3. Difficulty weighting (complex artifacts more valuable)
4. Distribution balancing (penalize oversampled artifacts)
"""

import math
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum


class FeedbackType(Enum):
    """Type of feedback received"""
    SUCCESS = "success"
    USER_CORRECTION = "user_correction"
    VALIDATION_FAILURE = "validation_failure"
    EXPLICIT_POSITIVE = "explicit_positive"
    EXPLICIT_NEGATIVE = "explicit_negative"


@dataclass
class FeedbackEvent:
    """Single feedback event from production"""
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
    metadata: Dict[str, Any] = None


class DifficultyEstimator:
    """Estimate example difficulty for weighting"""
    
    # Artifact complexity weights (0-1, higher = more complex)
    ARTIFACT_COMPLEXITY = {
        'erd': 0.3,
        'architecture': 0.7,
        'system_overview': 0.6,
        'data_flow': 0.5,
        'user_flow': 0.5,
        'components_diagram': 0.6,
        'api_sequence': 0.5,
        'api_docs': 0.5,
        'jira': 0.4,
        'workflows': 0.6,
        'code_prototype': 0.8,
        'visual_prototype_dev': 0.7,
    }
    
    def estimate(self, event: FeedbackEvent) -> float:
        """
        Estimate example difficulty (0-1) based on:
        - Artifact complexity (ERD < Code < Architecture)
        - Input length (longer = harder)
        - RAG context size (more context = more complex)
        - Validation score (lower = harder to generate correctly)
        
        Returns:
            float: Difficulty score 0-1 (0=easy, 1=hard)
        """
        # 1. Artifact complexity
        artifact_complexity = self.ARTIFACT_COMPLEXITY.get(event.artifact_type, 0.5)
        
        # 2. Input complexity (longer = harder)
        input_length = len(event.input_data)
        # Normalize to 0-1 (assume 5000 chars = max complexity)
        input_complexity = min(1.0, input_length / 5000)
        
        # 3. Context complexity
        context_size = len(str(event.context))
        # Normalize to 0-1 (assume 10000 chars = max complexity)
        context_complexity = min(1.0, context_size / 10000)
        
        # 4. Generation difficulty (inverse of validation score)
        # Lower score = harder to generate correctly
        generation_difficulty = 1.0 - (event.validation_score / 100.0)
        
        # Weighted average
        difficulty = (
            artifact_complexity * 0.4 +      # Most important
            generation_difficulty * 0.3 +    # Second most important
            input_complexity * 0.2 +         # Less important
            context_complexity * 0.1         # Least important
        )
        
        return max(0.0, min(1.0, difficulty))


class EnhancedRewardCalculator:
    """
    Advanced reward calculation with:
    - Continuous score mapping (not discrete buckets)
    - Temporal decay (recent feedback more important)
    - Difficulty weighting (complex artifacts more valuable)
    - Distribution balancing (penalize oversampled artifacts)
    """
    
    def __init__(
        self,
        time_decay_rate: float = 0.95,      # Decay per day (0.95 = 5% decay/day)
        difficulty_weight: float = 1.5,     # Boost for hard examples (1.5 = 50% boost)
        balance_threshold: int = 100        # Start penalizing after N examples
    ):
        self.time_decay_rate = time_decay_rate
        self.difficulty_weight = difficulty_weight
        self.balance_threshold = balance_threshold
        
        self.difficulty_estimator = DifficultyEstimator()
        
        # Track artifact distribution for balancing
        self.artifact_counts: Dict[str, int] = defaultdict(int)
    
    def calculate_reward(self, event: FeedbackEvent) -> float:
        """
        Calculate reward signal with advanced features.
        
        Args:
            event: Feedback event with validation score, feedback type, etc.
        
        Returns:
            float: Reward signal in range [-1, 1]
        """
        # 1. CONTINUOUS VALIDATION SCORE MAPPING
        # Map [0, 100] → [-1, 1] with smooth sigmoid
        # Score 50 → 0, Score 100 → ~1, Score 0 → ~-1
        normalized_score = (event.validation_score - 50) / 50  # [-1, 1] range
        validation_reward = math.tanh(normalized_score)  # Smooth sigmoid: -1 to 1
        
        # 2. FEEDBACK TYPE ADJUSTMENT
        # User corrections and explicit feedback override validation
        feedback_bonus = self._calculate_feedback_bonus(event)
        
        # Base reward (before adjustments)
        base_reward = validation_reward + feedback_bonus
        
        # 3. TEMPORAL DECAY
        # Recent feedback more important than old feedback
        time_weight = self._calculate_temporal_weight(event.timestamp)
        
        # 4. DIFFICULTY WEIGHTING
        # Complex artifacts get boosted rewards (learn more from hard examples)
        difficulty_multiplier = self._calculate_difficulty_multiplier(event)
        
        # 5. DISTRIBUTION BALANCING
        # Penalize oversampled artifacts to maintain balance
        balance_multiplier = self._calculate_balance_multiplier(event.artifact_type)
        
        # FINAL REWARD
        # Combine all factors
        final_reward = base_reward * time_weight * difficulty_multiplier * balance_multiplier
        
        # Clamp to [-1, 1]
        final_reward = max(-1.0, min(1.0, final_reward))
        
        # Update distribution tracking
        self.artifact_counts[event.artifact_type] += 1
        
        return final_reward
    
    def _calculate_feedback_bonus(self, event: FeedbackEvent) -> float:
        """
        Calculate bonus/penalty based on feedback type.
        
        Returns:
            float: Adjustment in range [-1, 1]
        """
        if event.feedback_type == FeedbackType.SUCCESS:
            # AI output accepted without changes
            return 0.3
        
        elif event.feedback_type == FeedbackType.USER_CORRECTION:
            # User modified AI output - learn from correction
            # More valuable than success (we see what was wrong)
            if event.corrected_output:
                # Estimate magnitude of correction
                similarity = self._calculate_similarity(event.ai_output, event.corrected_output)
                if similarity > 0.8:
                    return 0.2  # Minor correction
                elif similarity > 0.5:
                    return 0.1  # Medium correction
                else:
                    return 0.0  # Major correction (neutral - need to learn)
            return 0.1
        
        elif event.feedback_type == FeedbackType.EXPLICIT_POSITIVE:
            # User clicked "Good" - strong positive signal
            return 0.5
        
        elif event.feedback_type == FeedbackType.EXPLICIT_NEGATIVE:
            # User clicked "Bad" - strong negative signal
            return -1.0
        
        elif event.feedback_type == FeedbackType.VALIDATION_FAILURE:
            # Failed validation - negative signal
            return -0.5
        
        return 0.0
    
    def _calculate_temporal_weight(self, timestamp: float) -> float:
        """
        Calculate temporal decay weight.
        Recent feedback more important than old feedback.
        
        Args:
            timestamp: Unix timestamp of feedback event
        
        Returns:
            float: Weight in range [0, 1] (1 = now, <1 = older)
        """
        age_seconds = time.time() - timestamp
        age_days = age_seconds / 86400  # Convert to days
        
        # Exponential decay: weight = decay_rate ^ days
        # 0.95 ^ 1 day = 0.95 (5% decay)
        # 0.95 ^ 7 days = 0.70 (30% decay)
        # 0.95 ^ 30 days = 0.21 (79% decay)
        weight = self.time_decay_rate ** age_days
        
        return max(0.1, weight)  # Floor at 0.1 (never completely ignore old feedback)
    
    def _calculate_difficulty_multiplier(self, event: FeedbackEvent) -> float:
        """
        Calculate difficulty multiplier.
        Complex artifacts get boosted rewards.
        
        Args:
            event: Feedback event
        
        Returns:
            float: Multiplier >= 1.0 (1.0 = no boost, higher = more boost)
        """
        difficulty = self.difficulty_estimator.estimate(event)
        
        # Boost reward based on difficulty
        # Easy (0.0): 1.0x (no boost)
        # Medium (0.5): 1.25x boost
        # Hard (1.0): 1.5x boost
        multiplier = 1.0 + (difficulty * (self.difficulty_weight - 1.0))
        
        return multiplier
    
    def _calculate_balance_multiplier(self, artifact_type: str) -> float:
        """
        Calculate distribution balance multiplier.
        Penalize oversampled artifacts to maintain balance.
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            float: Multiplier in range [0.5, 1.0] (1.0 = balanced, <1.0 = oversampled)
        """
        count = self.artifact_counts[artifact_type]
        
        if count < self.balance_threshold:
            # Not oversampled yet - no penalty
            return 1.0
        
        # Calculate penalty based on how much over threshold
        excess = count - self.balance_threshold
        # Penalty increases with excess, but floor at 0.5 (never completely ignore)
        penalty = math.exp(-excess / 50)  # Exponential decay
        
        return max(0.5, penalty)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Simple character-level similarity (0-1).
        
        Note: This is a basic implementation. The advanced similarity
        metrics in similarity_metrics.py provide better accuracy.
        """
        if not text1 or not text2:
            return 0.0
        
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get reward calculator statistics"""
        return {
            'artifact_counts': dict(self.artifact_counts),
            'total_examples': sum(self.artifact_counts.values()),
            'time_decay_rate': self.time_decay_rate,
            'difficulty_weight': self.difficulty_weight,
            'balance_threshold': self.balance_threshold
        }
    
    def reset_statistics(self):
        """Reset artifact count statistics"""
        self.artifact_counts.clear()


# Example usage
if __name__ == "__main__":
    import json
    
    # Create calculator
    calculator = EnhancedRewardCalculator()
    
    # Test with sample events
    test_events = [
        # High-quality recent ERD
        FeedbackEvent(
            timestamp=time.time(),
            feedback_type=FeedbackType.SUCCESS,
            input_data="Generate ERD for e-commerce system" * 50,
            ai_output="erDiagram...",
            corrected_output=None,
            context={"rag": "..." * 100},
            validation_score=90.0,
            artifact_type="erd",
            model_used="mistral:7b"
        ),
        
        # Low-quality old code prototype
        FeedbackEvent(
            timestamp=time.time() - 86400 * 7,  # 7 days ago
            feedback_type=FeedbackType.VALIDATION_FAILURE,
            input_data="Generate code for user authentication" * 100,
            ai_output="class User...",
            corrected_output=None,
            context={"rag": "..." * 500},
            validation_score=45.0,
            artifact_type="code_prototype",
            model_used="codellama:7b"
        ),
        
        # Medium-quality with user correction
        FeedbackEvent(
            timestamp=time.time() - 86400,  # 1 day ago
            feedback_type=FeedbackType.USER_CORRECTION,
            input_data="Generate architecture diagram",
            ai_output="graph TD\nA-->B",
            corrected_output="graph TD\nA-->B\nB-->C",
            context={"rag": "..." * 200},
            validation_score=75.0,
            artifact_type="architecture",
            model_used="mistral:7b"
        ),
    ]
    
    print("="*80)
    print("ENHANCED REWARD CALCULATOR - TEST")
    print("="*80)
    
    for i, event in enumerate(test_events, 1):
        reward = calculator.calculate_reward(event)
        difficulty = calculator.difficulty_estimator.estimate(event)
        
        print(f"\nEvent {i}:")
        print(f"  Artifact: {event.artifact_type}")
        print(f"  Validation Score: {event.validation_score}")
        print(f"  Feedback Type: {event.feedback_type.value}")
        print(f"  Age: {(time.time() - event.timestamp) / 86400:.1f} days")
        print(f"  Difficulty: {difficulty:.3f}")
        print(f"  → Reward: {reward:.3f}")
    
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    stats = calculator.get_statistics()
    print(json.dumps(stats, indent=2))

