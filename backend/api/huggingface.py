"""
HuggingFace API endpoints for model search and download.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from backend.services.huggingface_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/huggingface", tags=["HuggingFace"])


class DownloadRequest(BaseModel):
    """Request body for model download."""
    convert_to_ollama: bool = True


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


@router.post("/download/{model_id:path}", summary="Download a model from HuggingFace")
@limiter.limit("2/minute")
async def download_model(
    request: Request,
    model_id: str,
    background_tasks: BackgroundTasks,
    body: Optional[DownloadRequest] = Body(default=None),
    convert_to_ollama_query: Optional[bool] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Download a model from HuggingFace Hub.
    
    This is a long-running operation and runs in the background.
    
    Args:
        model_id: HuggingFace model ID (e.g., "codellama/CodeLlama-7b-Instruct-hf")
        convert_to_ollama: Whether to convert to Ollama format after download (body or query param)
    
    Returns:
        Download status
    """
    # Support both body and query param for convert_to_ollama
    # Priority: body > query param > default (True)
    if body is not None and body.convert_to_ollama is not None:
        convert_to_ollama = body.convert_to_ollama
    elif convert_to_ollama_query is not None:
        convert_to_ollama = convert_to_ollama_query
    else:
        convert_to_ollama = True
    
    logger.info(f"📥 [HF_DOWNLOAD] Download request for {model_id}, convert_to_ollama={convert_to_ollama}")
    
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
    def download_with_error_handling():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"🚀 [HF_DOWNLOAD] Background download started for {model_id}")
            result = loop.run_until_complete(service.download_model(model_id, convert_to_ollama))
            if not result.get("success"):
                logger.error(f"❌ [HF_DOWNLOAD] Download failed for {model_id}: {result.get('error')}")
            else:
                logger.info(f"✅ [HF_DOWNLOAD] Download completed for {model_id}: {result.get('message')}")
        except Exception as e:
            logger.error(f"❌ [HF_DOWNLOAD] Background download error for {model_id}: {e}", exc_info=True)
            service.active_downloads[model_id] = {
                "status": "failed",
                "error": str(e),
                "progress": 0.0
            }
        finally:
            loop.close()
    
    background_tasks.add_task(download_with_error_handling)
    logger.info(f"📥 [HF_DOWNLOAD] Download task queued for {model_id}")
    
    return {
        "success": True,
        "message": f"Download of {model_id} started in background",
        "model_id": model_id,
        "convert_to_ollama": convert_to_ollama
    }


@router.get("/download/{model_id:path}/status", summary="Get download status")
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


@router.get("/info/{model_id:path}", summary="Get model information")
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

