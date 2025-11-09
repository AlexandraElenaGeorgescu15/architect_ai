"""
User Feedback Collection System
Collects thumbs up/down + corrections for fine-tuning local models
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class FeedbackEntry:
    """Single feedback entry for fine-tuning"""
    timestamp: str
    artifact_type: str
    task_type: str
    prompt: str
    system_message: str
    output: str
    rating: str  # "good" or "bad"
    correction: Optional[str]
    model_used: str
    is_local: bool
    generation_time: float
    feedback_id: str
    validation_score: float = 0.0  # Quality score (0-100)
    is_generic_content: bool = False  # Whether content is generic/placeholder


class FeedbackCollector:
    """
    Collect user feedback for fine-tuning local models.
    
    Feedback is saved to disk and can be processed in batches
    for training the Code model on user-specific patterns.
    """
    
    def __init__(self, feedback_dir: str = "outputs/feedback"):
        """
        Initialize feedback collector.
        
        Args:
            feedback_dir: Directory to store feedback files
        """
        self.feedback_dir = Path(feedback_dir)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate good and bad feedback
        self.good_dir = self.feedback_dir / "good"
        self.bad_dir = self.feedback_dir / "bad"
        self.good_dir.mkdir(exist_ok=True)
        self.bad_dir.mkdir(exist_ok=True)
    
    def collect_feedback(
        self,
        artifact_type: str,
        task_type: str,
        prompt: str,
        system_message: str,
        output: str,
        rating: str,  # "good" or "bad"
        model_used: str,
        is_local: bool,
        generation_time: float,
        correction: Optional[str] = None,
        validation_score: float = 0.0,
        is_generic_content: bool = False
    ) -> Optional[str]:
        """
        Save user feedback for later training.
        
        Args:
            artifact_type: Type of artifact (code_prototype, erd, etc.)
            task_type: Task type for model routing (code, mermaid, jira)
            prompt: Original prompt
            system_message: System message used
            output: Generated output
            rating: "good" or "bad"
            model_used: Name of model that generated it
            is_local: True if local Ollama model
            generation_time: Time taken in seconds
            correction: User's corrected version (optional)
            validation_score: Quality score (0-100)
            is_generic_content: Whether content is generic/placeholder
            
        Returns:
            feedback_id: Unique ID for this feedback, or None if discarded
        """
        # QUALITY GATE: Only accept high-quality feedback for training
        # This prevents contaminating the training data with bad examples
        
        # Check 1: For "good" rating, validation score must be > 70
        if rating == "good" and validation_score < 70.0:
            print(f"[FEEDBACK_COLLECTOR] ⛔ Discarded 'good' feedback with low score ({validation_score:.1f} < 70.0)")
            print(f"[FEEDBACK_COLLECTOR]    Artifact: {artifact_type}, Model: {model_used}")
            return None
        
        # Check 2: Must not be generic/placeholder content
        if is_generic_content and rating == "good":
            print(f"[FEEDBACK_COLLECTOR] ⛔ Discarded generic content (not project-specific)")
            print(f"[FEEDBACK_COLLECTOR]    Artifact: {artifact_type}, Model: {model_used}, Score: {validation_score:.1f}")
            return None
        
        # Quality checks passed - record feedback
        # Generate unique ID
        feedback_id = f"{artifact_type}_{int(time.time() * 1000)}"
        
        # Create feedback entry
        entry = FeedbackEntry(
            timestamp=datetime.now().isoformat(),
            artifact_type=artifact_type,
            task_type=task_type,
            prompt=prompt,
            system_message=system_message,
            output=output,
            rating=rating,
            correction=correction,
            model_used=model_used,
            is_local=is_local,
            generation_time=generation_time,
            feedback_id=feedback_id,
            validation_score=validation_score,
            is_generic_content=is_generic_content
        )
        
        # Save to appropriate directory
        target_dir = self.good_dir if rating == "good" else self.bad_dir
        feedback_file = target_dir / f"{feedback_id}.json"
        
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(entry), f, indent=2, ensure_ascii=False)
        
        print(f"[FEEDBACK_COLLECTOR] ✅ Saved {rating} feedback: {feedback_id} (score: {validation_score:.1f})")
        
        return feedback_id
    
    def get_feedback_count(self) -> Dict[str, int]:
        """
        Get count of feedback entries.
        
        Returns:
            Dict with counts: {'good': int, 'bad': int, 'total': int}
        """
        good_count = len(list(self.good_dir.glob("*.json")))
        bad_count = len(list(self.bad_dir.glob("*.json")))
        
        return {
            'good': good_count,
            'bad': bad_count,
            'total': good_count + bad_count
        }
    
    def load_feedback(self, rating: Optional[str] = None, limit: int = 100) -> List[FeedbackEntry]:
        """
        Load feedback entries from disk.
        
        Args:
            rating: Filter by rating ("good", "bad", or None for all)
            limit: Maximum number to load
            
        Returns:
            List of FeedbackEntry objects
        """
        entries = []
        
        # Determine which directories to scan
        if rating == "good":
            dirs_to_scan = [self.good_dir]
        elif rating == "bad":
            dirs_to_scan = [self.bad_dir]
        else:
            dirs_to_scan = [self.good_dir, self.bad_dir]
        
        # Load from each directory
        for dir_path in dirs_to_scan:
            for feedback_file in dir_path.glob("*.json"):
                if len(entries) >= limit:
                    break
                
                try:
                    with open(feedback_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        entries.append(FeedbackEntry(**data))
                except Exception as e:
                    print(f"[WARN] Failed to load {feedback_file}: {e}")
        
        return entries[:limit]
    
    def get_feedback_by_task_type(self, task_type: str, limit: int = 50) -> List[FeedbackEntry]:
        """
        Get feedback filtered by task type (e.g., only 'code' feedback).
        
        Args:
            task_type: Task type to filter by
            limit: Maximum number to load
            
        Returns:
            List of FeedbackEntry objects
        """
        all_feedback = self.load_feedback(limit=limit * 2)  # Load more, then filter
        return [f for f in all_feedback if f.task_type == task_type][:limit]
    
    def prepare_training_dataset(self, task_type: str = "code") -> List[Dict[str, str]]:
        """
        Prepare feedback for fine-tuning.
        
        Format: List of {"prompt": str, "completion": str} dicts
        
        Args:
            task_type: Task type to prepare dataset for (e.g., 'code')
            
        Returns:
            List of training examples
        """
        feedback = self.get_feedback_by_task_type(task_type, limit=500)
        
        training_examples = []
        
        for entry in feedback:
            # Use correction if available (bad feedback with correction)
            # Otherwise use original output (good feedback)
            target_output = entry.correction if entry.correction else entry.output
            
            # Only include if we have a valid target
            if not target_output or len(target_output.strip()) < 10:
                continue
            
            # Format as training example
            example = {
                "prompt": f"{entry.system_message}\n\n{entry.prompt}" if entry.system_message else entry.prompt,
                "completion": target_output,
                "metadata": {
                    "artifact_type": entry.artifact_type,
                    "rating": entry.rating,
                    "timestamp": entry.timestamp
                }
            }
            
            training_examples.append(example)
        
        return training_examples
    
    def export_for_fine_tuning(
        self,
        output_file: str = "finetune_datasets/code_dataset.jsonl",
        task_type: str = "code",
        min_examples: int = 20
    ) -> bool:
        """
        Export feedback as JSONL for fine-tuning.
        
        Args:
            output_file: Path to output JSONL file
            task_type: Task type to export
            min_examples: Minimum number of examples required
            
        Returns:
            True if successful, False if not enough examples
        """
        # Prepare dataset
        examples = self.prepare_training_dataset(task_type)
        
        if len(examples) < min_examples:
            print(f"[ERROR] Not enough examples. Have {len(examples)}, need {min_examples}.")
            return False
        
        # Create output directory
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                f.write(json.dumps(example, ensure_ascii=False) + '\n')
        
        print(f"[SUCCESS] Exported {len(examples)} examples to {output_file}")
        return True
    
    def clear_feedback(self, rating: Optional[str] = None):
        """
        Clear feedback entries (use with caution!).
        
        Args:
            rating: Clear only "good" or "bad" feedback, or None for all
        """
        if rating == "good":
            for f in self.good_dir.glob("*.json"):
                f.unlink()
        elif rating == "bad":
            for f in self.bad_dir.glob("*.json"):
                f.unlink()
        else:
            for f in self.good_dir.glob("*.json"):
                f.unlink()
            for f in self.bad_dir.glob("*.json"):
                f.unlink()


# Global instance
_feedback_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get or create global feedback collector instance"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector

