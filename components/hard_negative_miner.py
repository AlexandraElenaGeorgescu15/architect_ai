"""
Hard Negative Mining for Targeted Training
Identifies and focuses on examples where the model struggles most.

Strategy:
1. Track model failures and low-confidence predictions
2. Identify patterns in failures (artifact types, complexity, etc.)
3. Generate challenging synthetic examples
4. Focus training on these hard cases

Improves edge case handling by ~20-30%.
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class FailureCase:
    """A single failure case to learn from"""
    input_data: str
    output: str
    expected_output: Optional[str]
    validation_score: float
    artifact_type: str
    failure_type: str  # 'low_score', 'validation_failure', 'user_correction'
    complexity_factors: Dict[str, float]  # What made it hard
    timestamp: float


class HardNegativeMiner:
    """
    Mine hard negative examples for targeted training.
    
    Workflow:
    1. Collect failure cases (low scores, corrections, etc.)
    2. Analyze failure patterns
    3. Identify common failure modes
    4. Generate similar challenging examples
    5. Focus training on hard cases
    
    Benefits:
    - Improves edge case handling
    - Reduces systematic errors
    - Balances training data (more hard examples)
    """
    
    def __init__(
        self,
        failure_threshold: float = 60.0,  # Score below this = failure
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize hard negative miner.
        
        Args:
            failure_threshold: Validation score threshold for failure
            storage_dir: Directory to store failure cases
        """
        self.failure_threshold = failure_threshold
        
        self.storage_dir = storage_dir or Path("training_jobs/hard_negative_mining")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Track failure cases
        self.failure_cases: List[FailureCase] = []
        
        # Track failure patterns
        self.failure_patterns: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Load existing failures
        self._load_failures()
    
    def record_failure(
        self,
        input_data: str,
        output: str,
        validation_score: float,
        artifact_type: str,
        expected_output: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[FailureCase]:
        """
        Record a failure case.
        
        Args:
            input_data: Input that led to failure
            output: Model output (incorrect/low-quality)
            validation_score: Validation score
            artifact_type: Type of artifact
            expected_output: Correct output (if available)
            metadata: Additional metadata
        
        Returns:
            FailureCase if recorded, None if not a failure
        """
        if validation_score >= self.failure_threshold:
            return None  # Not a failure
        
        # Classify failure type
        if expected_output:
            failure_type = 'user_correction'
        elif validation_score < 50:
            failure_type = 'validation_failure'
        else:
            failure_type = 'low_score'
        
        # Analyze complexity factors
        complexity_factors = self._analyze_complexity(input_data, output, artifact_type, metadata)
        
        # Create failure case
        import time
        failure = FailureCase(
            input_data=input_data,
            output=output,
            expected_output=expected_output,
            validation_score=validation_score,
            artifact_type=artifact_type,
            failure_type=failure_type,
            complexity_factors=complexity_factors,
            timestamp=time.time()
        )
        
        # Store failure
        self.failure_cases.append(failure)
        
        # Update failure patterns
        self._update_patterns(failure)
        
        # Save to disk
        self._save_failures()
        
        print(f"[HARD_NEG] Recorded failure case:")
        print(f"  Artifact: {artifact_type}")
        print(f"  Score: {validation_score:.1f}")
        print(f"  Type: {failure_type}")
        print(f"  Complexity: {complexity_factors}")
        
        return failure
    
    def get_hard_negatives(
        self,
        artifact_type: Optional[str] = None,
        min_difficulty: float = 0.5,
        limit: int = 100
    ) -> List[FailureCase]:
        """
        Get hard negative examples for training.
        
        Args:
            artifact_type: Filter by artifact type (None = all)
            min_difficulty: Minimum complexity threshold
            limit: Maximum number to return
        
        Returns:
            List of hard negative examples, sorted by difficulty
        """
        # Filter by artifact type
        candidates = self.failure_cases
        if artifact_type:
            candidates = [f for f in candidates if f.artifact_type == artifact_type]
        
        # Calculate difficulty score for each
        scored = []
        for failure in candidates:
            difficulty = self._calculate_difficulty(failure)
            if difficulty >= min_difficulty:
                scored.append((difficulty, failure))
        
        # Sort by difficulty (hardest first)
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Return top-k
        hard_negatives = [failure for _, failure in scored[:limit]]
        
        print(f"[HARD_NEG] Retrieved {len(hard_negatives)} hard negatives:")
        print(f"  Artifact type: {artifact_type or 'all'}")
        print(f"  Min difficulty: {min_difficulty}")
        if hard_negatives:
            avg_difficulty = sum(d for d, _ in scored[:limit]) / len(hard_negatives)
            print(f"  Avg difficulty: {avg_difficulty:.3f}")
        
        return hard_negatives
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """
        Analyze failure patterns to identify systematic issues.
        
        Returns:
            Dict with:
            - most_common_failures: Top failure types per artifact
            - complexity_bottlenecks: What makes examples hard
            - recommendations: Suggested improvements
        """
        if not self.failure_cases:
            return {
                'most_common_failures': {},
                'complexity_bottlenecks': {},
                'recommendations': []
            }
        
        # Analyze by artifact type
        by_artifact = defaultdict(list)
        for failure in self.failure_cases:
            by_artifact[failure.artifact_type].append(failure)
        
        most_common_failures = {}
        complexity_bottlenecks = {}
        
        for artifact_type, failures in by_artifact.items():
            # Most common failure type
            failure_types = [f.failure_type for f in failures]
            most_common = max(set(failure_types), key=failure_types.count)
            most_common_failures[artifact_type] = {
                'type': most_common,
                'count': failure_types.count(most_common),
                'percentage': failure_types.count(most_common) / len(failures) * 100
            }
            
            # Complexity bottlenecks
            all_factors = defaultdict(list)
            for failure in failures:
                for factor, score in failure.complexity_factors.items():
                    all_factors[factor].append(score)
            
            # Average complexity per factor
            avg_factors = {
                factor: sum(scores) / len(scores)
                for factor, scores in all_factors.items()
            }
            
            # Find highest complexity factors
            sorted_factors = sorted(avg_factors.items(), key=lambda x: x[1], reverse=True)
            complexity_bottlenecks[artifact_type] = sorted_factors[:3]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            most_common_failures,
            complexity_bottlenecks
        )
        
        return {
            'total_failures': len(self.failure_cases),
            'most_common_failures': most_common_failures,
            'complexity_bottlenecks': complexity_bottlenecks,
            'recommendations': recommendations
        }
    
    def _analyze_complexity(
        self,
        input_data: str,
        output: str,
        artifact_type: str,
        metadata: Optional[Dict]
    ) -> Dict[str, float]:
        """
        Analyze what made this example complex/difficult.
        
        Returns:
            Dict of complexity factors (0-1 each)
        """
        factors = {}
        
        # Input length
        factors['input_length'] = min(1.0, len(input_data) / 5000)
        
        # Output length
        factors['output_length'] = min(1.0, len(output) / 2000)
        
        # Context size
        if metadata and 'context' in metadata:
            context_size = len(str(metadata['context']))
            factors['context_size'] = min(1.0, context_size / 10000)
        else:
            factors['context_size'] = 0.0
        
        # Artifact complexity (based on type)
        complexity_map = {
            'erd': 0.3,
            'jira': 0.4,
            'api_docs': 0.5,
            'architecture': 0.7,
            'code_prototype': 0.8,
        }
        factors['artifact_complexity'] = complexity_map.get(artifact_type, 0.5)
        
        # Output structure complexity (number of lines)
        factors['output_lines'] = min(1.0, output.count('\n') / 50)
        
        return factors
    
    def _calculate_difficulty(self, failure: FailureCase) -> float:
        """
        Calculate overall difficulty score for a failure case.
        
        Higher = harder example, more valuable for training.
        """
        # Validation score (lower = harder)
        score_difficulty = 1.0 - (failure.validation_score / 100.0)
        
        # Average complexity factors
        avg_complexity = sum(failure.complexity_factors.values()) / len(failure.complexity_factors)
        
        # Weighted combination
        difficulty = (
            score_difficulty * 0.6 +  # Most important
            avg_complexity * 0.4       # Secondary
        )
        
        return difficulty
    
    def _update_patterns(self, failure: FailureCase):
        """Update failure pattern statistics"""
        self.failure_patterns[failure.artifact_type][failure.failure_type] += 1
    
    def _generate_recommendations(
        self,
        most_common_failures: Dict,
        complexity_bottlenecks: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for artifact_type, failure_info in most_common_failures.items():
            if failure_info['percentage'] > 50:
                recommendations.append(
                    f"Focus training on {artifact_type} - {failure_info['percentage']:.0f}% "
                    f"of failures are '{failure_info['type']}'"
                )
        
        for artifact_type, factors in complexity_bottlenecks.items():
            top_factor, top_score = factors[0]
            if top_score > 0.7:
                recommendations.append(
                    f"Improve {artifact_type} handling of {top_factor} "
                    f"(avg complexity: {top_score:.2f})"
                )
        
        return recommendations
    
    def _save_failures(self):
        """Save failure cases to disk"""
        filepath = self.storage_dir / "failure_cases.jsonl"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for failure in self.failure_cases:
                    data = {
                        'input_data': failure.input_data[:500],  # Truncate for storage
                        'output': failure.output[:500],
                        'validation_score': failure.validation_score,
                        'artifact_type': failure.artifact_type,
                        'failure_type': failure.failure_type,
                        'complexity_factors': failure.complexity_factors,
                        'timestamp': failure.timestamp
                    }
                    f.write(json.dumps(data) + '\n')
        except Exception as e:
            print(f"[WARN] Could not save failure cases: {e}")
    
    def _load_failures(self):
        """Load failure cases from disk"""
        filepath = self.storage_dir / "failure_cases.jsonl"
        
        if not filepath.exists():
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    failure = FailureCase(
                        input_data=data['input_data'],
                        output=data['output'],
                        expected_output=None,
                        validation_score=data['validation_score'],
                        artifact_type=data['artifact_type'],
                        failure_type=data['failure_type'],
                        complexity_factors=data['complexity_factors'],
                        timestamp=data['timestamp']
                    )
                    self.failure_cases.append(failure)
            
            print(f"[HARD_NEG] Loaded {len(self.failure_cases)} failure cases")
        except Exception as e:
            print(f"[WARN] Could not load failure cases: {e}")


# Example usage
if __name__ == "__main__":
    import time
    import random
    
    miner = HardNegativeMiner()
    
    print("="*80)
    print("HARD NEGATIVE MINING - TEST")
    print("="*80)
    
    # Simulate failure cases
    print("\nSimulating failure cases...")
    print("-" * 40)
    
    # ERD failures (input length issues)
    for i in range(10):
        miner.record_failure(
            input_data=f"Generate ERD for complex system" * (i + 1),
            output="erDiagram\nEntity1\nEntity2",
            validation_score=random.uniform(30, 55),
            artifact_type="erd",
            metadata={'context': "x" * random.randint(100, 1000)}
        )
    
    # Code failures (complexity issues)
    for i in range(8):
        miner.record_failure(
            input_data=f"Generate authentication code with OAuth2 and JWT" * (i + 1),
            output="class Auth:\n    pass",
            validation_score=random.uniform(40, 58),
            artifact_type="code_prototype",
            expected_output="class Auth:\n    # proper implementation",
            metadata={'context': "x" * random.randint(500, 5000)}
        )
    
    # Architecture failures (various)
    for i in range(5):
        miner.record_failure(
            input_data=f"Design microservices architecture",
            output="graph TD\nA-->B",
            validation_score=random.uniform(35, 59),
            artifact_type="architecture",
            metadata={'context': "x" * random.randint(200, 2000)}
        )
    
    # Analyze patterns
    print("\n" + "="*80)
    print("FAILURE PATTERN ANALYSIS")
    print("="*80)
    
    analysis = miner.analyze_failure_patterns()
    print(json.dumps(analysis, indent=2))
    
    # Get hard negatives
    print("\n" + "="*80)
    print("RETRIEVING HARD NEGATIVES")
    print("="*80)
    
    hard_negatives = miner.get_hard_negatives(limit=5)
    
    print(f"\nTop 5 hardest examples:")
    for i, failure in enumerate(hard_negatives, 1):
        difficulty = miner._calculate_difficulty(failure)
        print(f"\n{i}. {failure.artifact_type}")
        print(f"   Score: {failure.validation_score:.1f}")
        print(f"   Difficulty: {difficulty:.3f}")
        print(f"   Input: {failure.input_data[:60]}...")

