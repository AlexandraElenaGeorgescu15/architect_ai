"""
HuggingFace API endpoints for model search and download.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging

from backend.services.huggingface_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/huggingface", tags=["HuggingFace"])


@router.get("/search", summary="Search models on HuggingFace")
@limiter.limit("10/minute")
async def search_models(
    request: Request,
    query: str,
    task: Optional[str] = None,
    limit: int = 20,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Search for models on HuggingFace Hub.
    
    Args:
        query: Search query (model name, description, etc.)
        task: Task type filter (e.g., "text-generation", "code-generation")
        limit: Maximum number of results (default: 20)
    
    Returns:
        List of matching models
    """
    service = get_service()
    results = await service.search_models(query=query, task=task, limit=limit)
    return {"success": True, "results": results, "count": len(results)}


@router.post("/download/{model_id}", summary="Download a model from HuggingFace")
@limiter.limit("2/minute")
async def download_model(
    request: Request,
    model_id: str,
    convert_to_ollama: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Download a model from HuggingFace Hub.
    
    This is a long-running operation and runs in the background.
    
    Args:
        model_id: HuggingFace model ID (e.g., "codellama/CodeLlama-7b-Instruct-hf")
        convert_to_ollama: Whether to convert to Ollama format after download
    
    Returns:
        Download status
    """
    service = get_service()
    
    # Check if already downloaded
    downloaded = await service.list_downloaded_models()
    if any(m.get("id") == model_id for m in downloaded):
        return {
            "success": True,
            "message": f"Model {model_id} already downloaded",
            "model_id": model_id
        }
    
    # Check if download is already in progress
    if model_id in service.active_downloads:
        status = service.active_downloads[model_id].get("status")
        if status == "downloading":
            return {
                "success": False,
                "error": f"Download of {model_id} is already in progress",
                "model_id": model_id
            }
    
    # Start download in background with error handling
    async def download_with_error_handling():
        try:
            result = await service.download_model(model_id, convert_to_ollama)
            if not result.get("success"):
                logger.error(f"Download failed for {model_id}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Background download error for {model_id}: {e}", exc_info=True)
            service.active_downloads[model_id] = {
                "status": "failed",
                "error": str(e),
                "progress": 0.0
            }
    
    background_tasks.add_task(download_with_error_handling)
    
    return {
        "success": True,
        "message": f"Download of {model_id} started in background",
        "model_id": model_id,
        "convert_to_ollama": convert_to_ollama
    }


@router.get("/download/{model_id}/status", summary="Get download status")
async def get_download_status(
    model_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get the download status for a model."""
    service = get_service()
    
    # Check if already downloaded
    downloaded = await service.list_downloaded_models()
    if any(m.get("id") == model_id for m in downloaded):
        return {
            "success": True,
            "status": "completed",
            "model_id": model_id,
            "progress": 1.0
        }
    
    # Check active downloads
    if model_id in service.active_downloads:
        return {
            "success": True,
            **service.active_downloads[model_id],
            "model_id": model_id
        }
    
    return {
        "success": True,
        "status": "not_started",
        "model_id": model_id,
        "progress": 0.0
    }


@router.get("/downloaded", summary="List downloaded models")
async def list_downloaded_models(
    current_user: UserPublic = Depends(get_current_user)
):
    """List all models downloaded from HuggingFace."""
    service = get_service()
    models = await service.list_downloaded_models()
    return {"success": True, "models": models, "count": len(models)}


@router.get("/info/{model_id}", summary="Get model information")
async def get_model_info(
    model_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get detailed information about a HuggingFace model."""
    service = get_service()
    info = await service.get_model_info(model_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )
    return {"success": True, "model": info}

