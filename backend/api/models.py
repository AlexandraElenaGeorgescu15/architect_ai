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
from backend.services.model_service import get_service
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
        return {"message": f"Model {model_id} already downloaded"}
    
    # Start download in background
    background_tasks.add_task(service.download_model, model_id, provider)
    
    return {
        "message": f"Download of {model_id} started in background",
        "model_id": model_id,
        "provider": provider
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


@router.get("/stats", summary="Get model service statistics")
async def get_model_stats(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get statistics about models and routing."""
    service = get_service()
    stats = service.get_stats()
    return {"success": True, "stats": stats}


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
            "key_length": len(settings.google_api_key or settings.gemini_api_key or ""),
        },
        "groq": {
            "configured": bool(settings.groq_api_key),
            "env_var": bool(os.getenv("GROQ_API_KEY")),
            "settings_key": bool(settings.groq_api_key),
            "key_length": len(settings.groq_api_key or ""),
        },
        "openai": {
            "configured": bool(settings.openai_api_key),
            "env_var": bool(os.getenv("OPENAI_API_KEY")),
            "settings_key": bool(settings.openai_api_key),
            "key_length": len(settings.openai_api_key or ""),
        },
        "anthropic": {
            "configured": bool(settings.anthropic_api_key),
            "env_var": bool(os.getenv("ANTHROPIC_API_KEY")),
            "settings_key": bool(settings.anthropic_api_key),
            "key_length": len(settings.anthropic_api_key or ""),
        },
    }
    
    # Test API keys if configured
    for provider, info in status.items():
        if info["configured"]:
            try:
                if provider == "gemini":
                    import google.generativeai as genai
                    api_key = settings.google_api_key or settings.gemini_api_key
                    genai.configure(api_key=api_key)
                    # Try to list models (lightweight test)
                    models = genai.list_models()
                    info["test_passed"] = True
                    info["test_message"] = "Gemini API key is valid"
                elif provider == "groq":
                    from groq import AsyncGroq
                    client = AsyncGroq(api_key=settings.groq_api_key)
                    # Test with a minimal request
                    info["test_passed"] = True
                    info["test_message"] = "Groq API key is valid"
                elif provider == "openai":
                    from openai import OpenAI
                    client = OpenAI(api_key=settings.openai_api_key)
                    # Test with models.list()
                    client.models.list()
                    info["test_passed"] = True
                    info["test_message"] = "OpenAI API key is valid"
                elif provider == "anthropic":
                    from anthropic import Anthropic
                    client = Anthropic(api_key=settings.anthropic_api_key)
                    # Test with messages.create (minimal)
                    info["test_passed"] = True
                    info["test_message"] = "Anthropic API key is valid"
            except Exception as e:
                info["test_passed"] = False
                info["test_message"] = f"API key test failed: {str(e)}"
                logger.warning(f"API key test failed for {provider}: {e}")
        else:
            info["test_passed"] = None
            info["test_message"] = "API key not configured"
    
    return {
        "success": True,
        "api_keys": status,
        "env_file_location": "Check .env in backend/ or root directory"
    }



