"""
Performance Tracker for Fine-Tuned Models
Tracks model performance over time with:
1. Train/Validation split (80/20 stratified)
2. Evaluation metrics (score, success rate, latency)
3. Performance history tracking
4. Best model checkpointing
5. Early stopping detection
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
import json
import time


@dataclass
class PerformanceMetrics:
    """Metrics for a single evaluation"""
    model_id: str
    artifact_type: str
    timestamp: float
    
    # Validation metrics
    avg_validation_score: float  # Average score (0-100)
    success_rate: float  # Percentage with score >= 70
    avg_reward: float  # Average reward (-1 to 1)
    
    # Performance metrics
    avg_latency: float  # Average generation time (seconds)
    
    # Sample counts
    n_samples: int
    
    # Optional: per-example results
    example_scores: List[float] = field(default_factory=list)
    
    def is_better_than(self, other: 'PerformanceMetrics') -> bool:
        """Check if this metrics is better than another"""
        # Primary: validation score
        if abs(self.avg_validation_score - other.avg_validation_score) > 2.0:
            return self.avg_validation_score > other.avg_validation_score
        
        # Secondary: success rate
        if abs(self.success_rate - other.success_rate) > 0.05:
            return self.success_rate > other.success_rate
        
        # Tertiary: latency (lower is better)
        return self.avg_latency < other.avg_latency


class PerformanceTracker:
    """
    Track model performance over time with validation sets.
    
    Workflow:
    1. Split examples into train (80%) and validation (20%)
    2. Train on train set
    3. Evaluate on validation set
    4. Track metrics over time
    5. Identify best model
    6. Detect early stopping conditions
    """
    
    def __init__(
        self,
        validation_split: float = 0.2,
        min_validation_samples: int = 10,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize performance tracker.
        
        Args:
            validation_split: Fraction of data for validation (0.2 = 20%)
            min_validation_samples: Minimum samples needed for validation
            storage_dir: Directory to persist metrics
        """
        self.validation_split = validation_split
        self.min_validation_samples = min_validation_samples
        
        # Track performance history per artifact type
        self.performance_history: Dict[str, List[PerformanceMetrics]] = defaultdict(list)
        
        # Track best models per artifact type
        self.best_models: Dict[str, PerformanceMetrics] = {}
        
        # Storage
        self.storage_dir = storage_dir or Path("training_jobs/performance_tracking")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "performance_history.json"
        self.best_models_file = self.storage_dir / "best_models.json"
        
        # Load existing data
        self._load_history()
        self._load_best_models()
    
    def split_train_validation(
        self,
        examples: List[Any],
        stratify_by: str = 'artifact_type'
    ) -> Tuple[List[Any], List[Any]]:
        """
        Split examples into train/validation sets.
        
        Uses stratified sampling to ensure balanced representation
        of all artifact types in validation set.
        
        Args:
            examples: List of feedback events or training examples
            stratify_by: Attribute to stratify by (usually 'artifact_type')
        
        Returns:
            Tuple of (train_set, validation_set)
        """
        # Group by stratification key
        groups = defaultdict(list)
        for example in examples:
            key = getattr(example, stratify_by, 'unknown')
            groups[key].append(example)
        
        train_set = []
        val_set = []
        
        # Split each group separately
        for group_key, group_examples in groups.items():
            n = len(group_examples)
            
            if n < 5:
                # Too few examples - use all for training
                train_set.extend(group_examples)
                print(f"[PERF_TRACKER] {group_key}: {n} examples (all → train, too few for validation)")
            else:
                # Split with stratification
                val_size = max(self.min_validation_samples, int(n * self.validation_split))
                val_size = min(val_size, n // 2)  # Never more than 50%
                
                # Shuffle for randomness (deterministic with seed for reproducibility)
                import random
                random.seed(42)
                shuffled = group_examples.copy()
                random.shuffle(shuffled)
                
                val_set.extend(shuffled[:val_size])
                train_set.extend(shuffled[val_size:])
                
                print(f"[PERF_TRACKER] {group_key}: {n} examples → {len(shuffled[val_size:])} train, {val_size} val")
        
        return train_set, val_set
    
    def record_metrics(self, metrics: PerformanceMetrics):
        """
        Record performance metrics for a model.
        
        Args:
            metrics: Performance metrics to record
        """
        artifact_type = metrics.artifact_type
        
        # Add to history
        self.performance_history[artifact_type].append(metrics)
        
        # Update best model if this is better
        if artifact_type not in self.best_models:
            self.best_models[artifact_type] = metrics
            print(f"[PERF_TRACKER] New best model for {artifact_type}: {metrics.avg_validation_score:.1f}")
        elif metrics.is_better_than(self.best_models[artifact_type]):
            old_score = self.best_models[artifact_type].avg_validation_score
            self.best_models[artifact_type] = metrics
            print(f"[PERF_TRACKER] Updated best model for {artifact_type}: {old_score:.1f} → {metrics.avg_validation_score:.1f}")
        
        # Save to disk
        self._save_history()
        self._save_best_models()
    
    def get_performance_trend(
        self,
        artifact_type: str,
        last_n: Optional[int] = None
    ) -> Dict[str, List[float]]:
        """
        Get performance trend over time for an artifact type.
        
        Args:
            artifact_type: Type of artifact
            last_n: Number of recent evaluations to return (None = all)
        
        Returns:
            Dict with lists of: timestamps, scores, success_rates, latencies
        """
        history = self.performance_history.get(artifact_type, [])
        
        if last_n:
            history = history[-last_n:]
        
        if not history:
            return {
                'timestamps': [],
                'scores': [],
                'success_rates': [],
                'latencies': [],
                'rewards': []
            }
        
        return {
            'timestamps': [m.timestamp for m in history],
            'scores': [m.avg_validation_score for m in history],
            'success_rates': [m.success_rate for m in history],
            'latencies': [m.avg_latency for m in history],
            'rewards': [m.avg_reward for m in history]
        }
    
    def check_early_stopping(
        self,
        artifact_type: str,
        patience: int = 5,
        min_improvement: float = 1.0
    ) -> bool:
        """
        Check if training should stop early.
        
        Early stopping conditions:
        - No improvement in validation score for `patience` evaluations
        - Improvement threshold: `min_improvement` points
        
        Args:
            artifact_type: Type of artifact
            patience: Number of evaluations to wait without improvement
            min_improvement: Minimum improvement in score to reset patience
        
        Returns:
            bool: True if should stop early, False otherwise
        """
        history = self.performance_history.get(artifact_type, [])
        
        if len(history) < patience + 1:
            return False  # Not enough evaluations yet
        
        # Get last N+1 evaluations
        recent = history[-(patience + 1):]
        best_score = recent[0].avg_validation_score
        
        # Check if any recent evaluation improved by min_improvement
        for metrics in recent[1:]:
            if metrics.avg_validation_score >= best_score + min_improvement:
                return False  # Improvement found, continue training
            best_score = max(best_score, metrics.avg_validation_score)
        
        # No improvement in last N evaluations
        print(f"[PERF_TRACKER] Early stopping triggered for {artifact_type} (no improvement in {patience} evaluations)")
        return True
    
    def get_best_model(self, artifact_type: str) -> Optional[PerformanceMetrics]:
        """Get best model metrics for an artifact type"""
        return self.best_models.get(artifact_type)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        total_evaluations = sum(len(history) for history in self.performance_history.values())
        
        # Calculate improvement statistics
        improvements = {}
        for artifact_type, history in self.performance_history.items():
            if len(history) >= 2:
                first_score = history[0].avg_validation_score
                best_score = max(m.avg_validation_score for m in history)
                improvement = best_score - first_score
                improvements[artifact_type] = {
                    'first_score': first_score,
                    'best_score': best_score,
                    'improvement': improvement,
                    'improvement_pct': (improvement / first_score * 100) if first_score > 0 else 0
                }
        
        return {
            'total_evaluations': total_evaluations,
            'tracked_artifacts': len(self.performance_history),
            'best_models': {
                artifact_type: {
                    'model_id': metrics.model_id,
                    'score': metrics.avg_validation_score,
                    'success_rate': metrics.success_rate,
                    'timestamp': metrics.timestamp
                }
                for artifact_type, metrics in self.best_models.items()
            },
            'improvements': improvements
        }
    
    def _save_history(self):
        """Save performance history to disk"""
        try:
            data = {
                artifact_type: [asdict(m) for m in history]
                for artifact_type, history in self.performance_history.items()
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save performance history: {e}")
    
    def _load_history(self):
        """Load performance history from disk"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for artifact_type, metrics_list in data.items():
                self.performance_history[artifact_type] = [
                    PerformanceMetrics(**m) for m in metrics_list
                ]
            
            print(f"[PERF_TRACKER] Loaded history for {len(self.performance_history)} artifact types")
        except Exception as e:
            print(f"[WARN] Could not load performance history: {e}")
    
    def _save_best_models(self):
        """Save best models to disk"""
        try:
            data = {
                artifact_type: asdict(metrics)
                for artifact_type, metrics in self.best_models.items()
            }
            with open(self.best_models_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save best models: {e}")
    
    def _load_best_models(self):
        """Load best models from disk"""
        if not self.best_models_file.exists():
            return
        
        try:
            with open(self.best_models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for artifact_type, metrics_dict in data.items():
                self.best_models[artifact_type] = PerformanceMetrics(**metrics_dict)
            
            print(f"[PERF_TRACKER] Loaded best models for {len(self.best_models)} artifact types")
        except Exception as e:
            print(f"[WARN] Could not load best models: {e}")


# Example usage
if __name__ == "__main__":
    import random
    
    tracker = PerformanceTracker()
    
    print("="*80)
    print("PERFORMANCE TRACKER - TEST")
    print("="*80)
    
    # Simulate training progression for ERD
    print("\nSimulating ERD training progression:")
    print("-" * 40)
    
    base_score = 65.0
    for i in range(10):
        # Simulate improving performance
        score = base_score + i * 2 + random.uniform(-1, 1)
        success_rate = min(1.0, score / 100 + 0.1)
        latency = 10.0 - i * 0.5  # Improving latency
        
        metrics = PerformanceMetrics(
            model_id=f"erd_mistral_ft_{i}",
            artifact_type="erd",
            timestamp=time.time() + i * 86400,  # Simulate daily evaluations
            avg_validation_score=score,
            success_rate=success_rate,
            avg_reward=score / 100 - 0.3,
            avg_latency=latency,
            n_samples=20
        )
        
        tracker.record_metrics(metrics)
        print(f"  Evaluation {i+1}: Score {score:.1f}, Success Rate {success_rate:.1%}, Latency {latency:.1f}s")
    
    # Check early stopping
    print("\n" + "-" * 40)
    should_stop = tracker.check_early_stopping("erd", patience=3)
    print(f"Early stopping? {should_stop}")
    
    # Get performance trend
    print("\n" + "="*80)
    print("PERFORMANCE TREND")
    print("="*80)
    trend = tracker.get_performance_trend("erd")
    print(f"Evaluations: {len(trend['scores'])}")
    print(f"Score progression: {' → '.join(f'{s:.1f}' for s in trend['scores'][:5])} ...")
    print(f"Best score: {max(trend['scores']):.1f}")
    
    # Get summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    summary = tracker.get_summary()
    print(json.dumps(summary, indent=2))

