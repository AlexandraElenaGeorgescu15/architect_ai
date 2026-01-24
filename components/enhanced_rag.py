"""
Enhanced RAG System with 100 Chunks and Flexible Context Window
Provides intelligent context assembly with tiered retrieval and adaptive context sizing

NOW WITH INTELLIGENT TASK TYPE DETECTION:
- Auto-detects fine-tuning vs generation tasks
- Dynamically adjusts context window and chunks based on task type and model
"""

import streamlit as st
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import json
import time
from datetime import datetime
import numpy as np
import logging

logger = logging.getLogger(__name__)

from components._tool_detector import (
    get_user_project_directories,
    should_exclude_path,
)


class TaskType(Enum):
    """Task type for intelligent RAG configuration"""
    FINE_TUNING = "fine_tuning"
    GENERATION = "generation"


@dataclass
class ChunkTier:
    """Represents a tier of chunks with different relevance levels"""
    tier_name: str
    chunks: List[Dict[str, Any]]
    relevance_score: float
    context_priority: int


@dataclass
class ContextAssembly:
    """Represents assembled context with metadata"""
    total_chunks: int
    total_tokens: int
    context_tiers: List[ChunkTier]
    assembly_strategy: str
    quality_score: float
    assembly_time: float
    context_text: str = ""


@dataclass
class ModelContextLimits:
    """Context limits for different AI models"""
    model_name: str
    max_tokens: int
    recommended_tokens: int
    context_window_type: str  # 'fixed', 'flexible', 'adaptive'


class EnhancedRAGSystem:
    """Enhanced RAG system with 100 chunks and flexible context window"""
    
    def __init__(self):
        # Updated Jan 2026 - Official model names
        self.model_limits = {
            'gpt-4o': ModelContextLimits('gpt-4o', 128000, 100000, 'flexible'),
            'gpt-4o-mini': ModelContextLimits('gpt-4o-mini', 128000, 100000, 'flexible'),
            'o1': ModelContextLimits('o1', 200000, 150000, 'flexible'),
            'gpt-4-turbo': ModelContextLimits('gpt-4-turbo', 128000, 100000, 'flexible'),  # Legacy
            'claude-sonnet-4': ModelContextLimits('claude-sonnet-4', 200000, 150000, 'flexible'),
            'claude-3-5-sonnet': ModelContextLimits('claude-3-5-sonnet', 200000, 150000, 'flexible'),
            'claude-3-sonnet': ModelContextLimits('claude-3-sonnet', 200000, 150000, 'flexible'),
            'claude-3-haiku': ModelContextLimits('claude-3-haiku', 200000, 150000, 'flexible'),
            'gemini-pro': ModelContextLimits('gemini-pro', 32000, 25000, 'flexible'),
            'gemini-pro-vision': ModelContextLimits('gemini-pro-vision', 32000, 25000, 'flexible'),
            'llama-2-70b': ModelContextLimits('llama-2-70b', 4096, 3000, 'fixed'),
            'llama-3-70b': ModelContextLimits('llama-3-70b', 8192, 6000, 'flexible'),
            'mistral-7b': ModelContextLimits('mistral-7b', 8192, 6000, 'flexible'),
            'codellama-7b': ModelContextLimits('codellama-7b', 16384, 12000, 'flexible')
        }
        
        self.assembly_strategies = {
            'tiered': self._assemble_tiered_context,
            'adaptive': self._assemble_adaptive_context,
            'hybrid': self._assemble_hybrid_context,
            'semantic': self._assemble_semantic_context
        }
        
        # Model-specific recommended chunks for generation tasks
        # Updated Jan 2026
        self.model_recommended_chunks = {
            'gpt-4o': 100,
            'gpt-4o-mini': 100,
            'o1': 100,
            'gpt-4-turbo': 100,  # Legacy
            'claude-sonnet-4': 100,
            'claude-3-5-sonnet': 100,
            'claude-3-sonnet': 100,
            'claude-3-haiku': 80,
            'gemini-pro': 100,
            'gemini-pro-vision': 100,
            'llama-2-70b': 20,
            'llama-3-70b': 50,
            'mistral-7b': 40,
            'codellama-7b': 60,
            'mixtral-8x7b': 40,
            'gemini-2.5-flash': 100,  # Updated Jan 2026
            'gemini-2.5-pro': 150
        }
    
        self.user_project_dirs = [p.resolve() for p in get_user_project_directories()]
        self.excluded_dirs = {
            '__pycache__',
            'node_modules',
            'dist',
            'build',
            'bin',
            'obj',
            '.git'
        }
        self.excluded_extensions = {
            '.pyc', '.pyo', '.dll', '.so', '.dylib', '.bin', '.exe', '.lock', '.sqlite3'
        }
        self.excluded_filenames = {
            'package-lock.json',
            'yarn.lock',
            'pnpm-lock.yaml',
            'package-lock.yaml'
        }

        self.provider_aliases = {
            'groq (free & fast)': 'llama-3.3-70b-versatile',
            'groq': 'llama-3.3-70b-versatile',
            'google gemini (free)': 'gemini-2.5-flash',
            'google gemini': 'gemini-2.5-flash',
            'openai gpt-4': 'gpt-4o',
            'openai': 'gpt-4o',
            'anthropic claude 3 opus': 'claude-3-opus',
            'anthropic claude 3 sonnet': 'claude-3-sonnet'
        }

        # Updated Jan 2026
        self.config_key_aliases = {
            'groq_api_key': 'llama-3.3-70b-versatile',
            'gemini_api_key': 'gemini-2.5-flash',
            'api_key': 'gpt-4o',
            'anthropic_api_key': 'claude-sonnet-4'
        }
    
    def get_optimal_config(self, model_name: str, task_type: TaskType,
                           alternate_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Intelligently determine optimal RAG configuration based on task type and model.
        
        Args:
            model_name: Name of the AI model
            task_type: Type of task (FINE_TUNING or GENERATION)
        
        Returns:
            dict: {
                'max_chunks': int,
                'context_window': int,
                'reason': str,
                'model_info': ModelContextLimits
            }
        """
        candidates = [model_name] + (alternate_names or [])
        resolution = None

        for candidate in candidates:
            resolution = self._resolve_model_limits(candidate)
            if resolution:
                break

        if resolution is None:
            return self._build_default_config(task_type)

        resolved_key, model_limits = resolution
        
        if task_type == TaskType.FINE_TUNING:
            # Fine-tuning needs MAXIMUM context
            return {
                'max_chunks': 500,  # Unlimited chunks for fine-tuning
                'context_window': model_limits.max_tokens,
                'reason': f'Fine-tuning requires maximum context for {resolved_key}',
                'model_info': model_limits,
                'task_type': 'fine_tuning',
                'resolved_model_name': resolved_key
            }
        else:  # GENERATION
            # Generation uses model-specific optimal chunks
            recommended_chunks = self.model_recommended_chunks.get(resolved_key)
            if recommended_chunks is None:
                estimated = max(18, min(60, model_limits.recommended_tokens // 400))
                recommended_chunks = estimated
                self.model_recommended_chunks[resolved_key] = recommended_chunks
            return {
                'max_chunks': recommended_chunks,
                'context_window': model_limits.recommended_tokens,
                'reason': f'Optimized for {resolved_key} generation capabilities',
                'model_info': model_limits,
                'task_type': 'generation',
                'resolved_model_name': resolved_key
            }
    
    async def retrieve_enhanced_context(self, query: str, model_name: str = "gpt-4", 
                                      max_chunks: int = 100, strategy: str = "tiered") -> ContextAssembly:
        """Retrieve enhanced context with up to 100 chunks and flexible context window"""
        
        start_time = time.time()
        
        resolution = self._resolve_model_limits(model_name)
        if resolution is None:
            resolution = self._build_default_limits()

        resolved_key, model_limits = resolution
        
        # Retrieve chunks from RAG system
        chunks = await self._retrieve_chunks_from_rag(query, max_chunks)
        
        # Log retrieval results
        print(f"[ENHANCED_RAG] Retrieved {len(chunks)} chunks from RAG system (requested: {max_chunks})")
        if len(chunks) == 0:
            print("[ENHANCED_RAG] ⚠️ WARNING: No chunks retrieved! RAG index may be empty or query didn't match.")
        elif len(chunks) < max_chunks:
            print(f"[ENHANCED_RAG] ℹ️ Retrieved {len(chunks)} chunks (less than requested {max_chunks})")
        else:
            print(f"[ENHANCED_RAG] ✅ Successfully retrieved {len(chunks)} chunks")
        
        # Organize chunks into tiers
        context_tiers = self._organize_chunks_into_tiers(chunks, query)
        
        # Assemble context based on strategy
        assembly_strategy = self.assembly_strategies.get(strategy, self._assemble_tiered_context)
        assembled_context = await assembly_strategy(context_tiers, model_limits)
        
        # Calculate quality score
        quality_score = self._calculate_context_quality(assembled_context, query)
        
        assembly_time = time.time() - start_time
        
        return ContextAssembly(
            total_chunks=len(chunks),
            total_tokens=assembled_context.get('total_tokens', 0),
            context_tiers=context_tiers,
            assembly_strategy=strategy,
            quality_score=quality_score,
            assembly_time=assembly_time,
            context_text=assembled_context.get('content', '')
        )

    def _resolve_model_limits(self, candidate: Optional[str]) -> Optional[Tuple[str, ModelContextLimits]]:
        if not candidate:
            return None

        key = candidate.strip()
        if not key:
            return None

        normalized = ''.join(ch for ch in key.lower() if ch.isalnum() or ch in {' ', '-', '_', ':'})
        normalized = ' '.join(normalized.split())

        if key in self.model_limits:
            return key, self.model_limits[key]
        if normalized in self.model_limits:
            return normalized, self.model_limits[normalized]

        alias_key = self.provider_aliases.get(normalized)
        if alias_key and alias_key in self.model_limits:
            return alias_key, self.model_limits[alias_key]

        config_alias = self.config_key_aliases.get(normalized)
        if config_alias and config_alias in self.model_limits:
            return config_alias, self.model_limits[config_alias]

        try:
            from config.model_config import dynamic_model_config

            dynamic_config = (
                dynamic_model_config.get_model_config(key)
                or dynamic_model_config.get_model_config(normalized)
            )
            if dynamic_config:
                limits = ModelContextLimits(
                    key,
                    dynamic_config.context_window,
                    dynamic_config.recommended_context,
                    'flexible'
                )
                self.model_limits[key] = limits
                return key, limits
        except Exception as e:
            logger.debug(f"Dynamic model config unavailable: {e}")

        return None

    def _build_default_limits(self) -> Tuple[str, ModelContextLimits]:
        default_limits = self.model_limits['gpt-4o']
        return 'gpt-4o', default_limits

    def _build_default_config(self, task_type: TaskType) -> Dict[str, Any]:
        default_limits = self.model_limits.get('gpt-4o')
        if task_type == TaskType.FINE_TUNING:
            return {
                'max_chunks': 500,
                'context_window': default_limits.max_tokens,
                'reason': 'Safe defaults for fine-tuning (model unknown)',
                'model_info': default_limits,
                'task_type': 'fine_tuning',
                'resolved_model_name': 'gpt-4o'
            }

        safe_chunks = 24
        return {
            'max_chunks': safe_chunks,
            'context_window': default_limits.recommended_tokens,
            'reason': 'Safe defaults for unknown model (limited chunks)',
            'model_info': default_limits,
            'task_type': 'generation',
            'resolved_model_name': 'gpt-4o'
        }
    
    async def _retrieve_chunks_from_rag(self, query: str, max_chunks: int) -> List[Dict[str, Any]]:
        """Retrieve chunks from the RAG system using the actual retrieval implementation"""
        
        try:
            # Use the actual RAG retrieval system (same as UniversalArchitectAgent)
            from rag.retrieve import vector_search, bm25_search, merge_rerank, load_docs_from_chroma
            from rag.utils import chroma_client, BM25Index
            from rag.filters import load_cfg
            
            cfg = load_cfg()
            client = chroma_client(cfg["store"]["path"])
            collection = client.get_or_create_collection("repo", metadata={"hnsw:space": "cosine"})
            docs = load_docs_from_chroma(collection)
            bm25 = BM25Index(docs)
            
            # Use hybrid search (vector + BM25) like the agent does
            # Scale up k values for enhanced RAG (100 chunks)
            k_vector = min(max_chunks * 2, 200)  # Get more vector results
            k_bm25 = min(max_chunks * 2, 200)    # Get more BM25 results
            k_final = max_chunks                  # Final merged results
            
            vec_hits = vector_search(collection, query, k_vector)
            bm25_hits = bm25_search(bm25, query, k_bm25)
            merged_hits = merge_rerank(vec_hits, bm25_hits, k_final)
            
            print(f"[ENHANCED_RAG] Hybrid search results: {len(vec_hits)} vector hits, {len(bm25_hits)} BM25 hits, {len(merged_hits)} merged hits")
            
            # Format chunks to expected structure
            formatted_chunks = []
            for doc, score in merged_hits:
                formatted_chunk = {
                    'content': doc.get('content', ''),
                    'metadata': doc.get('meta', {}),
                    'similarity_score': float(score)
                }
                formatted_chunks.append(formatted_chunk)
            
            filtered = self._filter_chunks(formatted_chunks)
            print(f"[ENHANCED_RAG] After filtering: {len(filtered)} chunks (filtered out {len(formatted_chunks) - len(filtered)} chunks)")
            
            return filtered
            
        except Exception as e:
            # If RAG system is completely unavailable, log error and return empty
            print(f"[ENHANCED_RAG] Warning: Could not retrieve RAG chunks: {e}")
            print("[ENHANCED_RAG] RAG system may not be initialized. Please run 'python rag/ingest.py' to index your repository.")
            import traceback
            print(f"[ENHANCED_RAG] Traceback: {traceback.format_exc()}")
            return []

    def _filter_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out chunks that are outside user projects or represent binaries/artifacts."""

        filtered: List[Dict[str, Any]] = []

        for chunk in chunks or []:
            metadata = chunk.get('metadata') or chunk.get('meta') or {}
            path_str = metadata.get('path') or metadata.get('file_path') or metadata.get('source')

            if not path_str:
                filtered.append(chunk)
                continue

            path_obj = Path(path_str)
            if not path_obj.is_absolute():
                try:
                    path_obj = (Path.cwd() / path_obj).resolve()
                except Exception as e:
                    logger.debug(f"Path resolution failed: {e}")

            try:
                if should_exclude_path(path_obj):
                    continue
            except Exception as e:
                logger.debug(f"Path exclusion check failed: {e}")

            if not any(self._is_within_directory(path_obj, root) for root in self.user_project_dirs):
                continue

            if any(ex_dir in path_obj.parts for ex_dir in self.excluded_dirs):
                continue

            lowered_name = path_obj.name.lower()
            lowered_suffix = path_obj.suffix.lower()

            if lowered_suffix in self.excluded_extensions:
                continue
            if lowered_name in self.excluded_filenames:
                continue
            if lowered_name.endswith('lock') or lowered_name.endswith('lock.json'):
                continue

            filtered.append(chunk)

        return filtered

    @staticmethod
    def _is_within_directory(path: Path, directory: Path) -> bool:
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False
    
    def _organize_chunks_into_tiers(self, chunks: List[Dict[str, Any]], query: str) -> List[ChunkTier]:
        """Organize chunks into relevance tiers"""
        
        # Sort chunks by relevance score
        sorted_chunks = sorted(chunks, key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        # Create tiers based on relevance
        tiers = []
        
        # Tier 1: High relevance (top 20%)
        high_relevance = sorted_chunks[:len(sorted_chunks)//5]
        if high_relevance:
            tiers.append(ChunkTier(
                tier_name="High Relevance",
                chunks=high_relevance,
                relevance_score=0.9,
                context_priority=1
            ))
        
        # Tier 2: Medium relevance (next 30%)
        medium_relevance = sorted_chunks[len(sorted_chunks)//5:len(sorted_chunks)//2]
        if medium_relevance:
            tiers.append(ChunkTier(
                tier_name="Medium Relevance",
                chunks=medium_relevance,
                relevance_score=0.7,
                context_priority=2
            ))
        
        # Tier 3: Low relevance (remaining 50%)
        low_relevance = sorted_chunks[len(sorted_chunks)//2:]
        if low_relevance:
            tiers.append(ChunkTier(
                tier_name="Low Relevance",
                chunks=low_relevance,
                relevance_score=0.5,
                context_priority=3
            ))
        
        return tiers
    
    async def _assemble_tiered_context(self, context_tiers: List[ChunkTier], 
                                     model_limits: ModelContextLimits) -> Dict[str, Any]:
        """Assemble context using tiered approach"""
        
        assembled_context = {
            'content': '',
            'total_tokens': 0,
            'tier_usage': {},
            'strategy': 'tiered'
        }
        
        current_tokens = 0
        max_tokens = model_limits.recommended_tokens
        
        # Add chunks from each tier in priority order
        for tier in context_tiers:
            tier_tokens = 0
            tier_content = []
            
            for chunk in tier.chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                
                if current_tokens + chunk_tokens <= max_tokens:
                    tier_content.append(chunk['content'])
                    current_tokens += chunk_tokens
                    tier_tokens += chunk_tokens
                else:
                    break
            
            if tier_content:
                assembled_context['content'] += f"\n\n## {tier.tier_name}\n"
                assembled_context['content'] += "\n".join(tier_content)
                assembled_context['tier_usage'][tier.tier_name] = {
                    'chunks_used': len(tier_content),
                    'tokens_used': tier_tokens
                }
        
        assembled_context['total_tokens'] = current_tokens
        return assembled_context
    
    async def _assemble_adaptive_context(self, context_tiers: List[ChunkTier], 
                                       model_limits: ModelContextLimits) -> Dict[str, Any]:
        """Assemble context using adaptive approach based on model capabilities"""
        
        assembled_context = {
            'content': '',
            'total_tokens': 0,
            'adaptive_strategy': {},
            'strategy': 'adaptive'
        }
        
        # Adaptive token allocation based on model type
        if model_limits.context_window_type == 'flexible':
            # Use more tokens for flexible models
            max_tokens = model_limits.recommended_tokens
            chunk_ratio = 0.8  # Use 80% of available tokens
        else:
            # Conservative approach for fixed models
            max_tokens = model_limits.recommended_tokens
            chunk_ratio = 0.6  # Use 60% of available tokens
        
        available_tokens = int(max_tokens * chunk_ratio)
        current_tokens = 0
        
        # Adaptive chunk selection
        for tier in context_tiers:
            tier_tokens = 0
            tier_content = []
            
            # Calculate how many tokens to allocate to this tier
            tier_allocation = available_tokens // len(context_tiers)
            
            for chunk in tier.chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                
                if current_tokens + chunk_tokens <= available_tokens and tier_tokens + chunk_tokens <= tier_allocation:
                    tier_content.append(chunk['content'])
                    current_tokens += chunk_tokens
                    tier_tokens += chunk_tokens
                else:
                    break
            
            if tier_content:
                assembled_context['content'] += f"\n\n## {tier.tier_name}\n"
                assembled_context['content'] += "\n".join(tier_content)
                assembled_context['adaptive_strategy'][tier.tier_name] = {
                    'chunks_used': len(tier_content),
                    'tokens_used': tier_tokens,
                    'allocation': tier_allocation
                }
        
        assembled_context['total_tokens'] = current_tokens
        return assembled_context
    
    async def _assemble_hybrid_context(self, context_tiers: List[ChunkTier], 
                                     model_limits: ModelContextLimits) -> Dict[str, Any]:
        """Assemble context using hybrid approach combining multiple strategies"""
        
        assembled_context = {
            'content': '',
            'total_tokens': 0,
            'hybrid_strategy': {},
            'strategy': 'hybrid'
        }
        
        # Hybrid approach: combine tiered and adaptive
        max_tokens = model_limits.recommended_tokens
        current_tokens = 0
        
        # First pass: Add high relevance chunks
        high_tier = next((tier for tier in context_tiers if tier.context_priority == 1), None)
        if high_tier:
            for chunk in high_tier.chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                if current_tokens + chunk_tokens <= max_tokens * 0.4:  # Use 40% for high relevance
                    assembled_context['content'] += f"\n{chunk['content']}\n"
                    current_tokens += chunk_tokens
        
        # Second pass: Add medium relevance chunks
        medium_tier = next((tier for tier in context_tiers if tier.context_priority == 2), None)
        if medium_tier:
            for chunk in medium_tier.chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                if current_tokens + chunk_tokens <= max_tokens * 0.7:  # Use 70% total
                    assembled_context['content'] += f"\n{chunk['content']}\n"
                    current_tokens += chunk_tokens
        
        # Third pass: Add low relevance chunks if space available
        low_tier = next((tier for tier in context_tiers if tier.context_priority == 3), None)
        if low_tier:
            for chunk in low_tier.chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                if current_tokens + chunk_tokens <= max_tokens:
                    assembled_context['content'] += f"\n{chunk['content']}\n"
                    current_tokens += chunk_tokens
        
        assembled_context['total_tokens'] = current_tokens
        return assembled_context
    
    async def _assemble_semantic_context(self, context_tiers: List[ChunkTier], 
                                       model_limits: ModelContextLimits) -> Dict[str, Any]:
        """Assemble context using semantic clustering approach"""
        
        assembled_context = {
            'content': '',
            'total_tokens': 0,
            'semantic_clusters': {},
            'strategy': 'semantic'
        }
        
        # Group chunks by semantic similarity
        semantic_clusters = self._cluster_chunks_semantically(context_tiers)
        
        max_tokens = model_limits.recommended_tokens
        current_tokens = 0
        
        # Add chunks from each semantic cluster
        for cluster_id, cluster_chunks in semantic_clusters.items():
            cluster_tokens = 0
            cluster_content = []
            
            for chunk in cluster_chunks:
                chunk_tokens = self._estimate_tokens(chunk['content'])
                
                if current_tokens + chunk_tokens <= max_tokens:
                    cluster_content.append(chunk['content'])
                    current_tokens += chunk_tokens
                    cluster_tokens += chunk_tokens
                else:
                    break
            
            if cluster_content:
                assembled_context['content'] += f"\n\n## Semantic Cluster {cluster_id}\n"
                assembled_context['content'] += "\n".join(cluster_content)
                assembled_context['semantic_clusters'][cluster_id] = {
                    'chunks_used': len(cluster_content),
                    'tokens_used': cluster_tokens
                }
        
        assembled_context['total_tokens'] = current_tokens
        return assembled_context
    
    def _cluster_chunks_semantically(self, context_tiers: List[ChunkTier]) -> Dict[str, List[Dict[str, Any]]]:
        """Cluster chunks by semantic similarity"""
        
        clusters = {}
        cluster_id = 0
        
        for tier in context_tiers:
            for chunk in tier.chunks:
                # Simple clustering based on file type and content keywords
                content = chunk['content'].lower()
                
                if 'api' in content or 'endpoint' in content:
                    cluster_key = 'api_cluster'
                elif 'database' in content or 'model' in content:
                    cluster_key = 'database_cluster'
                elif 'auth' in content or 'login' in content:
                    cluster_key = 'auth_cluster'
                else:
                    cluster_key = f'general_cluster_{cluster_id}'
                    cluster_id += 1
                
                if cluster_key not in clusters:
                    clusters[cluster_key] = []
                clusters[cluster_key].append(chunk)
        
        return clusters
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def _calculate_context_quality(self, assembled_context: Dict[str, Any], query: str) -> float:
        """Calculate quality score for assembled context"""
        
        quality_score = 0.0
        
        # Factor 1: Token utilization (0-0.3)
        total_tokens = assembled_context.get('total_tokens', 0)
        if total_tokens > 0:
            quality_score += min(0.3, total_tokens / 1000 * 0.1)
        
        # Factor 2: Content diversity (0-0.3)
        content = assembled_context.get('content', '')
        unique_words = len(set(content.lower().split()))
        quality_score += min(0.3, unique_words / 1000 * 0.3)
        
        # Factor 3: Query relevance (0-0.4)
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        relevance = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0
        quality_score += min(0.4, relevance * 0.4)
        
        return min(1.0, quality_score)
    
    def get_model_context_info(self, model_name: str) -> ModelContextLimits:
        """Get context information for a specific model"""
        return self.model_limits.get(model_name, self.model_limits['gpt-4'])
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available assembly strategies"""
        return list(self.assembly_strategies.keys())


# Global instance
enhanced_rag_system = EnhancedRAGSystem()


def render_enhanced_rag_ui():
    """Streamlit UI for enhanced RAG system"""
    
    st.subheader("🧠 Enhanced RAG System (100 Chunks + Flexible Context)")
    
    # Input section
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔍 Query:**")
        query = st.text_area(
            "Enter your query:",
            height=100,
            placeholder="Enter your query for enhanced RAG retrieval...",
            key="enhanced_rag_query"
        )
    
    with col2:
        st.write("**🤖 AI Model:**")
        model_name = st.selectbox(
            "Select AI Model:",
            list(enhanced_rag_system.model_limits.keys()),
            key="enhanced_rag_model"
        )
        
        st.write("**📊 Max Chunks:**")
        max_chunks = st.slider(
            "Maximum chunks to retrieve:",
            min_value=10,
            max_value=100,
            value=50,
            key="enhanced_rag_max_chunks"
        )
    
    # Strategy selection
    st.write("**🎯 Assembly Strategy:**")
    strategy = st.selectbox(
        "Select context assembly strategy:",
        enhanced_rag_system.get_available_strategies(),
        key="enhanced_rag_strategy"
    )
    
    # Model info
    model_info = enhanced_rag_system.get_model_context_info(model_name)
    st.info(f"**Model Info:** {model_info.model_name} | Max Tokens: {model_info.max_tokens:,} | Recommended: {model_info.recommended_tokens:,} | Type: {model_info.context_window_type}")
    
    # Generate button
    if st.button("🧠 Retrieve Enhanced Context", type="primary"):
        if not query.strip():
            st.warning("Please enter a query")
            return
        
        with st.spinner("Retrieving enhanced context..."):
            try:
                # Retrieve enhanced context
                context_assembly = asyncio.run(
                    enhanced_rag_system.retrieve_enhanced_context(
                        query, model_name, max_chunks, strategy
                    )
                )
                
                # Store in session state
                st.session_state.enhanced_rag_result = context_assembly
                st.success("✅ Enhanced context retrieved!")
                
            except Exception as e:
                st.error(f"❌ Error retrieving context: {str(e)}")
    
    # Display results
    if 'enhanced_rag_result' in st.session_state:
        result = st.session_state.enhanced_rag_result
        
        st.divider()
        
        # Results overview
        st.write("**📊 Context Assembly Results:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Chunks", result.total_chunks)
        with col2:
            st.metric("Total Tokens", f"{result.total_tokens:,}")
        with col3:
            st.metric("Quality Score", f"{result.quality_score:.2f}")
        with col4:
            st.metric("Assembly Time", f"{result.assembly_time:.2f}s")
        
        # Strategy info
        st.info(f"**Strategy:** {result.assembly_strategy} | **Quality:** {result.quality_score:.2f}/1.0")
        
        # Display context tiers
        tab1, tab2, tab3 = st.tabs(["📚 Context Content", "📊 Tier Analysis", "🔍 Raw Data"])
        
        with tab1:
            st.write("**Assembled Context:**")
            st.text_area(
                "Context Content:",
                value=result.context_tiers[0].chunks[0]['content'] if result.context_tiers and result.context_tiers[0].chunks else "No content available",
                height=400,
                key="context_content_display"
            )
        
        with tab2:
            st.write("**Tier Analysis:**")
            for tier in result.context_tiers:
                with st.expander(f"📊 {tier.tier_name} (Score: {tier.relevance_score:.2f})"):
                    st.write(f"**Chunks:** {len(tier.chunks)}")
                    st.write(f"**Priority:** {tier.context_priority}")
                    st.write(f"**Relevance Score:** {tier.relevance_score:.2f}")
                    
                    # Show sample chunks
                    if tier.chunks:
                        st.write("**Sample Chunks:**")
                        for i, chunk in enumerate(tier.chunks[:3]):
                            st.write(f"{i+1}. {chunk['content'][:100]}...")
        
        with tab3:
            st.write("**Raw Assembly Data:**")
            st.json({
                "total_chunks": result.total_chunks,
                "total_tokens": result.total_tokens,
                "assembly_strategy": result.assembly_strategy,
                "quality_score": result.quality_score,
                "assembly_time": result.assembly_time,
                "tiers": [
                    {
                        "name": tier.tier_name,
                        "chunks_count": len(tier.chunks),
                        "relevance_score": tier.relevance_score,
                        "priority": tier.context_priority
                    }
                    for tier in result.context_tiers
                ]
            })


def render_enhanced_rag_tab():
    """Render the enhanced RAG tab"""
    render_enhanced_rag_ui()
