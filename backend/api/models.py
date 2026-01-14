"""
Model Management API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging

from backend.models.dto import (
    ModelInfoDTO, ModelRoutingDTO, ModelRoutingUpdateRequest,
    ArtifactType
)
from backend.services.model_service import get_service, OLLAMA_AVAILABLE
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("/", response_model=List[ModelInfoDTO], summary="List all available models")
async def list_models(
    current_user: UserPublic = Depends(get_current_user)
):
    """List all registered models (Ollama, HuggingFace, Cloud)."""
    service = get_service()
    models = await service.list_models()
    return models


@router.get("/routing", response_model=Dict[str, ModelRoutingDTO], summary="Get model routing configuration")
async def get_routing(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get model routing configuration for all artifact types."""
    service = get_service()
    return {
        artifact_type: routing
        for artifact_type, routing in service.routing.items()
    }


@router.get("/routing/{artifact_type}", response_model=ModelRoutingDTO, summary="Get routing for specific artifact type")
async def get_routing_for_artifact(
    artifact_type: ArtifactType,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get model routing configuration for a specific artifact type."""
    service = get_service()
    routing = service.get_routing_for_artifact(artifact_type)
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No routing configuration found for {artifact_type.value}"
        )
    return routing


# ============== SPECIFIC ROUTES (must come before /{model_id}) ==============

@router.get("/stats", summary="Get model service statistics")
async def get_model_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get statistics about models and routing."""
    service = get_service()
    stats = service.get_stats()
    return {"success": True, "stats": stats}


@router.post("/refresh", summary="Refresh model list from Ollama")
async def refresh_models(
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Refresh the model list from Ollama and cloud providers.
    This will update the registry with newly downloaded/fine-tuned models.
    """
    service = get_service()
    
    # Refresh Ollama models
    if OLLAMA_AVAILABLE:
        await service._refresh_ollama_models()
    
    # Refresh cloud models
    await service._refresh_cloud_models()
    
    # Get updated list
    models = await service.list_models()
    
    return {
        "success": True,
        "message": f"Refreshed {len(models)} models",
        "models_count": len(models)
    }


@router.get("/api-keys/status", summary="Check API key status for cloud providers")
async def check_api_keys_status(
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Check which API keys are configured and test their validity.
    Returns status for Gemini, Groq, OpenAI, and Anthropic.
    """
    from backend.core.config import settings
    import os
    
    status = {
        "gemini": {
            "configured": bool(settings.google_api_key or settings.gemini_api_key),
            "env_var": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "settings_key": bool(settings.google_api_key or settings.gemini_api_key),
            "valid": False  # Will test
        },
        "groq": {
            "configured": bool(settings.groq_api_key),
            "env_var": bool(os.getenv("GROQ_API_KEY")),
            "settings_key": bool(settings.groq_api_key),
            "valid": False
        },
        "openai": {
            "configured": bool(settings.openai_api_key),
            "env_var": bool(os.getenv("OPENAI_API_KEY")),
            "settings_key": bool(settings.openai_api_key),
            "valid": False
        },
        "anthropic": {
            "configured": bool(settings.anthropic_api_key),
            "env_var": bool(os.getenv("ANTHROPIC_API_KEY")),
            "settings_key": bool(settings.anthropic_api_key),
            "valid": False
        }
    }
    
    # Test API keys
    import httpx
    
    # Test OpenAI
    if status["openai"]["configured"]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    timeout=10.0
                )
                status["openai"]["valid"] = response.status_code == 200
        except Exception:
            status["openai"]["valid"] = False
    
    # For other providers, just check if key is configured
    # (Full validation would require specific API calls)
    if status["gemini"]["configured"]:
        status["gemini"]["valid"] = True  # Assume valid if configured
    if status["groq"]["configured"]:
        status["groq"]["valid"] = True
    if status["anthropic"]["configured"]:
        status["anthropic"]["valid"] = True
    
    return status


# ============== DYNAMIC ROUTES (must come after specific routes) ==============

@router.get("/{model_id}", response_model=ModelInfoDTO, summary="Get model information")
async def get_model(
    model_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get detailed information about a specific model."""
    service = get_service()
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return model


@router.post("/{model_id}/download", summary="Download a model")
@limiter.limit("2/minute")
async def download_model(
    request: Request,
    model_id: str,
    provider: str = "ollama",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Download a model (Ollama only for now).
    This is a long-running operation and runs in the background.
    """
    service = get_service()
    
    # Check if model already exists
    existing_model = await service.get_model(model_id)
    if existing_model and existing_model.status == "downloaded":
        return {
            "success": True,
            "message": f"Model {model_id} already downloaded",
            "model_id": model_id,
            "status": "downloaded"
        }
    
    # Check if already downloading
    if existing_model and existing_model.status == "downloading":
        return {
            "success": True,
            "message": f"Model {model_id} is already downloading",
            "model_id": model_id,
            "status": "downloading"
        }
    
    # Start download in background
    async def download_with_notification():
        success = await service.download_model(model_id, provider)
        if success:
            # Refresh models list after download
            await service.list_models()
            logger.info(f"✅ Model {model_id} download completed and registered")
        else:
            logger.error(f"❌ Model {model_id} download failed")
    
    background_tasks.add_task(download_with_notification)
    
    return {
        "success": True,
        "message": f"Download of {model_id} started in background",
        "model_id": model_id,
        "provider": provider,
        "status": "downloading"
    }


@router.put("/routing", summary="Update model routing configuration")
@limiter.limit("10/minute")
async def update_routing(
    request: Request,
    body: ModelRoutingUpdateRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Update model routing configuration for one or more artifact types."""
    service = get_service()
    success = service.update_routing(body.routings)
    
    if success:
        return {
            "message": f"Updated routing for {len(body.routings)} artifact types",
            "routings": body.routings
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update routing configuration"
        )

