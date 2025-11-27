"""
RAG Retrieval Service - Refactored from rag/retrieve.py
Handles hybrid search (BM25 + vector), reranking, and context assembly.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
import os

# Disable ChromaDB telemetry before import
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "True")

import chromadb
from chromadb.config import Settings as ChromaSettings

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import BM25 from existing rag utils
try:
    from rag.utils import BM25Index, chroma_client
except ImportError:
    # Fallback if rag.utils not available
    from rank_bm25 import BM25Okapi
    BM25Index = None

from backend.core.config import settings

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    RAG retrieval service for hybrid search.
    
    Features:
    - Vector search (ChromaDB)
    - BM25 search (keyword-based)
    - Hybrid reranking
    - Query logging
    - Metadata filtering
    """
    
    def __init__(self, index_path: Optional[str] = None):
        """
        Initialize RAG retriever.
        
        Args:
            index_path: Path to ChromaDB index (defaults to settings.rag_index_path)
        """
        self.index_path = Path(index_path or settings.rag_index_path)
        
        # Use shared ChromaDB client to avoid "different settings" conflicts
        from backend.core.chromadb_client import get_shared_chromadb_client
        self.client = get_shared_chromadb_client(str(self.index_path))
        
        # Get collection
        self.collection = self.client.get_or_create_collection(
            name="repo",
            metadata={"hnsw:space": "cosine"}
        )
        
        # BM25 index (lazy-loaded)
        self._bm25_index: Optional[Any] = None
        self._docs_cache: Optional[List[Dict]] = None
        
        # Query logging
        self.query_log: List[Dict[str, Any]] = []
        self.max_log_size = 1000
        
        logger.info(f"RAG Retriever initialized with index at {self.index_path}")
    
    def _load_docs_for_bm25(self) -> List[Dict[str, Any]]:
        """
        Load documents from ChromaDB for BM25 indexing.
        
        Returns:
            List of document dictionaries
        """
        if self._docs_cache is not None:
            return self._docs_cache
        
        try:
            res = self.collection.get(
                include=["documents", "metadatas"],
                limit=100000
            )
            
            docs = []
            for i, (doc, meta) in enumerate(zip(res["documents"], res["metadatas"])):
                docs.append({
                    "id": i,
                    "content": doc,
                    "meta": meta or {}
                })
            
            self._docs_cache = docs
            logger.info(f"Loaded {len(docs)} documents for BM25")
            return docs
            
        except Exception as e:
            logger.error(f"Error loading documents for BM25: {e}")
            return []
    
    def _get_bm25_index(self):
        """Get or create BM25 index."""
        if self._bm25_index is None:
            docs = self._load_docs_for_bm25()
            if docs and BM25Index:
                self._bm25_index = BM25Index(docs)
            elif docs:
                # Fallback: create BM25 index directly
                from rank_bm25 import BM25Okapi
                tokenized_docs = [doc["content"].lower().split() for doc in docs]
                self._bm25_index = BM25Okapi(tokenized_docs)
                # Store docs for search results
                self._bm25_docs = docs
        
        return self._bm25_index
    
    def vector_search(
        self, 
        query: str, 
        k: int = 200,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query
            k: Number of results
            metadata_filter: Optional metadata filter
        
        Returns:
            List of (document, score) tuples
        """
        try:
            query_params = {
                "query_texts": [query],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if metadata_filter:
                query_params["where"] = metadata_filter
            
            res = self.collection.query(**query_params)
            
            results = []
            for doc, meta, dist in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0]
            ):
                results.append((
                    {"content": doc, "meta": meta or {}},
                    1.0 - float(dist)  # Convert distance to similarity
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}", exc_info=True)
            return []
    
    def bm25_search(self, query: str, k: int = 200) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform BM25 keyword search.
        
        Args:
            query: Search query
            k: Number of results
        
        Returns:
            List of (document, score) tuples
        """
        try:
            bm25 = self._get_bm25_index()
            if not bm25:
                return []
            
            docs = self._load_docs_for_bm25()
            if not docs:
                return []
            
            # Tokenize query
            query_tokens = query.lower().split()
            
            # Get scores
            if hasattr(bm25, 'search'):
                # Using our BM25Index wrapper
                results = bm25.search(query, k=k)
            else:
                # Using BM25Okapi directly
                scores = bm25.get_scores(query_tokens)
                top_indices = sorted(
                    range(len(scores)),
                    key=lambda i: scores[i],
                    reverse=True
                )[:k]
                
                results = []
                for idx in top_indices:
                    score = scores[idx]
                    if score > 0:
                        results.append((docs[idx], score))
                return results
            
            return results
            
        except Exception as e:
            logger.error(f"BM25 search error: {e}", exc_info=True)
            return []
    
    def _create_smart_metadata_filter(self, artifact_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create intelligent metadata filter based on artifact type.
        This helps retrieve more relevant files for specific artifact types.
        
        Args:
            artifact_type: Artifact type
        
        Returns:
            Metadata filter dictionary or None
        """
        if not artifact_type:
            return None
        
        # Map artifact types to relevant file extensions
        file_type_preferences = {
            # ERD and database diagrams prefer model/entity files
            "mermaid_erd": [".py", ".cs", ".ts", ".java"],  # Model files
            "html_erd": [".py", ".cs", ".ts", ".java"],
            
            # Architecture diagrams prefer config and main files
            "mermaid_architecture": [".py", ".cs", ".ts", ".js", ".json", ".yaml", ".yml"],
            "html_architecture": [".py", ".cs", ".ts", ".js", ".json", ".yaml", ".yml"],
            
            # API and sequence diagrams prefer controller/route files
            "mermaid_api_sequence": [".py", ".cs", ".ts", ".js"],
            "mermaid_sequence": [".py", ".cs", ".ts", ".js"],
            "html_api_sequence": [".py", ".cs", ".ts", ".js"],
            "html_sequence": [".py", ".cs", ".ts", ".js"],
            
            # Class diagrams prefer class/interface files
            "mermaid_class": [".py", ".cs", ".ts", ".java"],
            "html_class": [".py", ".cs", ".ts", ".java"],
            
            # Code prototypes prefer implementation files
            "code_prototype": [".py", ".cs", ".ts", ".js", ".jsx", ".tsx"],
            
            # Visual prototypes prefer frontend files
            "dev_visual_prototype": [".tsx", ".jsx", ".ts", ".js", ".html", ".css", ".scss"],
            
            # API docs prefer controller/route files
            "api_docs": [".py", ".cs", ".ts", ".js", ".yaml", ".yml", ".json"],
        }
        
        preferred_extensions = file_type_preferences.get(artifact_type, [])
        
        # Note: ChromaDB metadata filtering syntax depends on the metadata structure
        # This is a placeholder - actual implementation would need to match the metadata schema
        if preferred_extensions:
            logger.debug(f"Smart filter for {artifact_type}: prioritizing {preferred_extensions}")
            # Return None for now as we'll boost these in the query instead
            # In a more advanced implementation, this would be a proper ChromaDB filter
        
        return None
    
    def hybrid_search(
        self,
        query: str,
        k_vector: int = 200,
        k_bm25: int = 200,
        k_final: int = 18,
        metadata_filter: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
        artifact_type: Optional[str] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform intelligent hybrid search combining vector and BM25 with artifact-aware enhancements.
        
        Args:
            query: Search query
            k_vector: Number of vector results
            k_bm25: Number of BM25 results
            k_final: Final number of results after reranking
            metadata_filter: Optional metadata filter
            vector_weight: Weight for vector scores (default: 0.6)
            bm25_weight: Weight for BM25 scores (default: 0.4)
            artifact_type: Optional artifact type for targeted retrieval
        
        Returns:
            List of (document, score) tuples, sorted by score
        """
        # Enhance query based on artifact type for better targeting
        enhanced_query = self._enhance_query_for_artifact(query, artifact_type)
        
        # Create smart metadata filter if no filter provided
        if not metadata_filter and artifact_type:
            metadata_filter = self._create_smart_metadata_filter(artifact_type)
        
        # Log query
        self._log_query(enhanced_query, k_final)
        
        # Perform both searches with enhanced query
        vec_hits = self.vector_search(enhanced_query, k=k_vector, metadata_filter=metadata_filter)
        bm25_hits = self.bm25_search(enhanced_query, k=k_bm25)
        
        # Merge and rerank using RRF
        return self._merge_rerank(vec_hits, bm25_hits, k_final, vector_weight, bm25_weight)
    
    def _reciprocal_rank_fusion(
        self,
        vec_hits: List[Tuple[Dict[str, Any], float]],
        bm25_hits: List[Tuple[Dict[str, Any], float]],
        k: int = 60
    ) -> Dict[str, float]:
        """
        Apply Reciprocal Rank Fusion (RRF) for better result merging.
        RRF is more robust than simple score averaging.
        
        Args:
            vec_hits: Vector search results
            bm25_hits: BM25 search results
            k: Constant for RRF (default: 60)
        
        Returns:
            Dictionary mapping doc keys to RRF scores
        """
        rrf_scores = {}
        
        # Process vector hits
        for rank, (doc, _) in enumerate(vec_hits, 1):
            file_path = doc.get("meta", {}).get("file_path", "")
            chunk_id = doc.get("meta", {}).get("chunk", "")
            key = f"{file_path}::{chunk_id}"
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank)
        
        # Process BM25 hits
        for rank, (doc, _) in enumerate(bm25_hits, 1):
            file_path = doc.get("meta", {}).get("file_path", "")
            chunk_id = doc.get("meta", {}).get("chunk", "")
            key = f"{file_path}::{chunk_id}"
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (k + rank)
        
        return rrf_scores
    
    def _merge_rerank(
        self,
        vec_hits: List[Tuple[Dict[str, Any], float]],
        bm25_hits: List[Tuple[Dict[str, Any], float]],
        k_final: int,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Merge and rerank results using Reciprocal Rank Fusion (RRF).
        RRF is more robust than simple weighted averaging for hybrid search.
        
        Args:
            vec_hits: Vector search results
            bm25_hits: BM25 search results
            k_final: Final number of results
            vector_weight: Weight for vector scores (used in fallback)
            bm25_weight: Weight for BM25 scores (used in fallback)
        
        Returns:
            Merged and reranked results
        """
        # Try RRF first (more sophisticated)
        rrf_scores = self._reciprocal_rank_fusion(vec_hits, bm25_hits)
        
        # Create document pool with RRF scores
        doc_pool = {}
        for doc, _ in vec_hits + bm25_hits:
            file_path = doc.get("meta", {}).get("file_path", "")
            chunk_id = doc.get("meta", {}).get("chunk", "")
            key = f"{file_path}::{chunk_id}"
            
            if key not in doc_pool:
                doc_pool[key] = {
                    "doc": doc,
                    "rrf_score": rrf_scores.get(key, 0),
                }
        
        # Sort by RRF score
        sorted_docs = sorted(
            doc_pool.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )[:k_final]
        
        # Return as list of (doc, score) tuples
        return [(item["doc"], item["rrf_score"]) for item in sorted_docs]
        
        # Fallback: Original weighted averaging (kept for reference)
        # Normalize scores
        v_max = max([s for _, s in vec_hits], default=1.0) or 1.0
        b_max = max([s for _, s in bm25_hits], default=1.0) or 1.0
        
        # Combine results
        pool = []
        for doc, score in vec_hits:
            normalized_score = vector_weight * (score / v_max) if v_max > 0 else 0
            pool.append((doc, normalized_score))
        
        for doc, score in bm25_hits:
            normalized_score = bm25_weight * (score / b_max) if b_max > 0 else 0
            pool.append((doc, normalized_score))
        
        # Deduplicate and sort
        seen = set()
        merged = []
        
        for doc, score in sorted(pool, key=lambda x: x[1], reverse=True):
            # Create unique key from file path and chunk
            file_path = doc.get("meta", {}).get("file_path", "")
            chunk_id = doc.get("meta", {}).get("chunk", "")
            key = f"{file_path}::{chunk_id}"
            
            if key in seen:
                continue
            
            seen.add(key)
            merged.append((doc, score))
            
            if len(merged) >= k_final:
                break
        
        return merged
    
    def _log_query(self, query: str, k: int):
        """
        Log query for analytics.
        
        Args:
            query: Search query
            k: Number of results requested
        """
        log_entry = {
            "query": query,
            "k": k,
            "timestamp": datetime.now().isoformat()
        }
        
        self.query_log.append(log_entry)
        
        # Limit log size
        if len(self.query_log) > self.max_log_size:
            self.query_log = self.query_log[-self.max_log_size:]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """
        Get query statistics.
        
        Returns:
            Dictionary with query statistics
        """
        return {
            "total_queries": len(self.query_log),
            "recent_queries": self.query_log[-10:] if self.query_log else []
        }
    
    def _expand_query_semantically(self, query: str) -> str:
        """
        Expand query with semantic synonyms and related terms.
        
        Args:
            query: Original query
        
        Returns:
            Expanded query with synonyms
        """
        # Common semantic expansions for software engineering terms
        expansions = {
            "auth": ["authentication", "authorization", "login", "security", "oauth", "jwt"],
            "user": ["account", "profile", "customer", "member"],
            "database": ["db", "storage", "persistence", "repository", "data store"],
            "api": ["endpoint", "route", "service", "rest", "graphql"],
            "ui": ["interface", "frontend", "view", "screen", "component"],
            "function": ["method", "procedure", "routine", "operation"],
            "error": ["exception", "failure", "bug", "issue"],
            "test": ["testing", "spec", "unit test", "integration test"],
            "model": ["entity", "schema", "class", "dto", "object"],
            "controller": ["handler", "manager", "service"],
        }
        
        query_lower = query.lower()
        expanded_terms = []
        
        for term, synonyms in expansions.items():
            if term in query_lower:
                # Add top 2 most relevant synonyms
                expanded_terms.extend(synonyms[:2])
        
        if expanded_terms:
            return f"{query} {' '.join(expanded_terms[:4])}"  # Add max 4 expanded terms
        
        return query
    
    def _enhance_query_for_artifact(self, query: str, artifact_type: Optional[str] = None) -> str:
        """
        Enhance query with artifact-specific keywords and semantic expansion.
        
        Args:
            query: Original query
            artifact_type: Artifact type (e.g., "mermaid_erd", "code_prototype")
        
        Returns:
            Enhanced query string
        """
        if not artifact_type:
            # Still apply semantic expansion
            return self._expand_query_semantically(query)
        
        # Artifact-specific keywords to boost relevant code
        artifact_keywords = {
            # Diagram types - look for structure, relationships, entities
            "mermaid_erd": ["entity", "relationship", "table", "schema", "database", "model", "class", "field", "column", "primary key", "foreign key"],
            "mermaid_architecture": ["architecture", "component", "service", "module", "system", "design", "structure", "layer", "tier"],
            "mermaid_sequence": ["sequence", "flow", "interaction", "call", "method", "function", "api", "request", "response"],
            "mermaid_class": ["class", "interface", "method", "property", "attribute", "inheritance", "composition", "aggregation"],
            "mermaid_state": ["state", "transition", "machine", "flow", "condition", "event", "action"],
            "mermaid_flowchart": ["flow", "process", "decision", "algorithm", "logic", "step", "workflow"],
            "mermaid_data_flow": ["data", "flow", "transform", "process", "input", "output", "pipeline", "stream"],
            "mermaid_user_flow": ["user", "flow", "journey", "interaction", "ui", "screen", "page", "navigation"],
            "mermaid_component": ["component", "module", "interface", "props", "state", "render", "react", "vue"],
            "mermaid_api_sequence": ["api", "endpoint", "request", "response", "http", "rest", "graphql", "route"],
            "mermaid_uml": ["uml", "diagram", "class", "interface", "package", "relationship"],
            
            # HTML diagrams - similar but focus on visual representation
            "html_erd": ["entity", "relationship", "table", "schema", "database", "visual", "diagram"],
            "html_architecture": ["architecture", "component", "visual", "diagram", "system"],
            "html_sequence": ["sequence", "interaction", "visual", "diagram"],
            "html_class": ["class", "interface", "visual", "diagram"],
            "html_state": ["state", "machine", "visual", "diagram"],
            "html_flowchart": ["flow", "process", "visual", "diagram"],
            "html_data_flow": ["data", "flow", "visual", "diagram"],
            "html_user_flow": ["user", "flow", "journey", "visual", "diagram"],
            "html_component": ["component", "visual", "diagram"],
            "html_api_sequence": ["api", "endpoint", "visual", "diagram"],
            "html_uml": ["uml", "visual", "diagram"],
            
            # Code artifacts - look for implementation, functions, classes
            "code_prototype": ["function", "class", "implementation", "code", "prototype", "example", "snippet", "method", "def", "return"],
            "dev_visual_prototype": ["ui", "component", "interface", "visual", "prototype", "design", "layout", "css", "html", "react", "vue"],
            "api_docs": ["api", "endpoint", "route", "method", "request", "response", "parameter", "documentation", "swagger", "openapi"],
            
            # PM artifacts - look for requirements, features, tasks
            "jira": ["task", "story", "feature", "requirement", "acceptance", "criteria", "epic", "sprint"],
            "workflows": ["workflow", "process", "step", "task", "action", "state", "transition"],
            "backlog": ["backlog", "feature", "requirement", "priority", "story", "task"],
            "personas": ["user", "persona", "character", "profile", "demographic", "behavior"],
            "estimations": ["estimate", "effort", "time", "complexity", "story point", "hour", "day"],
            "feature_scoring": ["feature", "score", "priority", "value", "impact", "effort", "matrix"]
        }
        
        keywords = artifact_keywords.get(artifact_type, [])
        
        # First, apply semantic expansion
        expanded_query = self._expand_query_semantically(query)
        
        if keywords:
            # Add artifact-specific keywords to boost relevant results
            enhanced = f"{expanded_query} {' '.join(keywords[:5])}"  # Add top 5 keywords
            logger.debug(f"Enhanced query for {artifact_type}: {enhanced[:100]}")
            return enhanced
        
        return expanded_query
    
    async def retrieve(
        self,
        query: str,
        k: int = 18,
        artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant code snippets using hybrid search.
        
        Args:
            query: Search query
            k: Number of results
            artifact_type: Optional artifact type for targeted retrieval
        
        Returns:
            List of snippet dictionaries with content, metadata, and score
        """
        # Run hybrid search in thread pool to avoid blocking
        import asyncio
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.hybrid_search(
                query=query,
                k_final=k,
                artifact_type=artifact_type
            )
        )
        
        snippets = []
        for doc, score in results:
            snippets.append({
                "content": doc.get("content", ""),
                "metadata": doc.get("meta", {}),
                "score": score
            })
        
        return snippets
    
    def invalidate_cache(self):
        """Invalidate BM25 cache (force reload on next search)."""
        self._bm25_index = None
        self._docs_cache = None
        logger.info("BM25 cache invalidated")


# Global retriever instance
_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    """Get or create global RAG retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever

