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
    """Get model routing configuration for a specific artifact type (built-in types)."""
    service = get_service()
    routing = service.get_routing_for_artifact(artifact_type)
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No routing configuration found for {artifact_type.value}"
        )
    return routing


@router.get("/routing/custom/{type_id}", response_model=ModelRoutingDTO, summary="Get routing for custom artifact type")
async def get_routing_for_custom_artifact(
    type_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get model routing configuration for a custom artifact type by ID.
    
    This endpoint supports custom artifact types that are not in the built-in enum.
    If no routing exists for the custom type, creates a default one.
    """
    service = get_service()
    routing = service.get_routing_for_custom_artifact(type_id)
    
    if not routing:
        # Create default routing for the custom type
        routing = service.create_routing_for_custom_type(type_id)
    
    return routing


@router.put("/routing/custom/{type_id}", response_model=ModelRoutingDTO, summary="Update routing for custom artifact type")
@limiter.limit("10/minute")
async def update_routing_for_custom_artifact(
    request: Request,
    type_id: str,
    primary_model: str,
    fallback_models: List[str] = [],
    enabled: bool = True,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Update model routing configuration for a custom artifact type.
    
    Args:
        type_id: Custom artifact type ID
        primary_model: Primary model to use (e.g., "ollama:llama3:latest")
        fallback_models: List of fallback models
        enabled: Whether the routing is enabled
    """
    service = get_service()
    
    routing = ModelRoutingDTO(
        artifact_type=type_id,
        primary_model=primary_model,
        fallback_models=fallback_models,
        enabled=enabled
    )
    
    service.routing[type_id] = routing
    service._save_routing()
    
    return routing


@router.post("/suggest-routing", summary="Get AI-powered model routing suggestions")
@limiter.limit("10/minute")
async def suggest_routing(
    request: Request,
    artifact_type: ArtifactType,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get AI-powered model routing suggestions for an artifact type.
    
    Uses a fast LLM to analyze the artifact type's characteristics and 
    recommend the best models based on their capabilities.
    
    Returns:
        - suggested_primary: Recommended primary model
        - suggested_fallbacks: List of recommended fallback models
        - reasoning: AI's explanation for the recommendations
        - confidence: Confidence score (0-1)
    """
    from backend.core.config import settings
    import httpx
    
    service = get_service()
    
    # Get available models
    models = await service.list_models()
    available_models = [
        {"id": m.id, "name": m.name, "provider": m.provider}
        for m in models
        if m.status in ["available", "downloaded"]
    ]
    
    if not available_models:
        return {
            "success": False,
            "error": "No models available",
            "suggested_primary": None,
            "suggested_fallbacks": [],
            "reasoning": "No models are currently available. Please ensure Ollama is running or API keys are configured.",
            "confidence": 0.0
        }
    
    # Build prompt for AI suggestion
    artifact_info = {
        "mermaid_erd": "Entity Relationship Diagrams - database schema visualization",
        "mermaid_architecture": "System architecture diagrams - high-level component relationships",
        "mermaid_sequence": "Sequence diagrams - API/method call flows",
        "mermaid_class": "Class diagrams - OOP structure visualization",
        "mermaid_flowchart": "Flowcharts - process/decision flows",
        "mermaid_state": "State diagrams - state machine visualization",
        "code_prototype": "Code generation - working code prototypes",
        "dev_visual_prototype": "HTML prototypes - interactive UI mockups",
        "api_docs": "API documentation - endpoint documentation",
        "jira": "JIRA tickets - user stories and tasks",
        "workflows": "Workflow definitions - process workflows",
        "backlog": "Product backlog - prioritized features",
    }
    
    artifact_description = artifact_info.get(
        artifact_type.value, 
        f"{artifact_type.value} - software development artifact"
    )
    
    models_list = "\n".join([
        f"- {m['id']} ({m['provider']})" for m in available_models[:15]
    ])
    
    prompt = f"""You are an expert at matching AI models to software development tasks.

ARTIFACT TYPE: {artifact_type.value}
DESCRIPTION: {artifact_description}

AVAILABLE MODELS:
{models_list}

Based on the artifact type, suggest the best model configuration:

1. PRIMARY MODEL: The model best suited for this artifact type
2. FALLBACK MODELS: 2-3 alternative models in order of preference
3. REASONING: Brief explanation (1-2 sentences) of why these models are best

Guidelines:
- For diagrams/Mermaid: Prefer models good at structured output (mistral, llama3)
- For code: Prefer code-specialized models (codellama, deepseek-coder)
- For documentation/text: Prefer models good at natural language (llama3, mistral)
- Cloud models (gemini, gpt-4) are good fallbacks but prefer local models when available

Respond in this exact JSON format:
{{
    "primary": "model_id",
    "fallbacks": ["model_id_1", "model_id_2"],
    "reasoning": "explanation",
    "confidence": 0.85
}}"""

    # Use Groq for fast response (or fall back to other providers)
    suggestion = None
    
    if settings.groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "You are an AI model routing expert. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()
                    
                    # Parse JSON response
                    import json
                    try:
                        if "{" in content:
                            json_start = content.index("{")
                            json_end = content.rindex("}") + 1
                            suggestion = json.loads(content[json_start:json_end])
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Failed to parse AI suggestion: {e}")
        except Exception as e:
            logger.warning(f"Groq suggestion failed: {e}")
    
    # Fallback: Use heuristic-based suggestion if AI fails
    if not suggestion:
        # Default recommendations based on artifact type
        if artifact_type.value.startswith("mermaid_"):
            primary = next((m["id"] for m in available_models if "mistral" in m["id"].lower()), 
                          next((m["id"] for m in available_models if "llama" in m["id"].lower()), 
                               available_models[0]["id"] if available_models else None))
            fallbacks = [m["id"] for m in available_models 
                        if m["id"] != primary and ("llama" in m["id"].lower() or "gemini" in m["id"].lower())][:2]
            reasoning = "Mistral and Llama models are well-suited for structured Mermaid diagram generation."
        elif artifact_type.value in ["code_prototype", "dev_visual_prototype"]:
            primary = next((m["id"] for m in available_models if "codellama" in m["id"].lower() or "deepseek" in m["id"].lower()), 
                          available_models[0]["id"] if available_models else None)
            fallbacks = [m["id"] for m in available_models 
                        if m["id"] != primary and ("llama" in m["id"].lower() or "gpt" in m["id"].lower())][:2]
            reasoning = "Code-specialized models (CodeLlama, DeepSeek) produce better code output."
        else:
            primary = next((m["id"] for m in available_models if "llama" in m["id"].lower()), 
                          available_models[0]["id"] if available_models else None)
            fallbacks = [m["id"] for m in available_models if m["id"] != primary][:2]
            reasoning = "Llama models provide good general-purpose text generation for documentation and PM artifacts."
        
        suggestion = {
            "primary": primary,
            "fallbacks": fallbacks,
            "reasoning": reasoning,
            "confidence": 0.7
        }
    
    # Validate that suggested models exist in available models
    available_ids = [m["id"] for m in available_models]
    if suggestion["primary"] not in available_ids:
        suggestion["primary"] = available_models[0]["id"] if available_models else None
    suggestion["fallbacks"] = [f for f in suggestion.get("fallbacks", []) if f in available_ids][:3]
    
    return {
        "success": True,
        "artifact_type": artifact_type.value,
        "suggested_primary": suggestion.get("primary"),
        "suggested_fallbacks": suggestion.get("fallbacks", []),
        "reasoning": suggestion.get("reasoning", ""),
        "confidence": suggestion.get("confidence", 0.5)
    }


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

