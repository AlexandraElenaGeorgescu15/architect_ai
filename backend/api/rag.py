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
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


def _get_target_directory(provided_path: Optional[str] = None) -> Path:
    """
    Get the target directory for RAG indexing.
    IMPORTANT: This should NEVER return the Architect.AI tool directory.
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    if provided_path:
        provided = Path(provided_path)
        if provided.exists():
            return provided
    
    if settings.target_repo_path:
        target = Path(settings.target_repo_path)
        if target.exists():
            return target
    
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    if user_dirs:
        # Score directories (same logic as other APIs)
        scored_dirs = []
        for d in user_dirs:
            if d == tool_dir or not d.exists():
                continue
            score = 0
            name_lower = d.name.lower()
            if name_lower in ['agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs']:
                score -= 100
            if (d / 'package.json').exists():
                score += 50
            if (d / 'angular.json').exists():
                score += 60
            if (d / 'src').is_dir():
                score += 30
            if 'project' in name_lower or 'final' in name_lower:
                score += 25
            scored_dirs.append((d, score))
        
        if scored_dirs:
            scored_dirs.sort(key=lambda x: x[1], reverse=True)
            return scored_dirs[0][0]
    
    if tool_dir:
        return tool_dir.parent
    
    return Path.cwd()


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
        "directory": "/path/to/directory",  (optional - defaults to user project)
        "recursive": true
    }
    """
    directory = _get_target_directory(body.get("directory"))
    recursive = body.get("recursive", True)
    logger.info(f"🔍 [RAG] Indexing directory: {directory}")
    
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


@router.post("/reindex-user-projects", response_model=dict)
@limiter.limit("2/minute")
async def reindex_user_projects(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Re-index ALL user project directories (excludes Architect.AI).
    
    This endpoint:
    1. Clears the existing RAG index
    2. Re-indexes ONLY user project directories (frontend, backend, etc.)
    3. Excludes Architect.AI tool files
    
    Use this when the index contains wrong files or hasn't picked up your projects.
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    from backend.services.universal_context import get_universal_context_service
    
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    if not user_dirs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user project directories found. Make sure your projects are in the same parent folder as Architect.AI."
        )
    
    ingester = get_ingester()
    
    # Background task to clear and reindex
    async def reindex_task():
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"🔄 [RAG] Starting full reindex of {len(user_dirs)} user project directories...")
            
            # Step 1: Clear existing index
            logger.info("🗑️ [RAG] Clearing existing index...")
            try:
                ingester.clear_index()
                logger.info("✅ [RAG] Index cleared")
            except Exception as e:
                logger.warning(f"Could not clear index (may not exist): {e}")
            
            # Step 2: Index each user project
            for i, directory in enumerate(user_dirs, 1):
                if directory == tool_dir:
                    logger.info(f"⏭️ [RAG] Skipping tool directory: {directory.name}")
                    continue
                    
                logger.info(f"📂 [RAG] Indexing [{i}/{len(user_dirs)}] {directory.name}...")
                try:
                    await ingester.index_directory(directory, recursive=True)
                    logger.info(f"✅ [RAG] Indexed {directory.name}")
                except Exception as e:
                    logger.error(f"❌ [RAG] Failed to index {directory.name}: {e}")
            
            # Step 3: Rebuild universal context
            logger.info("🔨 [RAG] Rebuilding Universal Context...")
            uc_service = get_universal_context_service()
            await uc_service.build_universal_context(force_rebuild=True)
            
            logger.info(f"✅ [RAG] Reindex complete! Indexed {len(user_dirs)} directories.")
            
        except Exception as e:
            logger.error(f"❌ [RAG] Reindex failed: {e}", exc_info=True)
    
    background_tasks.add_task(reindex_task)
    
    return {
        "success": True,
        "message": f"Reindexing started for {len(user_dirs)} user project(s)",
        "directories": [d.name for d in user_dirs],
        "excluded": tool_dir.name if tool_dir else None
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
            # Reconstruct snippets from cached string to maintain API consistency (List[dict])
            # Cache stores snippets joined by "\n---\n"
            raw_snippets = cached.split("\n---\n")
            cached_results = []
            for s in raw_snippets:
                if s.strip():
                    cached_results.append({
                        "content": s,
                        "source_file": "cached",
                        "similarity_score": 1.0,
                        "metadata": {"cached": True}
                    })
            
            return {
                "results": cached_results,
                "from_cache": True,
                "num_results": len(cached_results)
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



