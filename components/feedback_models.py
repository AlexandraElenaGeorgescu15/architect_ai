"""
Shared feedback-related data structures used across adaptive learning components.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FeedbackType(Enum):
    """Canonical feedback categories emitted by validation/user review."""

    SUCCESS = "success"
    USER_CORRECTION = "user_correction"
    VALIDATION_FAILURE = "validation_failure"
    EXPLICIT_POSITIVE = "explicit_positive"
    EXPLICIT_NEGATIVE = "explicit_negative"


@dataclass
class FeedbackEvent:
    """Normalized record describing a single feedback event."""

    timestamp: float
    feedback_type: FeedbackType
    input_data: str
    ai_output: str
    corrected_output: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    validation_score: float = 0.0
    artifact_type: str = ""
    model_used: str = ""
    reward_signal: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_training_example(self) -> Dict[str, Any]:
        """Convert the event into a generic fine-tuning example payload."""
        target = self.corrected_output if self.corrected_output else self.ai_output
        return {
            "instruction": f"Generate {self.artifact_type}",
            "input": self.input_data,
            "output": target,
            "context": json.dumps(self.context),
            "quality_score": self.validation_score,
        }


@dataclass
class TrainingBatch:
    """Bundle of curated training examples ready for downstream fine-tuning."""

    batch_id: str
    created_at: float
    examples: List[Dict[str, Any]]
    priority: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    hyperparameters: Optional[Any] = None
