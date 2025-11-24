"""
RAG API endpoints for ingestion and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pathlib import Path
from typing import Optional
from backend.models.dto import SnippetDTO, ContextBuildResponse, ContextBuildRequest
from backend.services.rag_ingester import get_ingester
from backend.services.rag_retriever import get_retriever
from backend.services.rag_cache import get_cache
from backend.core.middleware import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/index", response_model=dict)
@limiter.limit("5/minute")
async def index_directory(
    request: Request,
    body: dict,
    background_tasks: BackgroundTasks
):
    """
    Index a directory for RAG.
    
    Request body:
    {
        "directory": "/path/to/directory",
        "recursive": true
    }
    """
    directory = Path(body.get("directory", "."))
    recursive = body.get("recursive", True)
    
    if not directory.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {directory}"
        )
    
    ingester = get_ingester()
    
    # Index in background
    background_tasks.add_task(ingester.index_directory, directory, recursive)
    
    return {
        "message": "Indexing started",
        "directory": str(directory),
        "recursive": recursive
    }


@router.get("/index/stats", response_model=dict)
async def get_index_stats():
    """Get RAG index statistics."""
    ingester = get_ingester()
    stats = ingester.get_index_stats()
    return {
        "success": True,
        "stats": stats
    }


@router.get("/status", response_model=dict)
async def get_rag_status():
    """
    Get RAG system status including auto-refresh status.
    
    Returns:
        Status information including:
        - is_watching: Whether file watcher is active
        - watched_directories: List of directories being watched
        - index_stats: Index statistics
        - last_refresh: Last refresh time (if available)
    """
    ingester = get_ingester()
    stats = ingester.get_index_stats()
    
    return {
        "success": True,
        "is_watching": len(ingester.watched_directories) > 0,
        "watched_directories": [str(d) for d in ingester.watched_directories],
        "index_stats": stats,
        "auto_refresh_enabled": len(ingester.watched_directories) > 0,
        "message": f"RAG auto-refresh is {'active' if ingester.watched_directories else 'inactive'}"
    }


@router.post("/refresh", response_model=dict)
async def manual_refresh(
    request: Optional[dict] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Manually trigger RAG refresh for a directory.
    
    Request body (optional):
    {
        "directory": "/path/to/directory",  # If not provided, refreshes all watched directories
        "force": false  # Force full reindex even if files haven't changed
    }
    """
    ingester = get_ingester()
    
    if request and "directory" in request:
        directory = Path(request["directory"])
        if not directory.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {directory}"
            )
        
        # Index in background
        background_tasks.add_task(ingester.index_directory, directory, True)
        return {
            "success": True,
            "message": f"Manual refresh started for {directory}",
            "directory": str(directory)
        }
    else:
        # Refresh all watched directories
        if not ingester.watched_directories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No directories are being watched. Use /api/rag/watch to start watching."
            )
        
        for directory in ingester.watched_directories:
            background_tasks.add_task(ingester.index_directory, directory, True)
        
        return {
            "success": True,
            "message": f"Manual refresh started for {len(ingester.watched_directories)} directories",
            "directories": [str(d) for d in ingester.watched_directories]
        }
    ingester = get_ingester()
    return ingester.get_index_stats()


@router.post("/search", response_model=dict)
@limiter.limit("30/minute")
async def search_rag(
    request: Request,
    body: dict
):
    """
    Search RAG index.
    
    Request body:
    {
        "query": "user authentication",
        "k": 18,
        "use_cache": true
    }
    """
    query = body.get("query", "")
    k = body.get("k", 18)
    use_cache = body.get("use_cache", True)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query is required"
        )
    
    retriever = get_retriever()
    cache = get_cache()
    
    # Check cache
    if use_cache:
        cached = cache.get_context(query)
        if cached:
            return {
                "results": cached,
                "from_cache": True,
                "num_results": len(cached.split("---"))
            }
    
    # Perform hybrid search
    results = retriever.hybrid_search(query, k_final=k)
    
    # Format results
    snippets = []
    for doc, score in results:
        snippets.append(SnippetDTO(
            content=doc.get("content", ""),
            source_file=doc.get("meta", {}).get("file_path", ""),
            line_start=doc.get("meta", {}).get("start_line"),
            line_end=doc.get("meta", {}).get("end_line"),
            similarity_score=score,
            metadata=doc.get("meta", {})
        ))
    
    # Cache results
    if use_cache:
        context = "\n---\n".join([s.content for s in snippets])
        cache.set_context(query, context)
    
    return {
        "results": [s.model_dump() for s in snippets],
        "from_cache": False,
        "num_results": len(snippets)
    }


@router.post("/watch", response_model=dict)
async def start_watching(request: dict):
    """
    Start watching a directory for file changes.
    
    Request body:
    {
        "directory": "/path/to/directory"
    }
    """
    directory = Path(request.get("directory", "."))
    
    if not directory.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {directory}"
        )
    
    ingester = get_ingester()
    ingester.start_watching(directory)
    
    return {
        "message": "Watching started",
        "directory": str(directory)
    }


@router.post("/watch/stop", response_model=dict)
async def stop_watching():
    """Stop watching directories."""
    ingester = get_ingester()
    ingester.stop_watching()
    
    return {"message": "Watching stopped"}


@router.post("/cache/invalidate", response_model=dict)
async def invalidate_cache(request: dict):
    """
    Invalidate RAG cache.
    
    Request body:
    {
        "meeting_notes": "optional specific notes to invalidate"
    }
    """
    meeting_notes = request.get("meeting_notes")
    cache = get_cache()
    count = cache.invalidate(meeting_notes)
    
    return {
        "message": "Cache invalidated",
        "entries_invalidated": count
    }


@router.get("/cache/stats", response_model=dict)
async def get_cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    return cache.get_cache_stats()


@router.get("/query/stats", response_model=dict)
async def get_query_stats():
    """Get query statistics."""
    retriever = get_retriever()
    return retriever.get_query_stats()



