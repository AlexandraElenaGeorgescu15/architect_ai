"""
Preference Learner (RLHF-style Training)
Learn from pairwise preferences instead of binary good/bad feedback.

Strategy:
1. Generate multiple outputs for same input
2. Rank outputs by quality (validation scores)
3. Create preference pairs (A better than B)
4. Train with preference learning loss (e.g., DPO, PPO)

More nuanced than binary feedback - learns relative quality.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class OutputRanking:
    """Ranked outputs for a single input"""
    input_data: str
    context: Dict
    artifact_type: str
    outputs: List[str]  # Ranked from best to worst
    scores: List[float]  # Validation scores
    timestamp: float


@dataclass
class PreferencePair:
    """A single preference pair for training"""
    prompt: str
    context: str
    chosen: str  # Better output
    rejected: str  # Worse output
    margin: float  # Confidence in preference (score difference)
    artifact_type: str
    
    def to_training_example(self) -> Dict:
        """Convert to training format (DPO-style)"""
        return {
            'prompt': self.prompt,
            'context': self.context,
            'chosen': self.chosen,
            'rejected': self.rejected,
            'margin': self.margin,
            'artifact_type': self.artifact_type
        }


class PreferenceLearner:
    """
    Learn from pairwise preferences (RLHF-style).
    
    Workflow:
    1. For each input, generate N outputs (N=2-5)
    2. Validate all outputs
    3. Rank by validation score
    4. Extract pairwise preferences (best vs. rest)
    5. Train with preference learning
    
    Benefits over binary feedback:
    - More informative (learns relative quality)
    - Handles ambiguous cases (slightly better vs. much better)
    - More sample efficient
    """
    
    def __init__(
        self,
        min_margin: float = 5.0,  # Minimum score difference for preference
        max_pairs_per_ranking: int = 3,  # Max preference pairs per ranking
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize preference learner.
        
        Args:
            min_margin: Minimum score difference to create preference (e.g., 5 points)
            max_pairs_per_ranking: Maximum preference pairs per ranking
            storage_dir: Directory to store preference data
        """
        self.min_margin = min_margin
        self.max_pairs_per_ranking = max_pairs_per_ranking
        
        self.storage_dir = storage_dir or Path("training_jobs/preference_learning")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Track collected preferences
        self.preference_pairs: List[PreferencePair] = []
        
        # Load existing preferences
        self._load_preferences()
    
    def collect_preferences(
        self,
        input_data: str,
        outputs: List[str],
        scores: List[float],
        artifact_type: str,
        context: Dict
    ) -> List[PreferencePair]:
        """
        Collect preference pairs from ranked outputs.
        
        Args:
            input_data: Input prompt/request
            outputs: Generated outputs (at least 2)
            scores: Validation scores for each output
            artifact_type: Type of artifact
            context: Generation context (RAG, etc.)
        
        Returns:
            List of preference pairs created
        """
        if len(outputs) < 2:
            print("[PREFERENCE] Need at least 2 outputs to create preferences")
            return []
        
        # Sort outputs by score (best first)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ranked_outputs = [outputs[i] for i in ranked_indices]
        ranked_scores = [scores[i] for i in ranked_indices]
        
        # Create preference pairs
        preferences = []
        best_output = ranked_outputs[0]
        best_score = ranked_scores[0]
        
        # Compare best against others
        for i in range(1, len(ranked_outputs)):
            worse_output = ranked_outputs[i]
            worse_score = ranked_scores[i]
            
            # Only create preference if margin is significant
            margin = best_score - worse_score
            if margin < self.min_margin:
                continue
            
            # Create preference pair
            pair = PreferencePair(
                prompt=input_data,
                context=json.dumps(context),
                chosen=best_output,
                rejected=worse_output,
                margin=margin,
                artifact_type=artifact_type
            )
            
            preferences.append(pair)
            
            # Limit pairs per ranking
            if len(preferences) >= self.max_pairs_per_ranking:
                break
        
        # Store preferences
        self.preference_pairs.extend(preferences)
        
        if preferences:
            print(f"[PREFERENCE] Created {len(preferences)} preference pairs:")
            print(f"  Best score: {best_score:.1f}")
            print(f"  Worst score: {ranked_scores[-1]:.1f}")
            print(f"  Margins: {[p.margin for p in preferences]}")
            
            # Save to disk
            self._save_preferences()
        
        return preferences
    
    def generate_multiple_outputs(
        self,
        input_data: str,
        context: Dict,
        artifact_type: str,
        generator_fn: callable,
        n_outputs: int = 3
    ) -> Tuple[List[str], List[float]]:
        """
        Generate multiple outputs for preference collection.
        
        Args:
            input_data: Input prompt
            context: Generation context
            artifact_type: Type of artifact
            generator_fn: Function that generates output (input, context) -> output
            n_outputs: Number of outputs to generate
        
        Returns:
            Tuple of (outputs, scores)
        """
        outputs = []
        scores = []
        
        print(f"[PREFERENCE] Generating {n_outputs} outputs for preference ranking...")
        
        for i in range(n_outputs):
            try:
                # Generate output
                output = generator_fn(input_data, context)
                
                # Validate output (mock - in real usage, use actual validator)
                score = self._mock_validate(output, artifact_type)
                
                outputs.append(output)
                scores.append(score)
                
                print(f"  Output {i+1}: score {score:.1f}")
            
            except Exception as e:
                print(f"[WARN] Output {i+1} generation failed: {e}")
        
        return outputs, scores
    
    def create_training_dataset(self) -> List[Dict]:
        """
        Create training dataset from collected preferences.
        
        Returns:
            List of training examples in DPO format
        """
        return [pair.to_training_example() for pair in self.preference_pairs]
    
    def get_statistics(self) -> Dict:
        """Get preference learning statistics"""
        if not self.preference_pairs:
            return {
                'total_pairs': 0,
                'avg_margin': 0.0,
                'artifact_types': []
            }
        
        import numpy as np
        
        margins = [p.margin for p in self.preference_pairs]
        artifact_types = list(set(p.artifact_type for p in self.preference_pairs))
        
        return {
            'total_pairs': len(self.preference_pairs),
            'avg_margin': float(np.mean(margins)),
            'min_margin': float(min(margins)),
            'max_margin': float(max(margins)),
            'artifact_types': artifact_types,
            'pairs_by_artifact': {
                at: sum(1 for p in self.preference_pairs if p.artifact_type == at)
                for at in artifact_types
            }
        }
    
    def _mock_validate(self, output: str, artifact_type: str) -> float:
        """Mock validation (in real usage, use actual validator)"""
        import random
        # Mock score based on output length (longer = better, simplistic)
        base_score = min(100, 50 + len(output) / 10)
        noise = random.uniform(-10, 10)
        return max(0, min(100, base_score + noise))
    
    def _save_preferences(self):
        """Save preferences to disk"""
        filepath = self.storage_dir / "preference_pairs.jsonl"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for pair in self.preference_pairs:
                    f.write(json.dumps(pair.to_training_example()) + '\n')
            
            print(f"[PREFERENCE] Saved {len(self.preference_pairs)} preference pairs to {filepath}")
        except Exception as e:
            print(f"[WARN] Could not save preferences: {e}")
    
    def _load_preferences(self):
        """Load preferences from disk"""
        filepath = self.storage_dir / "preference_pairs.jsonl"
        
        if not filepath.exists():
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    pair = PreferencePair(
                        prompt=data['prompt'],
                        context=data['context'],
                        chosen=data['chosen'],
                        rejected=data['rejected'],
                        margin=data['margin'],
                        artifact_type=data['artifact_type']
                    )
                    self.preference_pairs.append(pair)
            
            print(f"[PREFERENCE] Loaded {len(self.preference_pairs)} preference pairs")
        except Exception as e:
            print(f"[WARN] Could not load preferences: {e}")


# Example usage
if __name__ == "__main__":
    import time
    import random
    
    learner = PreferenceLearner()
    
    print("="*80)
    print("PREFERENCE LEARNER - TEST")
    print("="*80)
    
    # Simulate generating multiple outputs
    input_data = "Generate ERD for e-commerce system with users, products, orders"
    context = {"rag": "existing code snippets...", "notes": "user requirements..."}
    artifact_type = "erd"
    
    # Simulate 3 outputs with different quality
    outputs = [
        "erDiagram\nUser {int id PK, string email, string name}\nProduct {int id PK, string name, decimal price}\nOrder {int id PK, int user_id FK}\nUser ||--o{ Order : places\nOrder ||--o{ Product : contains",
        "erDiagram\nUser {int id PK, string email}\nProduct {int id PK, string name}\nOrder {int id PK}",
        "erDiagram\nUSER\nPRODUCT\nORDER"
    ]
    
    scores = [85.0, 65.0, 40.0]  # Quality decreases
    
    print(f"\nInput: {input_data}")
    print(f"\nGenerated {len(outputs)} outputs with scores: {scores}")
    
    # Collect preferences
    print("\n" + "-" * 40)
    print("COLLECTING PREFERENCES")
    print("-" * 40)
    
    preferences = learner.collect_preferences(
        input_data=input_data,
        outputs=outputs,
        scores=scores,
        artifact_type=artifact_type,
        context=context
    )
    
    # Show collected preferences
    print("\n" + "-" * 40)
    print(f"COLLECTED {len(preferences)} PREFERENCE PAIRS")
    print("-" * 40)
    
    for i, pref in enumerate(preferences, 1):
        print(f"\nPair {i}:")
        print(f"  Margin: {pref.margin:.1f} points")
        print(f"  Chosen (truncated): {pref.chosen[:80]}...")
        print(f"  Rejected (truncated): {pref.rejected[:80]}...")
    
    # Show statistics
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    stats = learner.get_statistics()
    print(json.dumps(stats, indent=2))
    
    # Show training dataset format
    print("\n" + "="*80)
    print("TRAINING DATASET FORMAT (DPO)")
    print("="*80)
    dataset = learner.create_training_dataset()
    print(f"Total examples: {len(dataset)}")
    if dataset:
        print("\nExample training entry:")
        print(json.dumps(dataset[0], indent=2)[:500] + "...")

