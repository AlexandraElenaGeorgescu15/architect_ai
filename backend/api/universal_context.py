"""
Universal Context API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from typing import Optional, Dict, Any
import logging

from backend.services.universal_context import get_universal_context_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/universal-context", tags=["Universal Context"])


@router.get("/status")
async def get_universal_context_status(request: Request) -> Dict[str, Any]:
    """
    Get status of the Universal Context.
    
    Returns:
        Universal context status and statistics
    """
    try:
        service = get_universal_context_service()
        universal_ctx = await service.get_universal_context()
        
        return {
            "status": "available",
            "built_at": universal_ctx.get("built_at"),
            "project_directories": universal_ctx.get("project_directories", []),
            "total_files": universal_ctx.get("total_files", 0),
            "kg_nodes": universal_ctx.get("knowledge_graph", {}).get("total_nodes", 0),
            "kg_edges": universal_ctx.get("knowledge_graph", {}).get("total_edges", 0),
            "patterns_found": universal_ctx.get("patterns", {}).get("total_patterns", 0),
            "key_entities_count": len(universal_ctx.get("key_entities", [])),
            "build_duration_seconds": universal_ctx.get("build_duration_seconds", 0)
        }
    except Exception as e:
        logger.error(f"Error getting universal context status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_universal_context(request: Request) -> Dict[str, Any]:
    """
    Get the complete Universal Context.
    
    Returns:
        Complete universal context with project knowledge
    """
    try:
        service = get_universal_context_service()
        return await service.get_universal_context()
    except Exception as e:
        logger.error(f"Error getting universal context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild")
async def rebuild_universal_context(
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = True
) -> Dict[str, str]:
    """
    Rebuild the Universal Context.
    
    Args:
        force: Force rebuild even if cache is fresh (default: True)
    
    Returns:
        Status message
    """
    try:
        service = get_universal_context_service()
        
        # Run rebuild in background
        async def rebuild_task():
            try:
                logger.info("🔨 Background rebuild of Universal Context started")
                await service.build_universal_context(force_rebuild=force)
                logger.info("✅ Background rebuild of Universal Context completed")
            except Exception as e:
                logger.error(f"Error in background rebuild: {e}", exc_info=True)
        
        background_tasks.add_task(rebuild_task)
        
        return {
            "status": "rebuilding",
            "message": "Universal Context rebuild started in background. Check status endpoint for progress."
        }
    except Exception as e:
        logger.error(f"Error triggering universal context rebuild: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/key-entities")
async def get_key_entities(request: Request, limit: int = 50) -> Dict[str, Any]:
    """
    Get key entities from the Universal Context.
    
    Args:
        limit: Maximum number of entities to return (default: 50)
    
    Returns:
        List of key entities
    """
    try:
        service = get_universal_context_service()
        universal_ctx = await service.get_universal_context()
        
        key_entities = universal_ctx.get("key_entities", [])[:limit]
        
        return {
            "total_entities": len(universal_ctx.get("key_entities", [])),
            "entities": key_entities,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting key entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project-map")
async def get_project_map(request: Request) -> Dict[str, Any]:
    """
    Get the project structure map from Universal Context.
    
    Returns:
        Project structure map
    """
    try:
        service = get_universal_context_service()
        universal_ctx = await service.get_universal_context()
        
        return universal_ctx.get("project_map", {})
    except Exception as e:
        logger.error(f"Error getting project map: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/importance-scores")
async def get_importance_scores(
    request: Request,
    min_importance: float = 0.7,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get file importance scores.
    
    Args:
        min_importance: Minimum importance score to include (0.0 to 1.0)
        limit: Maximum number of files to return
    
    Returns:
        List of files with importance scores
    """
    try:
        service = get_universal_context_service()
        universal_ctx = await service.get_universal_context()
        
        importance_scores = universal_ctx.get("importance_scores", {})
        
        # Filter and sort by importance
        filtered_scores = [
            {"file": file, "importance": score}
            for file, score in importance_scores.items()
            if score >= min_importance
        ]
        filtered_scores.sort(key=lambda x: x["importance"], reverse=True)
        
        return {
            "total_files": len(importance_scores),
            "filtered_count": len(filtered_scores),
            "min_importance": min_importance,
            "files": filtered_scores[:limit]
        }
    except Exception as e:
        logger.error(f"Error getting importance scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

