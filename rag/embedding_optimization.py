"""
Embedding Optimization Techniques
Fine-tuning, caching, batch processing, semantic compression
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import hashlib
import pickle

@dataclass
class EmbeddingCache:
    """Cache for embeddings"""
    text_hash: str
    embedding: np.ndarray
    timestamp: float

class EmbeddingOptimizer:
    """
    Optimizes embedding generation and usage
    """
    
    def __init__(self, embedding_model):
        self.model = embedding_model
        self.cache = {}
        self.batch_size = 32
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    async def get_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """Get embedding with caching"""
        text_hash = self._hash_text(text)
        
        # Check cache
        if use_cache and text_hash in self.cache:
            return self.cache[text_hash].embedding
        
        # Generate embedding
        embedding = await self._generate_embedding(text)
        
        # Cache it
        import time
        self.cache[text_hash] = EmbeddingCache(
            text_hash=text_hash,
            embedding=embedding,
            timestamp=time.time()
        )
        
        return embedding
    
    async def get_embeddings_batch(self, texts: List[str], use_cache: bool = True) -> List[np.ndarray]:
        """Get embeddings in optimized batches"""
        embeddings = []
        to_generate = []
        to_generate_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            text_hash = self._hash_text(text)
            if use_cache and text_hash in self.cache:
                embeddings.append(self.cache[text_hash].embedding)
            else:
                embeddings.append(None)
                to_generate.append(text)
                to_generate_indices.append(i)
        
        # Generate missing embeddings in batches
        if to_generate:
            new_embeddings = await self._generate_embeddings_batch(to_generate)
            
            # Fill in results
            for idx, embedding in zip(to_generate_indices, new_embeddings):
                embeddings[idx] = embedding
                
                # Cache it
                import time
                text_hash = self._hash_text(texts[idx])
                self.cache[text_hash] = EmbeddingCache(
                    text_hash=text_hash,
                    embedding=embedding,
                    timestamp=time.time()
                )
        
        return embeddings
    
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate single embedding"""
        # Use existing embedding model
        return self.model.encode([text])[0]
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings in batch"""
        # Process in chunks of batch_size
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(batch)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def save_cache(self, filepath: str):
        """Save embedding cache to disk"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.cache, f)
    
    def load_cache(self, filepath: str):
        """Load embedding cache from disk"""
        try:
            with open(filepath, 'rb') as f:
                self.cache = pickle.load(f)
        except:
            pass

class SemanticCompression:
    """
    Compress text while preserving semantic meaning
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    async def compress_text(self, text: str, target_ratio: float = 0.5) -> str:
        """
        Compress text to target ratio while preserving key information
        target_ratio: 0.5 = compress to 50% of original length
        """
        target_length = int(len(text.split()) * target_ratio)
        
        prompt = f"""
Compress this text to approximately {target_length} words while preserving all key information:

Original Text:
{text}

Compressed Version (focus on key facts, technical details, and actionable information):"""
        
        compressed = await self.llm_client._call_ai(
            prompt,
            "Compress while preserving all important information."
        )
        
        return compressed
    
    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """Extract key points from text"""
        prompt = f"""
Extract the {max_points} most important points from this text:

Text:
{text}

Key Points (one per line):"""
        
        response = await self.llm_client._call_ai(
            prompt,
            "Extract key points concisely."
        )
        
        points = [line.strip() for line in response.split('\n') if line.strip() and not line.startswith('#')]
        return points[:max_points]

class ContextOptimizer:
    """
    Optimize context for LLM consumption
    """
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.compressor = SemanticCompression(llm_client)
    
    async def optimize_context(self, chunks: List[Dict], max_tokens: int = 4000) -> str:
        """
        Optimize context to fit within token limit
        Prioritizes most relevant information
        """
        # Sort by relevance (assuming 'score' field)
        sorted_chunks = sorted(chunks, key=lambda x: x.get('score', 0), reverse=True)
        
        # Build context incrementally
        context_parts = []
        current_tokens = 0
        
        for chunk in sorted_chunks:
            text = chunk.get('text', '')
            chunk_tokens = len(text.split()) * 1.3  # Rough token estimate
            
            if current_tokens + chunk_tokens > max_tokens:
                # Try to compress this chunk
                if current_tokens < max_tokens * 0.8:  # Still have room
                    compressed = await self.compressor.compress_text(text, target_ratio=0.3)
                    compressed_tokens = len(compressed.split()) * 1.3
                    
                    if current_tokens + compressed_tokens <= max_tokens:
                        context_parts.append(compressed)
                        current_tokens += compressed_tokens
                break
            
            context_parts.append(text)
            current_tokens += chunk_tokens
        
        return "\n\n---\n\n".join(context_parts)
    
    async def create_hierarchical_summary(self, chunks: List[Dict]) -> str:
        """
        Create hierarchical summary of chunks
        High-level overview + detailed sections
        """
        # Extract key points from each chunk
        all_key_points = []
        for chunk in chunks[:10]:  # Top 10 chunks
            points = await self.compressor.extract_key_points(chunk.get('text', ''), max_points=3)
            all_key_points.extend(points)
        
        # Create overview
        overview_prompt = f"""
Create a concise overview from these key points:

{chr(10).join(f"- {point}" for point in all_key_points)}

Overview:"""
        
        overview = await self.llm_client._call_ai(overview_prompt, "Create concise overview.")
        
        # Combine with detailed sections
        detailed_sections = []
        for i, chunk in enumerate(chunks[:5]):  # Top 5 for details
            detailed_sections.append(f"### Section {i+1}\n{chunk.get('text', '')[:500]}...")
        
        hierarchical = f"""# Overview
{overview}

# Detailed Information
{chr(10).join(detailed_sections)}
"""
        
        return hierarchical

class SmartRetrieval:
    """
    Smart retrieval that adapts based on query type
    """
    
    def __init__(self, embedding_optimizer: EmbeddingOptimizer, context_optimizer: ContextOptimizer):
        self.embedding_opt = embedding_optimizer
        self.context_opt = context_optimizer
    
    async def retrieve_and_optimize(self, query: str, retrieval_fn, max_tokens: int = 4000) -> str:
        """
        Retrieve and optimize context in one go
        """
        # Retrieve chunks
        chunks = await retrieval_fn(query)
        
        # Optimize context
        optimized_context = await self.context_opt.optimize_context(chunks, max_tokens)
        
        return optimized_context


def get_embedding_optimizer(embedding_model):
    """Get embedding optimizer"""
    return EmbeddingOptimizer(embedding_model)

def get_context_optimizer(llm_client):
    """Get context optimizer"""
    return ContextOptimizer(llm_client)

