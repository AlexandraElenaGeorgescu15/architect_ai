"""
Adaptive Learning Loop - Self-Improving AI System

This is the CORE of the self-learning pipeline. It implements:
1. Online learning from feedback
2. Reinforcement learning with reward signals
3. Automatic training batch generation
4. Model fine-tuning from production data

WORKFLOW:
User Request → AI Generation → Validation → Feedback → Training Batch → Fine-tune Model

The system learns from EVERY interaction without manual intervention.
"""

import sys
# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        import io
        # Check if already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        # Already wrapped, closed, or not available
        pass

import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
from enum import Enum
import asyncio


class FeedbackType(Enum):
    """Type of feedback received"""
    SUCCESS = "success"  # AI output accepted without changes
    USER_CORRECTION = "user_correction"  # User modified AI output
    VALIDATION_FAILURE = "validation_failure"  # Failed programmatic validation
    EXPLICIT_POSITIVE = "explicit_positive"  # User clicked "Good"
    EXPLICIT_NEGATIVE = "explicit_negative"  # User clicked "Bad"


@dataclass
class FeedbackEvent:
    """Single feedback event from production"""
    timestamp: float
    feedback_type: FeedbackType
    input_data: str  # Original user request
    ai_output: str  # What AI generated
    corrected_output: Optional[str]  # What user corrected it to (if applicable)
    context: Dict[str, Any]  # RAG context, meeting notes, etc.
    validation_score: float  # 0-100 from output_validator
    artifact_type: str  # 'erd', 'code', 'html', etc.
    model_used: str  # Which model generated this
    reward_signal: float  # -1 to +1 (RL reward)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_training_example(self) -> Dict[str, str]:
        """Convert to training example format"""
        # For successful outputs, use AI output
        # For corrected outputs, use user correction as target
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
    priority: int  # 1-10, higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)


class RewardCalculator:
    """
    Calculates reward signals for reinforcement learning.
    
    Reward formula:
    - Validation pass + No user changes = +1.0
    - Validation pass + Minor changes = +0.5
    - Validation warning + Accepted = +0.3
    - Validation failure = -0.5
    - User explicit negative = -1.0
    """
    
    @staticmethod
    def calculate_reward(event: FeedbackEvent) -> float:
        """Calculate RL reward signal"""
        base_reward = 0.0
        
        # Validation-based reward
        if event.validation_score >= 90:
            base_reward += 0.6
        elif event.validation_score >= 70:
            base_reward += 0.3
        elif event.validation_score >= 50:
            base_reward += 0.1
        else:
            base_reward -= 0.5
        
        # Feedback type adjustment
        if event.feedback_type == FeedbackType.SUCCESS:
            base_reward += 0.4  # Total: up to +1.0
        elif event.feedback_type == FeedbackType.USER_CORRECTION:
            # Check magnitude of correction
            if event.corrected_output:
                similarity = calculate_similarity(event.ai_output, event.corrected_output)
                if similarity > 0.8:
                    base_reward += 0.2  # Minor correction
                else:
                    base_reward += 0.0  # Major correction
        elif event.feedback_type == FeedbackType.VALIDATION_FAILURE:
            base_reward -= 0.3
        elif event.feedback_type == FeedbackType.EXPLICIT_POSITIVE:
            base_reward += 0.5
        elif event.feedback_type == FeedbackType.EXPLICIT_NEGATIVE:
            base_reward = -1.0
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, base_reward))


def calculate_similarity(text1: str, text2: str) -> float:
    """Simple Levenshtein-like similarity (0-1)"""
    if not text1 or not text2:
        return 0.0
    
    # Simple character-level similarity
    set1 = set(text1.lower())
    set2 = set(text2.lower())
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0


class AdaptiveLearningLoop:
    """
    Main adaptive learning system.
    
    Collects feedback, calculates rewards, builds training batches,
    and triggers model fine-tuning automatically.
    """
    
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path("training_jobs/adaptive_learning")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedback_events: List[FeedbackEvent] = []
        self.training_batches: List[TrainingBatch] = []
        self.reward_calculator = RewardCalculator()
        
        # Configuration
        self.batch_size = 50  # Create batch after N successful examples
        self.min_reward_threshold = 0.3  # Only include examples with reward > threshold
        self.priority_weights = {
            FeedbackType.USER_CORRECTION: 10,  # Highest priority
            FeedbackType.EXPLICIT_POSITIVE: 8,
            FeedbackType.SUCCESS: 5,
            FeedbackType.VALIDATION_FAILURE: 3,
            FeedbackType.EXPLICIT_NEGATIVE: 1
        }
        
        # Load existing feedback
        self._load_feedback_history()
    
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
        Record a feedback event from production.
        
        This is called EVERY time AI generates something.
        
        Returns:
            FeedbackEvent if quality is acceptable, None if discarded
        """
        # QUALITY GATE: Only accept high-quality feedback for training
        # This prevents contaminating the training data with bad examples
        
        # Check 1: Validation score must be > 70 (not just > 60)
        if validation_score < 70.0:
            print(f"[ADAPTIVE_LEARNING] ⛔ Discarded low-quality feedback (score: {validation_score:.1f} < 70.0)")
            print(f"[ADAPTIVE_LEARNING]    Artifact: {artifact_type}, Model: {model_used}")
            return None
        
        # Check 2: Must not be generic/placeholder content
        is_generic_content = context.get('is_generic_content', False) if context else False
        if is_generic_content:
            print(f"[ADAPTIVE_LEARNING] ⛔ Discarded generic content (not project-specific)")
            print(f"[ADAPTIVE_LEARNING]    Artifact: {artifact_type}, Model: {model_used}, Score: {validation_score:.1f}")
            return None
        
        # Check 3: For "success" feedback, ensure validation passed
        if feedback_type == FeedbackType.SUCCESS and validation_score < 80.0:
            print(f"[ADAPTIVE_LEARNING] ⛔ Discarded 'success' feedback with score < 80.0 ({validation_score:.1f})")
            print(f"[ADAPTIVE_LEARNING]    Artifact: {artifact_type}, Model: {model_used}")
            return None
        
        # Quality checks passed - record feedback
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
            reward_signal=0.0  # Calculated below
        )
        
        # Calculate reward
        event.reward_signal = self.reward_calculator.calculate_reward(event)
        
        # Store event
        self.feedback_events.append(event)
        self._save_feedback_event(event)
        
        print(f"[ADAPTIVE_LEARNING] ✅ Recorded feedback: {feedback_type.value}, "
              f"reward={event.reward_signal:.2f}, validation={validation_score:.1f}")
        
        # Check if we should create a training batch
        self._check_and_create_batch()
        
        return event
    
    def _check_and_create_batch(self):
        """
        Check if we have enough good examples to create a training batch.
        
        NOW GROUPS BY (artifact_type, model) PAIR:
        - Each (artifact_type, model) pair gets its own fine-tuned model
        - Only creates batch when specific pair has 50+ examples
        - Example: (erd, mistral:7b) gets fine-tuned separately from (api_docs, codellama:7b)
        """
        # Filter high-quality examples (reward > threshold)
        high_quality = [
            e for e in self.feedback_events
            if e.reward_signal >= self.min_reward_threshold
        ]
        
        # Group by (artifact_type, model_used) pair
        pairs: Dict[Tuple[str, str], List[FeedbackEvent]] = {}
        for event in high_quality:
            pair_key = (event.artifact_type, event.model_used)
            if pair_key not in pairs:
                pairs[pair_key] = []
            pairs[pair_key].append(event)
        
        # Check each pair and create batch if threshold met
        for (artifact_type, model_used), events in pairs.items():
            if len(events) >= self.batch_size:
                print(f"[ADAPTIVE_LEARNING] 🎯 Creating batch for ({artifact_type}, {model_used}) - {len(events)} examples")
                self._create_training_batch_for_pair(artifact_type, model_used, events[:self.batch_size])
                # Remove used examples
                for event in events[:self.batch_size]:
                    self.feedback_events.remove(event)
    
    def _create_training_batch_for_pair(
        self, 
        artifact_type: str, 
        model_used: str, 
        events: List[FeedbackEvent]
    ):
        """
        Create a training batch for a specific (artifact_type, model) pair.
        
        This ensures each model gets fine-tuned specifically for the artifact type it generates.
        """
        # Convert to training examples
        examples = [e.to_training_example() for e in events]
        
        # Calculate priority based on feedback types
        avg_priority = sum(
            self.priority_weights.get(e.feedback_type, 5) for e in events
        ) / len(events)
        
        # Create batch ID that includes artifact_type and model
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_id = f"batch_{artifact_type}_{model_used.replace(':', '_')}_{timestamp}"
        
        batch = TrainingBatch(
            batch_id=batch_id,
            created_at=time.time(),
            examples=examples,
            priority=int(avg_priority),
            metadata={
                'n_examples': len(examples),
                'avg_reward': sum(e.reward_signal for e in events) / len(events),
                'artifact_types': [artifact_type],  # Single artifact type
                'models_used': [model_used],  # Single model
                'target_artifact_type': artifact_type,  # For routing
                'target_model': model_used  # For routing
            }
        )
        
        self.training_batches.append(batch)
        self._save_training_batch(batch)
        
        print(f"[ADAPTIVE_LEARNING] ✅ Created training batch: {batch.batch_id}")
        print(f"  Artifact Type: {artifact_type}")
        print(f"  Model: {model_used}")
        print(f"  Priority: {batch.priority}/10")
        print(f"  Examples: {len(examples)}")
        print(f"  Avg Reward: {batch.metadata['avg_reward']:.2f}")
        
        # Trigger fine-tuning for this specific pair
        self._trigger_finetuning_for_pair(batch, artifact_type, model_used)
    
    def _create_training_batch(self, events: List[FeedbackEvent]):
        """DEPRECATED: Use _create_training_batch_for_pair instead"""
        # Fallback for old code paths
        if not events:
            return
        artifact_type = events[0].artifact_type
        model_used = events[0].model_used
        self._create_training_batch_for_pair(artifact_type, model_used, events)
    
    def _trigger_finetuning_for_pair(
        self, 
        batch: TrainingBatch, 
        artifact_type: str, 
        model_used: str
    ):
        """
        Trigger model fine-tuning for a specific (artifact_type, model) pair.
        
        The fine-tuned model will be specialized for generating this artifact type.
        """
        try:
            from components.local_finetuning import local_finetuning_system
            
            # Create dataset file
            dataset_file = self.storage_dir / f"{batch.batch_id}.jsonl"
            
            with open(dataset_file, 'w', encoding='utf-8') as f:
                for example in batch.examples:
                    f.write(json.dumps(example) + '\n')
            
            print(f"[ADAPTIVE_LEARNING] 📦 Saved training dataset: {dataset_file}")
            print(f"[ADAPTIVE_LEARNING] 🎯 Target: {artifact_type} artifacts using {model_used}")
            print(f"[ADAPTIVE_LEARNING] 🔄 Queuing fine-tuning job...")
            
            # Queue fine-tuning job (async) with artifact_type and model info
            # NOTE: Actual fine-tuning happens in background to not block app
            self._queue_finetuning_job(
                batch.batch_id, 
                dataset_file, 
                batch.priority,
                artifact_type=artifact_type,
                model_used=model_used
            )
            
        except Exception as e:
            print(f"[ERROR] Failed to trigger fine-tuning: {e}")
    
    def _trigger_finetuning(self, batch: TrainingBatch):
        """DEPRECATED: Use _trigger_finetuning_for_pair instead"""
        artifact_type = batch.metadata.get('target_artifact_type', batch.metadata['artifact_types'][0])
        model_used = batch.metadata.get('target_model', batch.metadata['models_used'][0])
        self._trigger_finetuning_for_pair(batch, artifact_type, model_used)
    
    def _queue_finetuning_job(
        self, 
        batch_id: str, 
        dataset_file: Path, 
        priority: int,
        artifact_type: str = None,
        model_used: str = None
    ):
        """Queue fine-tuning job for background processing"""
        job_file = self.storage_dir / f"job_{batch_id}.json"
        
        job_config = {
            'job_id': batch_id,
            'dataset_file': str(dataset_file),
            'priority': priority,
            'status': 'pending',  # ✅ FIXED: Changed from 'queued' to 'pending' (worker looks for 'pending')
            'created_at': time.time(),
            'artifact_type': artifact_type,  # Track artifact type
            'model_used': model_used,  # Track model
            'base_model': 'codellama:7b-instruct',
            'epochs': 3,
            'learning_rate': 2e-5
        }
        
        job_file.write_text(json.dumps(job_config, indent=2), encoding='utf-8')
        
        print(f"[ADAPTIVE_LEARNING] ✅ Queued job: {job_file}")
        
        # Automatically trigger background training (non-blocking)
        self._start_background_training(job_file)
    
    def _start_background_training(self, job_file: Path):
        """Start background training automatically (non-blocking)"""
        import subprocess
        import sys
        
        try:
            # Start fine-tuning worker in background process (non-blocking)
            worker_script = Path(__file__).parent.parent / "workers" / "finetuning_worker.py"
            
            if not worker_script.exists():
                print(f"[WARNING] Worker script not found: {worker_script}")
                print(f"[INFO] Manual trigger: python workers/finetuning_worker.py")
                return
            
            # Start worker as background process (detached, non-blocking)
            if sys.platform == 'win32':
                # Windows: Start in new process with no window
                subprocess.Popen(
                    [sys.executable, str(worker_script), "--single-job", str(job_file)],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Linux/Mac: Start as background daemon
                subprocess.Popen(
                    [sys.executable, str(worker_script), "--single-job", str(job_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            print(f"[ADAPTIVE_LEARNING] 🚀 Automatic training started in background")
            print(f"[INFO] Training will complete in 5-10 minutes")
            
        except Exception as e:
            print(f"[WARNING] Could not auto-start training: {e}")
            print(f"[INFO] Manual trigger: python workers/finetuning_worker.py")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the learning system"""
        if not self.feedback_events:
            return {
                'total_feedback': 0,
                'training_batches_created': len(self.training_batches)
            }
        
        return {
            'total_feedback': len(self.feedback_events),
            'avg_reward': sum(e.reward_signal for e in self.feedback_events) / len(self.feedback_events),
            'feedback_by_type': {
                ft.value: sum(1 for e in self.feedback_events if e.feedback_type == ft)
                for ft in FeedbackType
            },
            'training_batches_created': len(self.training_batches),
            'total_training_examples': sum(len(b.examples) for b in self.training_batches),
            'avg_validation_score': sum(e.validation_score for e in self.feedback_events) / len(self.feedback_events)
        }
    
    def _save_feedback_event(self, event: FeedbackEvent):
        """Save feedback event to disk"""
        feedback_file = self.storage_dir / "feedback_events.jsonl"
        
        with open(feedback_file, 'a', encoding='utf-8') as f:
            event_dict = asdict(event)
            # Convert enum to string for JSON serialization
            event_dict['feedback_type'] = event.feedback_type.value
            f.write(json.dumps(event_dict) + '\n')
    
    def _save_training_batch(self, batch: TrainingBatch):
        """Save training batch to disk"""
        batch_file = self.storage_dir / f"{batch.batch_id}.json"
        batch_file.write_text(json.dumps(asdict(batch), indent=2), encoding='utf-8')
    
    def _load_feedback_history(self):
        """Load historical feedback events"""
        feedback_file = self.storage_dir / "feedback_events.jsonl"
        
        if not feedback_file.exists():
            return
        
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Convert back to FeedbackEvent
                        # (simplified for now)
                        pass
        except Exception as e:
            print(f"[WARN] Failed to load feedback history: {e}")


# Global instance
_adaptive_loop = None

def get_adaptive_loop() -> AdaptiveLearningLoop:
    """Get global adaptive learning loop"""
    global _adaptive_loop
    if _adaptive_loop is None:
        _adaptive_loop = AdaptiveLearningLoop()
    return _adaptive_loop


# Example usage
if __name__ == '__main__':
    loop = get_adaptive_loop()
    
    # Simulate feedback events
    
    # Example 1: Successful generation
    loop.record_feedback(
        input_data="Generate ERD for e-commerce",
        ai_output="erDiagram\n  User {}\n  Order {}",
        artifact_type="erd",
        model_used="codellama-7b",
        validation_score=85.0,
        feedback_type=FeedbackType.SUCCESS
    )
    
    # Example 2: User correction
    loop.record_feedback(
        input_data="Generate user controller",
        ai_output="class UserController { }",
        corrected_output="class UserController {\n  getUsers() {}\n}",
        artifact_type="code",
        model_used="codellama-7b",
        validation_score=70.0,
        feedback_type=FeedbackType.USER_CORRECTION
    )
    
    # Example 3: Validation failure
    loop.record_feedback(
        input_data="Generate HTML form",
        ai_output="<div>test</div>",
        artifact_type="html",
        model_used="codellama-7b",
        validation_score=45.0,
        feedback_type=FeedbackType.VALIDATION_FAILURE
    )
    
    # Show stats
    stats = loop.get_learning_stats()
    print("\n=== LEARNING STATISTICS ===")
    print(json.dumps(stats, indent=2))
