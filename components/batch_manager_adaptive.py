"""
Adaptive Batch Manager for Fine-Tuning
Dynamically adjusts batch size per artifact type based on:
1. Availability (more examples = larger batches)
2. Quality (higher quality = smaller batches needed)
3. Rarity (rare artifacts = smaller batches to train sooner)
4. Performance trends (improving = increase batch size)
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class ArtifactStats:
    """Statistics for a single artifact type"""
    artifact_type: str
    total_examples: int = 0
    avg_quality: float = 0.0  # Average reward
    batches_created: int = 0
    last_batch_size: int = 0
    last_batch_timestamp: float = 0.0
    quality_trend: List[float] = field(default_factory=list)  # Last N batch qualities
    
    def update_quality(self, quality: float, window_size: int = 10):
        """Update quality trend with new batch quality"""
        self.quality_trend.append(quality)
        if len(self.quality_trend) > window_size:
            self.quality_trend.pop(0)
        self.avg_quality = sum(self.quality_trend) / len(self.quality_trend)


class AdaptiveBatchManager:
    """
    Dynamically adjust batch size per artifact type.
    
    Smaller batches = faster iteration, more frequent updates
    Larger batches = more stable training, less overhead
    
    Strategy:
    - Start small for new artifacts (quick first iteration)
    - Grow batches as more data accumulates
    - Shrink if quality drops
    - Keep rare artifacts small (train sooner)
    """
    
    def __init__(
        self,
        min_batch_size: int = 20,
        max_batch_size: int = 100,
        default_batch_size: int = 50,
        target_quality: float = 0.7,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize adaptive batch manager.
        
        Args:
            min_batch_size: Minimum batch size (never go below this)
            max_batch_size: Maximum batch size (cap to prevent overfitting)
            default_batch_size: Starting batch size for new artifacts
            target_quality: Target average quality (reward) threshold
            storage_dir: Directory to persist statistics
        """
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.default_batch_size = default_batch_size
        self.target_quality = target_quality
        
        # Track per-artifact statistics
        self.artifact_stats: Dict[str, ArtifactStats] = {}
        
        # Storage
        self.storage_dir = storage_dir or Path("training_jobs/batch_manager")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.storage_dir / "artifact_stats.json"
        
        # Load existing statistics
        self._load_statistics()
    
    def calculate_optimal_batch_size(
        self,
        artifact_type: str,
        available_examples: int,
        avg_quality: float
    ) -> int:
        """
        Calculate optimal batch size for an artifact type.
        
        Args:
            artifact_type: Type of artifact (erd, code, etc.)
            available_examples: Number of quality examples available
            avg_quality: Average reward of available examples
        
        Returns:
            int: Optimal batch size (0 if not enough examples yet)
        """
        # Get or create artifact stats
        if artifact_type not in self.artifact_stats:
            self.artifact_stats[artifact_type] = ArtifactStats(artifact_type=artifact_type)
        
        stats = self.artifact_stats[artifact_type]
        
        # Not enough examples yet
        if available_examples < self.min_batch_size:
            return 0
        
        # 1. BASE SIZE FROM AVAILABILITY
        # More examples = can use larger batches
        if available_examples < 30:
            base_size = self.min_batch_size
        elif available_examples < 50:
            base_size = 30
        elif available_examples < 100:
            base_size = 50
        elif available_examples < 200:
            base_size = 75
        else:
            base_size = self.max_batch_size
        
        # 2. QUALITY ADJUSTMENT
        # High quality = can train with fewer examples
        # Low quality = need more examples for stability
        if avg_quality >= 0.8:
            # Very high quality - small batches ok
            quality_multiplier = 0.7
        elif avg_quality >= self.target_quality:
            # Good quality - standard batches
            quality_multiplier = 1.0
        else:
            # Low quality - need more examples
            quality_multiplier = 1.3
        
        # 3. RARITY ADJUSTMENT
        # Rare artifacts (< 100 total examples seen) train sooner with smaller batches
        if stats.total_examples < 50:
            # Very rare - train ASAP with small batches
            rarity_multiplier = 0.5
        elif stats.total_examples < 100:
            # Somewhat rare - smaller batches
            rarity_multiplier = 0.7
        else:
            # Common - standard batches
            rarity_multiplier = 1.0
        
        # 4. TREND ADJUSTMENT
        # If quality improving = increase batch size
        # If quality declining = decrease batch size
        trend_multiplier = self._calculate_trend_multiplier(stats)
        
        # COMBINE ALL FACTORS
        optimal_size = int(
            base_size *
            quality_multiplier *
            rarity_multiplier *
            trend_multiplier
        )
        
        # Clamp to [min, max]
        optimal_size = max(self.min_batch_size, min(self.max_batch_size, optimal_size))
        
        # Update stats
        stats.last_batch_size = optimal_size
        
        return optimal_size
    
    def _calculate_trend_multiplier(self, stats: ArtifactStats) -> float:
        """
        Calculate multiplier based on quality trend.
        
        Improving quality → increase batches (model converging)
        Declining quality → decrease batches (need more frequent updates)
        """
        if len(stats.quality_trend) < 3:
            # Not enough data to determine trend
            return 1.0
        
        # Calculate trend (linear regression slope)
        # Positive slope = improving, negative = declining
        n = len(stats.quality_trend)
        x = list(range(n))
        y = stats.quality_trend
        
        # Simple slope calculation
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 1.0
        
        slope = numerator / denominator
        
        # Interpret slope
        if slope > 0.05:
            # Strongly improving - can increase batch size
            return 1.2
        elif slope > 0.01:
            # Slightly improving - slightly increase
            return 1.1
        elif slope < -0.05:
            # Strongly declining - decrease batch size
            return 0.8
        elif slope < -0.01:
            # Slightly declining - slightly decrease
            return 0.9
        else:
            # Stable - no change
            return 1.0
    
    def record_batch_creation(
        self,
        artifact_type: str,
        batch_size: int,
        avg_quality: float,
        timestamp: float
    ):
        """
        Record that a batch was created for an artifact.
        
        Args:
            artifact_type: Type of artifact
            batch_size: Size of batch created
            avg_quality: Average quality (reward) of examples in batch
            timestamp: Timestamp of batch creation
        """
        if artifact_type not in self.artifact_stats:
            self.artifact_stats[artifact_type] = ArtifactStats(artifact_type=artifact_type)
        
        stats = self.artifact_stats[artifact_type]
        stats.total_examples += batch_size
        stats.batches_created += 1
        stats.last_batch_size = batch_size
        stats.last_batch_timestamp = timestamp
        stats.update_quality(avg_quality)
        
        # Save statistics
        self._save_statistics()
    
    def get_artifact_stats(self, artifact_type: str) -> Optional[ArtifactStats]:
        """Get statistics for an artifact type"""
        return self.artifact_stats.get(artifact_type)
    
    def get_all_stats(self) -> Dict[str, ArtifactStats]:
        """Get statistics for all artifact types"""
        return self.artifact_stats.copy()
    
    def get_summary(self) -> Dict[str, any]:
        """Get summary statistics"""
        total_examples = sum(s.total_examples for s in self.artifact_stats.values())
        total_batches = sum(s.batches_created for s in self.artifact_stats.values())
        
        # Most/least trained artifacts
        if self.artifact_stats:
            most_trained = max(self.artifact_stats.values(), key=lambda s: s.total_examples)
            least_trained = min(self.artifact_stats.values(), key=lambda s: s.total_examples)
        else:
            most_trained = None
            least_trained = None
        
        return {
            'total_examples': total_examples,
            'total_batches': total_batches,
            'unique_artifacts': len(self.artifact_stats),
            'most_trained': {
                'artifact_type': most_trained.artifact_type,
                'total_examples': most_trained.total_examples,
                'batches_created': most_trained.batches_created
            } if most_trained else None,
            'least_trained': {
                'artifact_type': least_trained.artifact_type,
                'total_examples': least_trained.total_examples,
                'batches_created': least_trained.batches_created
            } if least_trained else None,
            'avg_batch_size': total_examples / total_batches if total_batches > 0 else 0
        }
    
    def _save_statistics(self):
        """Save statistics to disk"""
        try:
            data = {
                artifact_type: asdict(stats)
                for artifact_type, stats in self.artifact_stats.items()
            }
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save batch manager statistics: {e}")
    
    def _load_statistics(self):
        """Load statistics from disk"""
        if not self.stats_file.exists():
            return
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for artifact_type, stats_dict in data.items():
                self.artifact_stats[artifact_type] = ArtifactStats(**stats_dict)
            
            print(f"[BATCH_MANAGER] Loaded statistics for {len(self.artifact_stats)} artifact types")
        except Exception as e:
            print(f"[WARN] Could not load batch manager statistics: {e}")


# Example usage
if __name__ == "__main__":
    import time
    
    manager = AdaptiveBatchManager()
    
    print("="*80)
    print("ADAPTIVE BATCH MANAGER - TEST")
    print("="*80)
    
    # Simulate different scenarios
    scenarios = [
        # Scenario 1: New rare artifact (ERD)
        ("erd", 25, 0.85, "New rare artifact"),
        
        # Scenario 2: Common artifact with many examples (code)
        ("code_prototype", 150, 0.70, "Common artifact"),
        
        # Scenario 3: Low quality artifact needs more examples
        ("jira", 60, 0.45, "Low quality artifact"),
        
        # Scenario 4: Very rare, not enough examples yet
        ("workflows", 15, 0.80, "Too few examples"),
    ]
    
    for artifact_type, available, quality, description in scenarios:
        print(f"\nScenario: {description}")
        print(f"  Artifact: {artifact_type}")
        print(f"  Available: {available} examples")
        print(f"  Avg Quality: {quality:.2f}")
        
        batch_size = manager.calculate_optimal_batch_size(
            artifact_type, available, quality
        )
        
        if batch_size > 0:
            print(f"  → Optimal Batch Size: {batch_size}")
            
            # Simulate batch creation
            manager.record_batch_creation(
                artifact_type, batch_size, quality, time.time()
            )
        else:
            print(f"  → Not enough examples yet (need {manager.min_batch_size})")
    
    # Show summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    summary = manager.get_summary()
    print(json.dumps(summary, indent=2))
    
    # Show per-artifact stats
    print("\n" + "="*80)
    print("PER-ARTIFACT STATISTICS")
    print("="*80)
    for artifact_type, stats in manager.get_all_stats().items():
        print(f"\n{artifact_type}:")
        print(f"  Total Examples: {stats.total_examples}")
        print(f"  Batches Created: {stats.batches_created}")
        print(f"  Avg Quality: {stats.avg_quality:.3f}")
        print(f"  Last Batch Size: {stats.last_batch_size}")

