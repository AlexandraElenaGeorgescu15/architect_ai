"""
Cross-Encoder Reranking for Better Relevance
Uses cross-encoder models to rerank search results
"""

from typing import List, Dict, Any
import numpy as np

class CrossEncoderReranker:
    """Rerank search results using cross-encoder"""
    
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.model = None
        self.model_name = model_name
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize cross-encoder model"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            print(f"[OK] Loaded cross-encoder: {self.model_name}")
        except ImportError:
            print("[WARN] sentence-transformers not available for reranking")
            self.model = None
        except Exception as e:
            print(f"[WARN] Could not load cross-encoder: {e}")
            self.model = None
    
    def rerank(self, query: str, candidates: List[Dict[str, Any]], 
               top_k: int = 18, score_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder
        
        Args:
            query: Search query
            candidates: List of candidate documents with 'content' and 'score'
            top_k: Number of top results to return
            score_weight: Weight for reranking score (vs original score)
        
        Returns:
            Reranked list of candidates
        """
        if not self.model or not candidates:
            return candidates[:top_k]
        
        try:
            # Prepare pairs for cross-encoder
            pairs = [[query, c.get('content', '')] for c in candidates]
            
            # Get reranking scores
            rerank_scores = self.model.predict(pairs)
            
            # Normalize scores to 0-1 range
            rerank_scores = self._normalize_scores(rerank_scores)
            
            # Combine with original scores
            for i, candidate in enumerate(candidates):
                original_score = candidate.get('score', 0.5)
                rerank_score = rerank_scores[i]
                
                # Weighted combination
                final_score = (
                    (1 - score_weight) * original_score +
                    score_weight * rerank_score
                )
                
                candidate['original_score'] = original_score
                candidate['rerank_score'] = float(rerank_score)
                candidate['final_score'] = float(final_score)
            
            # Sort by final score
            reranked = sorted(candidates, key=lambda x: x['final_score'], reverse=True)
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"[WARN] Reranking failed: {e}")
            return candidates[:top_k]
    
    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize scores to 0-1 range"""
        scores = np.array(scores)
        min_score = scores.min()
        max_score = scores.max()
        
        if max_score - min_score > 0:
            normalized = (scores - min_score) / (max_score - min_score)
        else:
            normalized = np.ones_like(scores) * 0.5
        
        return normalized
    
    def batch_rerank(self, queries: List[str], candidates_list: List[List[Dict[str, Any]]], 
                     top_k: int = 18) -> List[List[Dict[str, Any]]]:
        """Rerank multiple queries in batch"""
        results = []
        
        for query, candidates in zip(queries, candidates_list):
            reranked = self.rerank(query, candidates, top_k)
            results.append(reranked)
        
        return results


class DiversityReranker:
    """Rerank results to maximize diversity"""
    
    def rerank_for_diversity(self, candidates: List[Dict[str, Any]], 
                            top_k: int = 18, diversity_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Rerank to maximize diversity while maintaining relevance
        
        Args:
            candidates: List of candidates with scores
            top_k: Number of results to return
            diversity_weight: Weight for diversity (vs relevance)
        
        Returns:
            Diversified list of candidates
        """
        if len(candidates) <= top_k:
            return candidates
        
        selected = []
        remaining = candidates.copy()
        
        # Always select the top result first
        selected.append(remaining.pop(0))
        
        # Iteratively select most diverse + relevant
        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = -1
            
            for i, candidate in enumerate(remaining):
                # Relevance score
                relevance = candidate.get('final_score', candidate.get('score', 0))
                
                # Diversity score (how different from already selected)
                diversity = self._calculate_diversity(candidate, selected)
                
                # Combined score
                combined = (
                    (1 - diversity_weight) * relevance +
                    diversity_weight * diversity
                )
                
                if combined > best_score:
                    best_score = combined
                    best_idx = i
            
            selected.append(remaining.pop(best_idx))
        
        return selected
    
    def _calculate_diversity(self, candidate: Dict[str, Any], 
                           selected: List[Dict[str, Any]]) -> float:
        """Calculate how diverse a candidate is from selected items"""
        if not selected:
            return 1.0
        
        # Simple diversity based on file path and content length
        candidate_path = candidate.get('meta', {}).get('path', '')
        candidate_len = len(candidate.get('content', ''))
        
        diversities = []
        for sel in selected:
            sel_path = sel.get('meta', {}).get('path', '')
            sel_len = len(sel.get('content', ''))
            
            # Path diversity (different files are more diverse)
            path_div = 0.0 if candidate_path == sel_path else 1.0
            
            # Length diversity (different sizes are more diverse)
            len_diff = abs(candidate_len - sel_len) / max(candidate_len, sel_len, 1)
            
            diversity = (path_div + len_diff) / 2
            diversities.append(diversity)
        
        # Return average diversity
        return sum(diversities) / len(diversities)


# Global rerankers
_cross_encoder_reranker = None
_diversity_reranker = None

def get_cross_encoder_reranker() -> CrossEncoderReranker:
    """Get or create global cross-encoder reranker"""
    global _cross_encoder_reranker
    if _cross_encoder_reranker is None:
        _cross_encoder_reranker = CrossEncoderReranker()
    return _cross_encoder_reranker

def get_diversity_reranker() -> DiversityReranker:
    """Get or create global diversity reranker"""
    global _diversity_reranker
    if _diversity_reranker is None:
        _diversity_reranker = DiversityReranker()
    return _diversity_reranker

def get_reranker(strategy: str = "hybrid"):
    """
    Get reranker based on strategy
    
    Args:
        strategy: Reranking strategy ('cross_encoder', 'diversity', 'hybrid')
    
    Returns:
        Appropriate reranker instance
    """
    if strategy == "cross_encoder":
        return get_cross_encoder_reranker()
    elif strategy == "diversity":
        return get_diversity_reranker()
    else:  # hybrid or default
        # For hybrid, return cross-encoder (it has hybrid mode built-in)
        return get_cross_encoder_reranker()

