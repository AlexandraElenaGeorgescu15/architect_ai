"""
Semantic Code Search Service

Provides a thin wrapper around the existing RAG retriever so the frontend
can query for relevant code/documentation snippets without triggering the
entire generation pipeline. Results are filtered to avoid tool contamination
and include metadata for quick linking in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from backend.services.rag_retriever import RAGRetriever
from backend.utils.tool_detector import should_exclude_path


@dataclass
class SemanticSnippet:
    """Single search result snippet."""

    content: str
    file_path: str
    score: float
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class SemanticSearchService:
    """Lightweight semantic search built on top of the RAG retriever."""

    def __init__(self):
        self.retriever = RAGRetriever()

    def search(
        self,
        query: str,
        limit: int = 20,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[SemanticSnippet]:
        """
        Perform semantic search across the indexed repository.

        Args:
            query: Natural language or keyword query.
            limit: Maximum number of snippets to return.
            metadata_filter: Optional metadata filter passed to Chroma.

        Returns:
            List of SemanticSnippet objects sorted by score (desc).
        """

        # Use the existing vector search to keep performance consistent
        vector_results = self.retriever.vector_search(
            query=query,
            k=min(limit * 2, 200),
            metadata_filter=metadata_filter,
        )

        snippets: List[SemanticSnippet] = []
        for result, score in vector_results:
            meta = result.get("meta", {})
            path = meta.get("path") or meta.get("file_path", "")

            # Skip any files that live inside the tool itself
            if path and should_exclude_path(path):
                continue

            snippet = SemanticSnippet(
                content=result.get("content", ""),
                file_path=path,
                score=score,
                start_line=meta.get("line_start"),
                end_line=meta.get("line_end"),
                metadata=meta,
            )
            snippets.append(snippet)

            if len(snippets) >= limit:
                break

        return snippets


_semantic_search_service: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> SemanticSearchService:
    """Lazy service accessor so we reuse the retriever instance."""

    global _semantic_search_service  # noqa: PLW0603 - intentional singleton
    if _semantic_search_service is None:
        _semantic_search_service = SemanticSearchService()
    return _semantic_search_service


