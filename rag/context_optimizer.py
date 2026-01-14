"""
Context Window Optimizer
Intelligently fits RAG context into LLM token limits
"""

import tiktoken
from typing import List, Dict, Any, Tuple

class ContextOptimizer:
    """Optimize context to fit within token limits"""
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initialize context optimizer
        
        Args:
            model_name: Model name for token counting
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base (GPT-4, GPT-3.5-turbo) for unknown models
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def optimize_context(
        self,
        retrieved_chunks: List[Tuple[Dict[str, Any], float]],
        max_tokens: int = 8000,
        preserve_top_n: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Optimize context to fit within token limit
        
        Strategy:
        1. Always preserve top N chunks (highest relevance)
        2. For remaining chunks, prioritize by:
           - Relevance score
           - Importance score (from metadata)
           - Diversity (avoid redundant information)
        3. Truncate chunks if needed to fit more variety
        
        Args:
            retrieved_chunks: List of (chunk_dict, score) tuples
            max_tokens: Maximum token budget
            preserve_top_n: Number of top chunks to always include
        
        Returns:
            Optimized list of chunks within token budget
        """
        if not retrieved_chunks:
            return []
        
        # Separate preserved and candidate chunks
        preserved = retrieved_chunks[:preserve_top_n]
        candidates = retrieved_chunks[preserve_top_n:]
        
        # Calculate tokens for preserved chunks
        preserved_tokens = sum(
            self.count_tokens(chunk["content"]) 
            for chunk, _ in preserved
        )
        
        if preserved_tokens >= max_tokens:
            # Need to truncate even preserved chunks
            return self._truncate_chunks(preserved, max_tokens)
        
        # Remaining budget for candidates
        remaining_budget = max_tokens - preserved_tokens
        
        # Score candidates by combined metric
        scored_candidates = []
        for chunk, relevance_score in candidates:
            importance = chunk["meta"].get("importance_score", 0.5)
            combined_score = 0.7 * relevance_score + 0.3 * importance
            scored_candidates.append((chunk, relevance_score, combined_score))
        
        # Sort by combined score
        scored_candidates.sort(key=lambda x: x[2], reverse=True)
        
        # Greedily add candidates with diversity check
        selected = list(preserved)
        selected_paths = {chunk["meta"].get("path") for chunk, _ in preserved}
        used_tokens = preserved_tokens
        
        for chunk, relevance_score, _ in scored_candidates:
            chunk_tokens = self.count_tokens(chunk["content"])
            chunk_path = chunk["meta"].get("path")
            
            # Check if adding this chunk would exceed budget
            if used_tokens + chunk_tokens > remaining_budget:
                # Try truncating the chunk
                truncated = self._truncate_single_chunk(
                    chunk, 
                    remaining_budget - used_tokens
                )
                if truncated:
                    selected.append((truncated, relevance_score))
                    used_tokens += self.count_tokens(truncated["content"])
                break
            
            # Diversity bonus: prefer chunks from different files
            if chunk_path not in selected_paths:
                selected.append((chunk, relevance_score))
                selected_paths.add(chunk_path)
                used_tokens += chunk_tokens
            elif len(selected) < len(retrieved_chunks) // 2:
                # Still add if we haven't selected many chunks yet
                selected.append((chunk, relevance_score))
                used_tokens += chunk_tokens
        
        return selected
    
    def _truncate_chunks(
        self,
        chunks: List[Tuple[Dict[str, Any], float]],
        max_tokens: int
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Truncate chunks to fit within token budget"""
        result = []
        used_tokens = 0
        tokens_per_chunk = max_tokens // len(chunks)
        
        for chunk, score in chunks:
            chunk_tokens = self.count_tokens(chunk["content"])
            
            if used_tokens + chunk_tokens <= max_tokens:
                result.append((chunk, score))
                used_tokens += chunk_tokens
            else:
                # Truncate this chunk
                remaining = max_tokens - used_tokens
                if remaining > 100:  # Only include if meaningful
                    truncated = self._truncate_single_chunk(chunk, remaining)
                    if truncated:
                        result.append((truncated, score))
                        used_tokens += self.count_tokens(truncated["content"])
                break
        
        return result
    
    def _truncate_single_chunk(
        self,
        chunk: Dict[str, Any],
        max_tokens: int
    ) -> Dict[str, Any]:
        """Truncate a single chunk to fit token budget"""
        content = chunk["content"]
        tokens = self.encoding.encode(content)
        
        if len(tokens) <= max_tokens:
            return chunk
        
        if max_tokens < 50:  # Too small to be useful
            return None
        
        # Truncate and add ellipsis
        truncated_tokens = tokens[:max_tokens - 3]
        truncated_content = self.encoding.decode(truncated_tokens) + "..."
        
        # Create new chunk with truncated content
        truncated_chunk = chunk.copy()
        truncated_chunk["content"] = truncated_content
        truncated_chunk["meta"] = chunk["meta"].copy()
        truncated_chunk["meta"]["truncated"] = True
        
        return truncated_chunk
    
    def format_context_with_budget(
        self,
        chunks: List[Tuple[Dict[str, Any], float]],
        max_tokens: int = 8000
    ) -> str:
        """
        Format optimized context as string
        
        Args:
            chunks: List of (chunk_dict, score) tuples
            max_tokens: Maximum token budget
        
        Returns:
            Formatted context string
        """
        optimized = self.optimize_context(chunks, max_tokens)
        
        lines = []
        lines.append("=== RETRIEVED CONTEXT ===\n")
        
        for i, (chunk, score) in enumerate(optimized, 1):
            meta = chunk["meta"]
            lines.append(f"--- Chunk {i} (score: {score:.3f}) ---")
            lines.append(f"File: {meta.get('path', 'unknown')}")
            
            # Add metadata hints
            if meta.get("language"):
                lines.append(f"Language: {meta['language']}")
            if meta.get("has_tests"):
                lines.append("[Has Tests]")
            if meta.get("truncated"):
                lines.append("[Truncated]")
            
            lines.append(f"\n{chunk['content']}\n")
        
        lines.append(f"\n=== END CONTEXT ({len(optimized)} chunks) ===")
        
        return "\n".join(lines)


# Global context optimizer
_context_optimizer = None

def get_context_optimizer(model_name: str = "gpt-4") -> ContextOptimizer:
    """Get or create global context optimizer"""
    global _context_optimizer
    if _context_optimizer is None:
        _context_optimizer = ContextOptimizer(model_name)
    return _context_optimizer

