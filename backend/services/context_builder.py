"""
Context Builder Service - Combines RAG, Knowledge Graph, Pattern Mining, and ML Features.
Builds comprehensive context for artifact generation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.rag_retriever import RAGRetriever
from backend.services.rag_cache import get_rag_cache
from backend.services.knowledge_graph import get_builder as get_kg_builder
from backend.services.pattern_mining import get_miner
from backend.services.ml_features import get_engineer
from backend.services.universal_context import get_universal_context_service
from backend.core.config import settings
from backend.core.cache import get_cache_manager, cached
from backend.core.metrics import get_metrics_collector, timed
from backend.core.logger import get_logger
from backend.core.lazy_loading import lazy_property

logger = get_logger(__name__)
metrics = get_metrics_collector()


class ContextBuilder:
    """
    Context Builder service that combines multiple analysis sources.
    
    Features:
    - RAG retrieval (hybrid search)
    - Knowledge Graph analysis
    - Pattern Mining insights
    - ML Feature extraction
    - Context caching
    - Context assembly and ranking
    """
    
    def __init__(self):
        """Initialize Context Builder."""
        self.rag_retriever = RAGRetriever()
        self.rag_cache = get_rag_cache()
        self.kg_builder = get_kg_builder()
        self.pattern_miner = get_miner()
        self.ml_engineer = get_engineer()
        self.universal_context_service = get_universal_context_service()
        self._context_store: Dict[str, Dict[str, Any]] = {}  # Store contexts by ID
        
        logger.info("Context Builder initialized with Universal Context Powerhouse")
    
    @timed("context_build", tags={"operation": "build_context"})
    @cached(ttl=3600, key_prefix="context:")
    async def build_context(
        self,
        meeting_notes: str,
        repo_id: Optional[str] = None,
        include_rag: bool = True,
        include_kg: bool = True,
        include_patterns: bool = True,
        include_ml_features: bool = False,
        max_rag_chunks: int = 18,
        kg_depth: int = 2,
        artifact_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive context from multiple sources.
        
        Args:
            meeting_notes: User requirements/meeting notes
            repo_id: Optional repository identifier
            include_rag: Whether to include RAG retrieval
            include_kg: Whether to include Knowledge Graph analysis
            include_patterns: Whether to include Pattern Mining
            include_ml_features: Whether to include ML features (slower)
            max_rag_chunks: Maximum number of RAG chunks to retrieve
            kg_depth: Knowledge Graph traversal depth
        
        Returns:
            Dictionary with assembled context
        """
        # 🚀 STEP 1: Get Universal Context (baseline project knowledge)
        logger.info("🚀 Getting Universal Context - The baseline that knows your entire project by heart")
        universal_ctx = await self.universal_context_service.get_universal_context()
        
        context = {
            "meeting_notes": meeting_notes,
            "repo_id": repo_id,
            "created_at": datetime.now().isoformat(),
            "universal_context": {
                "project_directories": universal_ctx.get("project_directories", []),
                "total_files": universal_ctx.get("total_files", 0),
                "key_entities": universal_ctx.get("key_entities", []),
                "project_map": universal_ctx.get("project_map", {})
            },
            "sources": {}
        }
        
        logger.info(f"✅ Universal Context loaded: {universal_ctx.get('total_files', 0)} files, {len(universal_ctx.get('key_entities', []))} key entities")
        
        # Check cache first
        cache_key = self._get_cache_key(meeting_notes, repo_id, include_rag, include_kg, include_patterns)
        cached_context = self.rag_cache.get(meeting_notes)
        
        if cached_context and not include_ml_features:
            logger.info("Using cached targeted context (with universal baseline)")
            return {
                **context,
                "sources": {
                    "rag": {"cached": True, "context": cached_context}
                },
                "from_cache": True
            }
        
        # 🎯 STEP 2: Build targeted context on top of universal baseline
        logger.info("🎯 Building targeted context for this specific query")
        tasks = []
        
        if include_rag:
            # Use smart context that combines universal + targeted
            tasks.append(self._build_smart_rag_context(meeting_notes, max_rag_chunks, artifact_type))
        
        if include_kg:
            tasks.append(self._build_kg_context(meeting_notes, kg_depth))
        
        if include_patterns:
            tasks.append(self._build_pattern_context(meeting_notes))
        
        if include_ml_features:
            tasks.append(self._build_ml_features_context(meeting_notes))
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error building context source {i}: {result}", exc_info=result)
                continue
            
            source_name = ["rag", "kg", "patterns", "ml_features"][i]
            if result:
                context["sources"][source_name] = result
        
        # Assemble final context
        assembled_context = self._assemble_context(context)
        
        # Cache the assembled context
        if include_rag and "rag" in context["sources"]:
            rag_context = context["sources"]["rag"].get("context", "")
            if rag_context:
                self.rag_cache.set(meeting_notes, rag_context)
        
        final_context = {
            **context,
            "assembled_context": assembled_context,
            "from_cache": False,
            "context_id": context.get("created_at", datetime.now().isoformat())  # Use timestamp as ID
        }
        
        # Store context for retrieval by ID
        context_id = final_context["context_id"]
        self._context_store[context_id] = final_context
        
        return final_context
    
    async def _build_smart_rag_context(self, meeting_notes: str, max_chunks: int, artifact_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Build SMART RAG context using Universal Context + Targeted Retrieval.
        This is the POWERHOUSE approach that knows your entire project + specific query needs.
        """
        try:
            # Use Universal Context Service's smart retrieval
            smart_ctx = await self.universal_context_service.get_smart_context_for_query(
                query=meeting_notes,
                artifact_type=artifact_type,
                k=max_chunks
            )
            
            targeted_snippets = smart_ctx.get("targeted_snippets", [])
            key_entities = smart_ctx.get("key_entities", [])
            
            context_parts = []
            for snippet in targeted_snippets:
                content = snippet.get("content", "")
                metadata = snippet.get("metadata", {})
                score = snippet.get("combined_score", snippet.get("score", 0.0))
                importance = snippet.get("importance", 0.5)
                
                context_parts.append({
                    "content": content,
                    "file_path": metadata.get("file_path", "unknown"),
                    "score": score,
                    "importance": importance,
                    "metadata": metadata
                })
            
            # Build context string with importance indicators
            context_lines = []
            context_lines.append("=== PROJECT CONTEXT (Universal Knowledge + Targeted Retrieval) ===\n")
            
            # Add key entities summary
            if key_entities:
                context_lines.append("🔑 KEY PROJECT ENTITIES:")
                for entity in key_entities[:10]:
                    context_lines.append(f"  - {entity.get('name', 'unknown')} ({entity.get('type', 'unknown')})")
                context_lines.append("")
            
            # Add targeted snippets (sorted by combined score)
            context_lines.append("📄 RELEVANT CODE SNIPPETS (ranked by importance + relevance):\n")
            for i, part in enumerate(context_parts, 1):
                importance_stars = "⭐" * int(part["importance"] * 5)
                context_lines.append(f"\n--- Snippet {i} {importance_stars} (score: {part['score']:.3f}) ---")
                context_lines.append(f"File: {part['file_path']}")
                context_lines.append(part["content"])
            
            context_str = "\n".join(context_lines)
            
            return {
                "context": context_str,
                "snippets": context_parts,
                "num_snippets": len(context_parts),
                "avg_score": sum(s["score"] for s in context_parts) / len(context_parts) if context_parts else 0.0,
                "key_entities": key_entities,
                "uses_universal_context": True
            }
        except Exception as e:
            logger.error(f"Error building smart RAG context: {e}", exc_info=True)
            # Fallback to basic RAG
            return await self._build_basic_rag_context(meeting_notes, max_chunks, artifact_type)
    
    async def _build_basic_rag_context(self, meeting_notes: str, max_chunks: int, artifact_type: Optional[str] = None) -> Dict[str, Any]:
        """Build basic RAG context (fallback if smart context fails)."""
        try:
            snippets = await self.rag_retriever.retrieve(meeting_notes, k=max_chunks, artifact_type=artifact_type)
            
            context_parts = []
            for snippet in snippets:
                content = snippet.get("content", "")
                metadata = snippet.get("metadata", {})
                score = snippet.get("score", 0.0)
                
                context_parts.append({
                    "content": content,
                    "file_path": metadata.get("path", "unknown"),
                    "score": score,
                    "metadata": metadata
                })
            
            context_str = "\n---\n".join([s["content"] for s in context_parts])
            
            return {
                "context": context_str,
                "snippets": context_parts,
                "num_snippets": len(context_parts),
                "avg_score": sum(s["score"] for s in context_parts) / len(context_parts) if context_parts else 0.0,
                "uses_universal_context": False
            }
        except Exception as e:
            logger.error(f"Error building basic RAG context: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _build_kg_context(self, meeting_notes: str, depth: int) -> Dict[str, Any]:
        """Build Knowledge Graph context."""
        try:
            # Extract key terms from meeting notes for graph query
            key_terms = self._extract_key_terms(meeting_notes)
            
            # Get graph stats
            stats = self.kg_builder.get_stats()
            
            # Find relevant nodes
            relevant_nodes = []
            for term in key_terms[:5]:  # Limit to top 5 terms
                node_id = self.kg_builder._find_node_by_name(term)
                if node_id:
                    relevant_nodes.append({
                        "term": term,
                        "node_id": node_id,
                        "found": True
                    })
            
            # Get most connected nodes (likely important)
            most_connected = self.kg_builder.get_most_connected_nodes(top_k=10)
            
            # Get centrality metrics
            centrality = self.kg_builder.get_centrality("degree")
            top_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "graph_stats": stats,
                "relevant_nodes": relevant_nodes,
                "most_connected": [{"node_id": nid, "degree": deg} for nid, deg in most_connected],
                "top_central_nodes": [{"node_id": nid, "centrality": score} for nid, score in top_central],
                "key_terms_searched": key_terms
            }
        except Exception as e:
            logger.error(f"Error building KG context: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _build_pattern_context(self, meeting_notes: str) -> Dict[str, Any]:
        """Build Pattern Mining context."""
        try:
            # Get recent pattern mining results (if available)
            # For now, return summary of what patterns would be detected
            # In production, this would use cached pattern mining results
            
            return {
                "patterns_available": True,
                "note": "Pattern mining analysis should be run separately via /api/analysis/patterns",
                "suggested_patterns": [
                    "Singleton", "Factory", "Observer"
                ]
            }
        except Exception as e:
            logger.error(f"Error building pattern context: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _build_ml_features_context(self, meeting_notes: str) -> Dict[str, Any]:
        """Build ML Features context."""
        try:
            # Extract features from meeting notes itself
            features = self.ml_engineer.extract_code_features(meeting_notes, "meeting_notes.txt")
            
            return {
                "meeting_notes_features": features,
                "note": "ML features extracted from meeting notes. For code/diagram features, use /api/analysis/ml-features"
            }
        except Exception as e:
            logger.error(f"Error building ML features context: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _assemble_context(self, context: Dict[str, Any]) -> str:
        """
        Assemble context from all sources into a single string.
        
        Args:
            context: Context dictionary with sources
        
        Returns:
            Assembled context string
        """
        parts = []
        
        # Add Universal Context Summary (The Powerhouse Baseline)
        if "universal_context" in context:
            uc = context["universal_context"]
            parts.append("🚀 === UNIVERSAL PROJECT CONTEXT (Knows Your Entire Project By Heart) ===\n")
            parts.append(f"📂 Project Directories: {', '.join(uc.get('project_directories', []))}")
            parts.append(f"📄 Total Files Indexed: {uc.get('total_files', 0)}")
            parts.append(f"⭐ Key Entities: {len(uc.get('key_entities', []))}")
            
            # Add key entities if available
            key_entities = uc.get('key_entities', [])
            if key_entities:
                parts.append("\n🔑 Most Important Entities in Your Project:")
                for entity in key_entities[:10]:
                    parts.append(f"  - {entity.get('name', 'unknown')} ({entity.get('type', 'unknown')})")
            parts.append("\n")
        
        # Add meeting notes
        parts.append("=== YOUR REQUIREMENTS (Meeting Notes) ===\n")
        parts.append(context.get("meeting_notes", ""))
        parts.append("\n")
        
        # Add RAG context
        if "rag" in context.get("sources", {}):
            rag_source = context["sources"]["rag"]
            if "context" in rag_source:
                parts.append("\n=== CODEBASE CONTEXT (RAG) ===\n")
                parts.append(rag_source["context"])
                parts.append(f"\n({rag_source.get('num_snippets', 0)} snippets retrieved)")
                parts.append("\n")
        
        # Add Knowledge Graph insights
        if "kg" in context.get("sources", {}):
            kg_source = context["sources"]["kg"]
            if "graph_stats" in kg_source:
                stats = kg_source["graph_stats"]
                parts.append("\n=== KNOWLEDGE GRAPH INSIGHTS ===\n")
                parts.append(f"Graph: {stats.get('node_count', 0)} nodes, {stats.get('edge_count', 0)} edges")
                
                if "most_connected" in kg_source:
                    parts.append("\nMost Connected Components:")
                    for node in kg_source["most_connected"][:5]:
                        parts.append(f"  - {node['node_id']} (degree: {node['degree']})")
                parts.append("\n")
        
        # Add Pattern Mining insights
        if "patterns" in context.get("sources", {}):
            pattern_source = context["sources"]["patterns"]
            if "suggested_patterns" in pattern_source:
                parts.append("\n=== DESIGN PATTERNS DETECTED ===\n")
                parts.append(", ".join(pattern_source["suggested_patterns"]))
                parts.append("\n")
        
        # Add ML Features (if available)
        if "ml_features" in context.get("sources", {}):
            ml_source = context["sources"]["ml_features"]
            if "meeting_notes_features" in ml_source:
                features = ml_source["meeting_notes_features"]
                parts.append("\n=== ML FEATURES ===\n")
                parts.append(f"Complexity: {features.get('cyclomatic_complexity_estimate', 0)}")
                parts.append(f"Lines: {features.get('lines_of_code', 0)}")
                parts.append("\n")
        
        return "\n".join(parts)
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for graph queries."""
        # Simple extraction: words that are capitalized or common tech terms
        words = text.split()
        key_terms = []
        
        for word in words:
            # Remove punctuation
            clean_word = word.strip('.,!?;:()[]{}"\'').lower()
            
            # Skip common words
            if clean_word in ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'from']:
                continue
            
            # Add capitalized words (likely class names, components)
            if word[0].isupper() and len(word) > 2:
                key_terms.append(clean_word)
            
            # Add common tech terms
            tech_terms = ['api', 'model', 'service', 'controller', 'component', 'class', 'function', 'method']
            if clean_word in tech_terms:
                key_terms.append(clean_word)
        
        # Remove duplicates and return
        return list(dict.fromkeys(key_terms))[:10]  # Top 10 terms
    
    def _get_cache_key(self, meeting_notes: str, repo_id: Optional[str], *flags) -> str:
        """Generate cache key for context."""
        key_parts = [meeting_notes, repo_id or "", str(flags)]
        return "|".join(key_parts)
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a previously built context by ID.
        
        Args:
            context_id: Context identifier (timestamp)
        
        Returns:
            Context dictionary or None if not found
        """
        return self._context_store.get(context_id)
    
    async def get_context_by_id(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        Alias for get_context for consistency.
        
        Args:
            context_id: Context identifier (timestamp)
        
        Returns:
            Context dictionary or None if not found
        """
        return await self.get_context(context_id)


# Global builder instance
_builder: Optional[ContextBuilder] = None


def get_builder() -> ContextBuilder:
    """Get or create global Context Builder instance."""
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder

