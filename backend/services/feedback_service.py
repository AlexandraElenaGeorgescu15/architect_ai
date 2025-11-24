"""
Feedback Service - Refactored from components/adaptive_learning*.py
Handles user feedback collection and training batch creation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)

# Optional imports for adaptive learning (graceful degradation)
try:
    from components.feedback_models import FeedbackEvent, FeedbackType, TrainingBatch
    from components.adaptive_learning_enhanced import EnhancedAdaptiveLearningLoop
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError:
    try:
        from components.adaptive_learning import AdaptiveLearningLoop, FeedbackEvent, FeedbackType
        ADAPTIVE_LEARNING_AVAILABLE = True
        EnhancedAdaptiveLearningLoop = None
    except ImportError:
        ADAPTIVE_LEARNING_AVAILABLE = False
        logger.warning("Adaptive learning not available. Feedback will be stored but not processed.")


class FeedbackService:
    """
    Feedback service for collecting and processing user feedback.
    
    Features:
    - Feedback event recording
    - Training batch creation
    - Quality gating (only high-quality feedback)
    - Reward calculation
    - Training trigger logic
    """
    
    def __init__(self):
        """Initialize Feedback Service."""
        if ADAPTIVE_LEARNING_AVAILABLE:
            if EnhancedAdaptiveLearningLoop:
                self.learning_loop = EnhancedAdaptiveLearningLoop()
            else:
                from components.adaptive_learning import AdaptiveLearningLoop
                self.learning_loop = AdaptiveLearningLoop()
        else:
            self.learning_loop = None
        
        self.feedback_storage: List[Dict[str, Any]] = []
        
        logger.info("Feedback Service initialized")
    
    async def record_feedback(
        self,
        artifact_id: str,
        artifact_type: str,
        ai_output: str,
        validation_score: float,
        feedback_type: str,
        score: Optional[float] = None,
        notes: Optional[str] = None,
        corrected_output: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record user feedback on an artifact.
        
        Args:
            artifact_id: Artifact identifier
            artifact_type: Type of artifact
            ai_output: Original AI-generated output
            validation_score: Validation score (0-100)
            feedback_type: Type of feedback (positive, negative, correction)
            score: Optional user-provided score
            notes: Optional user notes
            corrected_output: Optional corrected output
            context: Optional additional context
        
        Returns:
            Dictionary with feedback recording result
        """
        # Map feedback_type string to FeedbackType enum
        feedback_type_map = {
            "positive": FeedbackType.EXPLICIT_POSITIVE if ADAPTIVE_LEARNING_AVAILABLE else "positive",
            "negative": FeedbackType.EXPLICIT_NEGATIVE if ADAPTIVE_LEARNING_AVAILABLE else "negative",
            "correction": FeedbackType.USER_CORRECTION if ADAPTIVE_LEARNING_AVAILABLE else "correction",
            "success": FeedbackType.SUCCESS if ADAPTIVE_LEARNING_AVAILABLE else "success",
            "validation_failure": FeedbackType.VALIDATION_FAILURE if ADAPTIVE_LEARNING_AVAILABLE else "validation_failure"
        }
        
        fb_type = feedback_type_map.get(feedback_type, feedback_type)
        
        # Use adaptive learning loop if available
        if self.learning_loop:
            try:
                # Extract input_data from context or use meeting_notes
                input_data = context.get("meeting_notes", "") if context else ""
                model_used = context.get("model_used", "unknown") if context else "unknown"
                
                # Record feedback
                event = self.learning_loop.record_feedback(
                    input_data=input_data,
                    ai_output=ai_output,
                    artifact_type=artifact_type,
                    model_used=model_used,
                    validation_score=validation_score,
                    feedback_type=fb_type if isinstance(fb_type, FeedbackType) else FeedbackType.SUCCESS,
                    corrected_output=corrected_output,
                    context=context or {}
                )
                
                if event:
                    # Feedback was accepted and recorded
                    return {
                        "success": True,
                        "feedback_id": artifact_id,
                        "event_recorded": True,
                        "reward_signal": getattr(event, 'reward_signal', 0.0),
                        "training_triggered": False,  # Would check if batch was created
                        "message": "Feedback recorded successfully"
                    }
                else:
                    # Feedback was rejected (quality gate)
                    return {
                        "success": True,
                        "feedback_id": artifact_id,
                        "event_recorded": False,
                        "message": "Feedback rejected (quality gate - validation score too low or generic content)"
                    }
            except Exception as e:
                logger.error(f"Error recording feedback with adaptive learning: {e}", exc_info=True)
                # Fall through to basic storage
        
        # Fallback: Basic storage
        feedback_entry = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "feedback_type": feedback_type,
            "validation_score": validation_score,
            "user_score": score,
            "notes": notes,
            "corrected_output": corrected_output,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        
        self.feedback_storage.append(feedback_entry)
        
        # Connect to finetuning pool: If thumbs up (positive) or correction, add to pool
        # Thumbs up = treat as 85+ quality, correction = use corrected output with 85+ score
        if feedback_type in ["positive", "correction"]:
            try:
                from backend.services.finetuning_pool import get_pool
                finetuning_pool = get_pool()
                
                # Use corrected output if available, otherwise use original
                content_to_add = corrected_output if corrected_output else ai_output
                
                # For thumbs up, treat as 85+ score; for correction, use validation_score or 85
                effective_score = 85.0 if feedback_type == "positive" else max(validation_score, 85.0)
                
                # Extract meeting_notes from context
                meeting_notes = context.get("meeting_notes", "") if context else ""
                model_used = context.get("model_used", "unknown") if context else "unknown"
                
                added = finetuning_pool.add_example(
                    artifact_type=artifact_type,
                    content=content_to_add,
                    meeting_notes=meeting_notes,
                    validation_score=effective_score,
                    model_used=model_used,
                    context=context
                )
                
                if added:
                    logger.info(f"User feedback ({feedback_type}) added to finetuning pool for {artifact_type}")
            except Exception as e:
                logger.warning(f"Failed to add feedback to finetuning pool: {e}")
        
        return {
            "success": True,
            "feedback_id": artifact_id,
            "event_recorded": True,
            "message": "Feedback stored (adaptive learning not available)"
        }
    
    def get_feedback_history(
        self,
        artifact_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get feedback history.
        
        Args:
            artifact_id: Optional artifact ID filter
            artifact_type: Optional artifact type filter
            limit: Maximum number of entries to return
        
        Returns:
            List of feedback entries
        """
        if self.learning_loop and hasattr(self.learning_loop, 'feedback_events'):
            # Get from adaptive learning loop
            events = self.learning_loop.feedback_events
            
            # Filter
            if artifact_id:
                events = [e for e in events if getattr(e, 'artifact_id', None) == artifact_id]
            if artifact_type:
                events = [e for e in events if getattr(e, 'artifact_type', None) == artifact_type]
            
            # Convert to dicts
            result = []
            for event in events[-limit:]:
                result.append({
                    "artifact_id": getattr(event, 'artifact_id', 'unknown'),
                    "artifact_type": getattr(event, 'artifact_type', 'unknown'),
                    "feedback_type": getattr(event, 'feedback_type', 'unknown'),
                    "validation_score": getattr(event, 'validation_score', 0.0),
                    "reward_signal": getattr(event, 'reward_signal', 0.0),
                    "timestamp": datetime.fromtimestamp(getattr(event, 'timestamp', 0)).isoformat(),
                    "corrected_output": getattr(event, 'corrected_output', None)
                })
            
            return result
        
        # Fallback: Basic storage
        feedback_list = self.feedback_storage.copy()
        
        if artifact_id:
            feedback_list = [f for f in feedback_list if f.get("artifact_id") == artifact_id]
        if artifact_type:
            feedback_list = [f for f in feedback_list if f.get("artifact_type") == artifact_type]
        
        return feedback_list[-limit:]
    
    def get_training_stats(self) -> Dict[str, Any]:
        """
        Get training statistics.
        
        Returns:
            Dictionary with training statistics
        """
        if self.learning_loop and hasattr(self.learning_loop, 'feedback_events'):
            events = self.learning_loop.feedback_events
            
            # Calculate stats
            total_feedback = len(events)
            avg_validation = sum(getattr(e, 'validation_score', 0.0) for e in events) / total_feedback if total_feedback > 0 else 0.0
            avg_reward = sum(getattr(e, 'reward_signal', 0.0) for e in events) / total_feedback if total_feedback > 0 else 0.0
            
            # Count by artifact type
            by_type = {}
            for event in events:
                artifact_type = getattr(event, 'artifact_type', 'unknown')
                by_type[artifact_type] = by_type.get(artifact_type, 0) + 1
            
            return {
                "total_feedback_events": total_feedback,
                "average_validation_score": avg_validation,
                "average_reward_signal": avg_reward,
                "feedback_by_artifact_type": by_type,
                "training_batches_created": 0,  # Would track this
                "adaptive_learning_enabled": True
            }
        
        # Fallback stats
        return {
            "total_feedback_events": len(self.feedback_storage),
            "average_validation_score": 0.0,
            "average_reward_signal": 0.0,
            "feedback_by_artifact_type": {},
            "training_batches_created": 0,
            "adaptive_learning_enabled": False
        }
    
    def check_training_ready(
        self,
        artifact_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if enough feedback collected to trigger training.
        
        Args:
            artifact_type: Optional artifact type to check
        
        Returns:
            Dictionary with training readiness status
        """
        if not self.learning_loop:
            return {
                "ready": False,
                "reason": "Adaptive learning not available"
            }
        
        # Check if learning loop has batch creation logic
        if hasattr(self.learning_loop, '_check_and_create_batch'):
            # Would trigger batch creation check
            return {
                "ready": False,  # Would check actual readiness
                "reason": "Batch creation check not implemented in service layer"
            }
        
        return {
            "ready": False,
            "reason": "Training readiness check not available"
        }


# Global service instance
_service: Optional[FeedbackService] = None


def get_service() -> FeedbackService:
    """Get or create global Feedback Service instance."""
    global _service
    if _service is None:
        _service = FeedbackService()
    return _service



