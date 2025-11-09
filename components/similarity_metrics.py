"""
Advanced Similarity Metrics for Text Comparison
Implements multiple similarity metrics for robust comparison:
1. Edit Distance (Levenshtein) - structural similarity
2. BLEU Score - n-gram overlap (good for code/diagrams)
3. Embedding Similarity - semantic similarity
4. Combined Score - weighted average
"""

from typing import Dict, Tuple, Optional
import numpy as np


class SimilarityCalculator:
    """
    Calculate similarity between two texts using multiple metrics.
    """
    
    def __init__(self, use_embeddings: bool = True):
        """
        Initialize similarity calculator.
        
        Args:
            use_embeddings: Whether to use embedding-based similarity (requires sentence-transformers)
        """
        self.use_embeddings = use_embeddings
        self._embedding_model = None
        
        if use_embeddings:
            self._initialize_embedding_model()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model for embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            # Use lightweight model (all-MiniLM-L6-v2 is 80MB, fast)
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[SIMILARITY] Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            print("[WARN] sentence-transformers not available. Install with: pip install sentence-transformers")
            self.use_embeddings = False
        except Exception as e:
            print(f"[WARN] Could not load embedding model: {e}")
            self.use_embeddings = False
    
    def calculate_all(
        self,
        text1: str,
        text2: str,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate all similarity metrics.
        
        Args:
            text1: First text
            text2: Second text
            weights: Optional weights for combined score
                     Default: {'edit_distance': 0.4, 'bleu': 0.3, 'embedding': 0.3}
        
        Returns:
            Dict with keys:
            - 'edit_distance': 0-1 (Levenshtein normalized)
            - 'bleu': 0-1 (BLEU score)
            - 'embedding': 0-1 (cosine similarity of embeddings)
            - 'combined': 0-1 (weighted average)
        """
        if not text1 or not text2:
            return {
                'edit_distance': 0.0,
                'bleu': 0.0,
                'embedding': 0.0,
                'combined': 0.0
            }
        
        # Default weights
        if weights is None:
            weights = {
                'edit_distance': 0.4,  # Structural similarity
                'bleu': 0.3,            # N-gram overlap
                'embedding': 0.3        # Semantic similarity
            }
        
        # Calculate individual metrics
        edit_sim = self.calculate_edit_distance_similarity(text1, text2)
        bleu_score = self.calculate_bleu_score(text1, text2)
        embedding_sim = self.calculate_embedding_similarity(text1, text2) if self.use_embeddings else edit_sim
        
        # Combined score (weighted average)
        combined = (
            edit_sim * weights['edit_distance'] +
            bleu_score * weights['bleu'] +
            embedding_sim * weights['embedding']
        )
        
        return {
            'edit_distance': edit_sim,
            'bleu': bleu_score,
            'embedding': embedding_sim,
            'combined': combined
        }
    
    def calculate_edit_distance_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate normalized edit distance (Levenshtein) similarity.
        
        This measures structural similarity - how many character edits needed
        to transform text1 into text2.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            float: Similarity 0-1 (0=completely different, 1=identical)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0
        
        try:
            import Levenshtein
            max_len = max(len(text1), len(text2))
            edit_dist = Levenshtein.distance(text1, text2)
            similarity = 1.0 - (edit_dist / max_len)
            return max(0.0, similarity)
        except ImportError:
            print("[WARN] python-Levenshtein not available. Using character-level similarity.")
            return self._fallback_character_similarity(text1, text2)
    
    def calculate_bleu_score(self, reference: str, candidate: str, n: int = 4) -> float:
        """
        Calculate BLEU score (n-gram overlap).
        
        Good for code and structured text (diagrams) where word order matters.
        
        Args:
            reference: Reference text (ground truth)
            candidate: Candidate text (generated)
            n: Maximum n-gram length (default: 4)
        
        Returns:
            float: BLEU score 0-1 (0=no overlap, 1=perfect match)
        """
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            
            # Tokenize (split by whitespace)
            ref_tokens = reference.split()
            cand_tokens = candidate.split()
            
            if not ref_tokens or not cand_tokens:
                return 0.0
            
            # Calculate BLEU with smoothing (handles 0-count n-grams)
            smoothing = SmoothingFunction().method1
            
            # Use up to n-grams (1-gram, 2-gram, ..., n-gram)
            weights = tuple([1.0/n] * n)
            
            score = sentence_bleu(
                [ref_tokens],
                cand_tokens,
                weights=weights,
                smoothing_function=smoothing
            )
            
            return max(0.0, min(1.0, score))
        
        except ImportError:
            print("[WARN] nltk not available. Using token overlap similarity.")
            return self._fallback_token_similarity(reference, candidate)
    
    def calculate_embedding_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity using sentence embeddings.
        
        Captures meaning similarity even if words are different
        (e.g., "big" vs "large").
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            float: Cosine similarity 0-1 (0=unrelated, 1=identical meaning)
        """
        if not self._embedding_model:
            return 0.0
        
        try:
            # Encode texts to embeddings
            emb1 = self._embedding_model.encode(text1, convert_to_numpy=True)
            emb2 = self._embedding_model.encode(text2, convert_to_numpy=True)
            
            # Calculate cosine similarity
            # cos_sim = (A · B) / (||A|| * ||B||)
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            cosine_sim = dot_product / (norm1 * norm2)
            
            # Convert from [-1, 1] to [0, 1]
            similarity = (cosine_sim + 1.0) / 2.0
            
            return max(0.0, min(1.0, similarity))
        
        except Exception as e:
            print(f"[WARN] Embedding similarity failed: {e}")
            return 0.0
    
    def _fallback_character_similarity(self, text1: str, text2: str) -> float:
        """
        Fallback: Character-level set similarity.
        Used when python-Levenshtein not available.
        """
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        intersection = set1 & set2
        union = set1 | set2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _fallback_token_similarity(self, text1: str, text2: str) -> float:
        """
        Fallback: Token-level set similarity.
        Used when nltk not available.
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0
    
    def compare_with_details(self, text1: str, text2: str) -> Dict[str, any]:
        """
        Compare texts and return detailed breakdown.
        
        Returns:
            Dict with:
            - similarities: All similarity scores
            - length_diff: Absolute difference in length
            - length_ratio: Ratio of lengths (shorter/longer)
            - recommendation: Interpretation of similarity
        """
        similarities = self.calculate_all(text1, text2)
        
        len1 = len(text1)
        len2 = len(text2)
        length_diff = abs(len1 - len2)
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 1.0
        
        # Interpret similarity
        combined = similarities['combined']
        if combined > 0.9:
            recommendation = "Nearly identical (minor typos or formatting)"
        elif combined > 0.7:
            recommendation = "Highly similar (minor corrections)"
        elif combined > 0.5:
            recommendation = "Moderately similar (significant changes)"
        elif combined > 0.3:
            recommendation = "Somewhat similar (major rewrite)"
        else:
            recommendation = "Very different (complete rewrite)"
        
        return {
            'similarities': similarities,
            'length_diff': length_diff,
            'length_ratio': length_ratio,
            'recommendation': recommendation
        }


# Global instance (lazy initialization)
_similarity_calculator = None

def get_similarity_calculator() -> SimilarityCalculator:
    """Get global similarity calculator (singleton)"""
    global _similarity_calculator
    if _similarity_calculator is None:
        _similarity_calculator = SimilarityCalculator()
    return _similarity_calculator


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Convenience function to calculate combined similarity.
    
    Args:
        text1: First text
        text2: Second text
    
    Returns:
        float: Combined similarity 0-1
    """
    calculator = get_similarity_calculator()
    return calculator.calculate_all(text1, text2)['combined']


# Example usage
if __name__ == "__main__":
    import json
    
    # Test cases
    test_cases = [
        # Case 1: Nearly identical (minor typo)
        ("Hello World", "Hello Wold"),
        
        # Case 2: Same meaning, different words
        ("The quick brown fox", "A fast brown fox"),
        
        # Case 3: Completely different
        ("Generate ERD diagram", "class UserModel: pass"),
        
        # Case 4: Code with small change
        ("def calculate(x): return x * 2", "def calculate(x): return x * 3"),
        
        # Case 5: Mermaid diagram (word order matters)
        ("graph TD\nA-->B\nB-->C", "graph TD\nC-->B\nB-->A"),
    ]
    
    calculator = SimilarityCalculator()
    
    print("="*80)
    print("ADVANCED SIMILARITY METRICS - TEST")
    print("="*80)
    
    for i, (text1, text2) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Text 1: {text1[:50]}...")
        print(f"  Text 2: {text2[:50]}...")
        
        results = calculator.compare_with_details(text1, text2)
        print(f"\n  Similarities:")
        for metric, score in results['similarities'].items():
            print(f"    {metric:15s}: {score:.3f}")
        
        print(f"\n  Length Diff: {results['length_diff']} chars")
        print(f"  Length Ratio: {results['length_ratio']:.3f}")
        print(f"  → {results['recommendation']}")
    
    print("\n" + "="*80)

