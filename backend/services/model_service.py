"""
Model Management Service - Handles model registry, routing, and management.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime, timedelta
import json
import yaml
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import (
    ModelInfoDTO, ModelRoutingDTO, ArtifactType
)

logger = logging.getLogger(__name__)


# =============================================================================
# In-Memory Cache for Model Lists (Performance Fix)
# =============================================================================
class ModelListCache:
    """
    Simple in-memory cache for model list queries.
    
    The /api/models/ endpoint was taking 4-7 seconds because it polls
    Ollama, cloud providers, and HuggingFace on every request.
    This cache reduces that to ~0ms for cached responses.
    """
    
    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize cache with TTL.
        
        Args:
            ttl_seconds: Cache time-to-live (default: 60 seconds)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Optional[List[ModelInfoDTO]] = None
        self._cache_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
    
    def is_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        return datetime.now() - self._cache_time < timedelta(seconds=self.ttl_seconds)
    
    def get(self) -> Optional[List[ModelInfoDTO]]:
        """Get cached model list if valid."""
        if self.is_valid():
            logger.debug(f"📦 [CACHE] Model list cache HIT (age: {(datetime.now() - self._cache_time).seconds}s)")
            return self._cache
        return None
    
    def set(self, models: List[ModelInfoDTO]) -> None:
        """Set cache with model list."""
        self._cache = models
        self._cache_time = datetime.now()
        logger.debug(f"📦 [CACHE] Model list cached ({len(models)} models)")
    
    def invalidate(self) -> None:
        """Invalidate the cache."""
        self._cache = None
        self._cache_time = None
        logger.debug("📦 [CACHE] Model list cache invalidated")


# Global cache instance
_model_list_cache = ModelListCache(ttl_seconds=60)

# Optional imports for Ollama (graceful degradation)
try:
    import httpx
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("httpx not available. Ollama integration disabled.")


def normalize_model_id(model_id: str, default_provider: str = "ollama") -> tuple[str, str]:
    """
    Normalize model ID to a consistent format.
    
    Handles various formats:
    - "llama3" -> ("ollama", "llama3")
    - "ollama:llama3" -> ("ollama", "llama3")
    - "ollama:llama3:latest" -> ("ollama", "llama3:latest")
    - "gemini:gemini-2.5-flash" -> ("gemini", "gemini-2.5-flash")
    
    Args:
        model_id: Model identifier in any format
        default_provider: Default provider if not specified (default: "ollama")
    
    Returns:
        Tuple of (provider, model_name)
    """
    if not model_id:
        return (default_provider, "llama3")
    
    model_id = model_id.strip()
    
    # Check for provider prefix
    known_providers = ["ollama", "gemini", "openai", "anthropic", "groq", "huggingface"]
    
    for provider in known_providers:
        if model_id.startswith(f"{provider}:"):
            # Extract model name after provider prefix
            model_name = model_id[len(provider) + 1:]
            return (provider, model_name)
    
    # No provider prefix - check if it looks like a cloud model
    cloud_model_patterns = {
        "gemini": ["gemini-"],
        "openai": ["gpt-", "davinci", "curie", "babbage", "ada"],
        "anthropic": ["claude-"],
        "groq": ["llama-3.3", "llama-3.1", "mixtral"],
    }
    
    for provider, patterns in cloud_model_patterns.items():
        for pattern in patterns:
            if model_id.lower().startswith(pattern.lower()):
                return (provider, model_id)
    
    # Default to specified provider (usually ollama)
    return (default_provider, model_id)


def get_canonical_model_id(model_id: str, default_provider: str = "ollama") -> str:
    """
    Get canonical model ID in 'provider:model_name' format.
    
    Args:
        model_id: Model identifier in any format
        default_provider: Default provider if not specified
    
    Returns:
        Canonical model ID string
    """
    provider, model_name = normalize_model_id(model_id, default_provider)
    return f"{provider}:{model_name}"


def get_ollama_model_name(model_id: str) -> str:
    """
    Extract just the model name for Ollama API calls (without provider prefix).
    
    Args:
        model_id: Model identifier in any format
    
    Returns:
        Model name without provider prefix
    """
    provider, model_name = normalize_model_id(model_id, "ollama")
    return model_name


class ModelService:
    """
    Model management service for tracking and routing models.
    
    Features:
    - Model registry (Ollama, HuggingFace, Cloud)
    - Model routing configuration
    - Model download/loading
    - VRAM management
    - Model status tracking
    """
    
    def __init__(self):
        """Initialize Model Service."""
        # Use absolute paths relative to project root
        project_root = Path(__file__).parent.parent.parent
        self.registry_file = project_root / "model_registry.json"
        self.routing_file = project_root / "model_routing.yaml"
        
        # In-memory registries
        self.models: Dict[str, ModelInfoDTO] = {}
        self.routing: Dict[str, ModelRoutingDTO] = {}
        
        # Load existing data
        self._load_registry()
        self._load_routing()
        
        logger.info("Model Service initialized")
    
    def _load_registry(self):
        """Load model registry from file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_id, model_data in data.items():
                        self.models[model_id] = ModelInfoDTO(**model_data)
                logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Error loading model registry: {e}")
    
    def _save_registry(self):
        """Save model registry to file."""
        try:
            data = {
                model_id: model.model_dump()
                for model_id, model in self.models.items()
            }
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving model registry: {e}")
    
    def _load_routing(self):
        """Load model routing configuration from file."""
        if self.routing_file.exists():
            try:
                with open(self.routing_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    for artifact_type, routing_data in data.items():
                        try:
                            # Try to parse as built-in ArtifactType enum
                            artifact_type_enum = ArtifactType(artifact_type)
                            self.routing[artifact_type] = ModelRoutingDTO(
                                artifact_type=artifact_type_enum,
                                **routing_data
                            )
                        except ValueError:
                            # Not a built-in type - treat as custom artifact type (string)
                            # Store with string key and string artifact_type
                            self.routing[artifact_type] = ModelRoutingDTO(
                                artifact_type=artifact_type,  # Store as string
                                **routing_data
                            )
                            logger.debug(f"Loaded routing for custom artifact type: {artifact_type}")
                logger.info(f"Loaded routing for {len(self.routing)} artifact types")
            except Exception as e:
                logger.error(f"Error loading routing config: {e}")
        else:
            # Create default routing
            self._create_default_routing()
        
        # After loading routing, check for fine-tuned models and update routing
        # This ensures fine-tuned models are always prioritized
        self._update_routing_with_finetuned_models()
    
    def _save_routing(self):
        """Save model routing configuration to file."""
        try:
            data = {}
            for routing in self.routing.values():
                # Handle both ArtifactType enum and string (custom types)
                if isinstance(routing.artifact_type, ArtifactType):
                    key = routing.artifact_type.value
                else:
                    key = str(routing.artifact_type)
                data[key] = {
                    "primary_model": routing.primary_model,
                    "fallback_models": routing.fallback_models,
                    "enabled": routing.enabled
                }
            with open(self.routing_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Error saving routing config: {e}")
    
    def _update_routing_with_finetuned_models(self):
        """
        Update routing to make fine-tuned models available as fallbacks.
        
        IMPORTANT: This method NO LONGER overwrites user's primary model choice.
        Fine-tuned models are added as high-priority fallbacks instead.
        User's explicit model preferences are always respected.
        """
        try:
            # Load fine-tuned models from registry
            self._load_finetuned_models_from_registry()
            
            # Check each fine-tuned model and update routing
            for model_id, model_info in self.models.items():
                if model_info.is_trained and model_info.provider == "ollama":
                    artifact_type_str = model_info.metadata.get("artifact_type", "")
                    if artifact_type_str:
                        # Find matching ArtifactType enum
                        artifact_type_enum = None
                        for at in ArtifactType:
                            if at.value.lower() == artifact_type_str.lower().replace("-", "_"):
                                artifact_type_enum = at
                                break
                        
                        if artifact_type_enum:
                            # Extract model name
                            model_name = model_id.split(":", 1)[1] if ":" in model_id else model_id
                            finetuned_model_id = f"ollama:{model_name}"
                            
                            # Get or create routing
                            routing = self.get_routing_for_artifact(artifact_type_enum)
                            if not routing:
                                # Create new routing with fine-tuned model as primary
                                # (Only set as primary if NO routing exists - user hasn't configured anything)
                                base_model = model_info.metadata.get("base_model", "llama3")
                                routing = ModelRoutingDTO(
                                    artifact_type=artifact_type_enum,
                                    primary_model=finetuned_model_id,
                                    fallback_models=[f"ollama:{base_model}"],
                                    enabled=True
                                )
                                self.routing[artifact_type_enum.value] = routing
                                logger.info(f"✅ Created routing for {artifact_type_str} with fine-tuned model {model_name}")
                            else:
                                # FIX: Don't overwrite user's primary model choice!
                                # Instead, add fine-tuned model as first fallback if not already there
                                if routing.primary_model != finetuned_model_id:
                                    # Only add to fallbacks, don't touch primary
                                    if finetuned_model_id not in routing.fallback_models:
                                        routing.fallback_models.insert(0, finetuned_model_id)
                                        logger.info(f"✅ Added fine-tuned model {model_name} as fallback for {artifact_type_str} (user's primary preserved: {routing.primary_model})")
        except Exception as e:
            logger.debug(f"Could not update routing with fine-tuned models: {e}")
    
    def _create_default_routing(self):
        """Create default model routing configuration for all artifact types."""
        # Use centralized config for default models (avoids magic strings)
        from backend.core.config import settings
        mermaid_models = settings.default_mermaid_models
        html_models = settings.default_html_models
        code_models = settings.default_code_models
        pm_models = settings.default_pm_models
        
        default_routing = {}
        
        # Mermaid diagrams (Fully Parsable to Canvas - 7 types)
        mermaid_parsable_types = [
            ArtifactType.MERMAID_ERD,
            ArtifactType.MERMAID_ARCHITECTURE,
            ArtifactType.MERMAID_SEQUENCE,
            ArtifactType.MERMAID_CLASS,
            ArtifactType.MERMAID_STATE,
            ArtifactType.MERMAID_FLOWCHART,
            ArtifactType.MERMAID_DATA_FLOW,
            ArtifactType.MERMAID_USER_FLOW,
            ArtifactType.MERMAID_COMPONENT,
            ArtifactType.MERMAID_SYSTEM_OVERVIEW,
            ArtifactType.MERMAID_API_SEQUENCE,
            ArtifactType.MERMAID_UML,
        ]
        
        # Mermaid diagrams (Recognized & Validated - 6 types)
        mermaid_validated_types = [
            ArtifactType.MERMAID_GANTT,
            ArtifactType.MERMAID_PIE,
            ArtifactType.MERMAID_JOURNEY,
            ArtifactType.MERMAID_MINDMAP,
            ArtifactType.MERMAID_GIT_GRAPH,
            ArtifactType.MERMAID_TIMELINE,
        ]
        
        # C4 Diagrams
        mermaid_c4_types = [
            ArtifactType.MERMAID_C4_CONTEXT,
            ArtifactType.MERMAID_C4_CONTAINER,
            ArtifactType.MERMAID_C4_COMPONENT,
            ArtifactType.MERMAID_C4_DEPLOYMENT,
        ]
        
        # Combine all Mermaid types
        mermaid_types = mermaid_parsable_types + mermaid_validated_types + mermaid_c4_types
        
        for artifact_type in mermaid_types:
            default_routing[artifact_type] = ModelRoutingDTO(
                artifact_type=artifact_type,
                primary_model="ollama:llama3",  # Use full model ID with prefix
                fallback_models=["ollama:codellama", "gemini:gemini-2.5-flash"],  # Use full model IDs
                enabled=True
            )
        
        # HTML diagrams (one for each Mermaid type)
        html_types = [
            ArtifactType.HTML_ERD,
            ArtifactType.HTML_ARCHITECTURE,
            ArtifactType.HTML_SEQUENCE,
            ArtifactType.HTML_CLASS,
            ArtifactType.HTML_STATE,
            ArtifactType.HTML_FLOWCHART,
            ArtifactType.HTML_DATA_FLOW,
            ArtifactType.HTML_USER_FLOW,
            ArtifactType.HTML_COMPONENT,
            ArtifactType.HTML_SYSTEM_OVERVIEW,
            ArtifactType.HTML_API_SEQUENCE,
            ArtifactType.HTML_UML,
            ArtifactType.HTML_GANTT,
            ArtifactType.HTML_PIE,
            ArtifactType.HTML_JOURNEY,
            ArtifactType.HTML_MINDMAP,
            ArtifactType.HTML_GIT_GRAPH,
            ArtifactType.HTML_TIMELINE,
            ArtifactType.HTML_C4_CONTEXT,
            ArtifactType.HTML_C4_CONTAINER,
            ArtifactType.HTML_C4_COMPONENT,
            ArtifactType.HTML_C4_DEPLOYMENT,
        ]
        
        for artifact_type in html_types:
            default_routing[artifact_type] = ModelRoutingDTO(
                artifact_type=artifact_type,
                primary_model="ollama:llama3",  # Use full model ID with prefix
                fallback_models=["gemini:gemini-2.5-flash", "openai:gpt-4o"],  # Use full model IDs
                enabled=True
            )
        
        # Code artifacts
        code_types = [
            ArtifactType.CODE_PROTOTYPE,
            ArtifactType.DEV_VISUAL_PROTOTYPE,
            ArtifactType.API_DOCS,
        ]
        
        for artifact_type in code_types:
            default_routing[artifact_type] = ModelRoutingDTO(
                artifact_type=artifact_type,
                primary_model="ollama:codellama",  # Use full model ID with prefix
                fallback_models=["ollama:llama3", "gemini:gemini-2.5-flash"],  # Use full model IDs
                enabled=True
            )
        
        # PM artifacts
        pm_types = [
            ArtifactType.JIRA,
            ArtifactType.WORKFLOWS,
            ArtifactType.BACKLOG,
            ArtifactType.PERSONAS,
            ArtifactType.ESTIMATIONS,
            ArtifactType.FEATURE_SCORING,
        ]
        
        for artifact_type in pm_types:
            default_routing[artifact_type] = ModelRoutingDTO(
                artifact_type=artifact_type,
                primary_model="ollama:llama3",  # Use full model ID with prefix
                fallback_models=["gemini:gemini-2.5-flash", "openai:gpt-4o"],  # Use full model IDs
                enabled=True
            )
        
        # Save all routings
        for artifact_type, routing in default_routing.items():
            self.routing[artifact_type.value] = routing
        
        self._save_routing()
        logger.info(f"Created default model routing configuration for {len(default_routing)} artifact types")
    
    async def list_models(self, force_refresh: bool = False) -> List[ModelInfoDTO]:
        """
        List all registered models with caching.
        
        Performance optimization: Model list is cached for 60 seconds to avoid
        polling Ollama, cloud providers, and HuggingFace on every request.
        The /api/models/ endpoint was taking 4-7 seconds without caching.
        
        Args:
            force_refresh: If True, bypass cache and refresh from all providers
        
        Returns:
            List of model information
        """
        # Check cache first (unless force_refresh)
        if not force_refresh:
            cached = _model_list_cache.get()
            if cached is not None:
                return cached
        
        logger.info("🔄 [MODEL_SERVICE] Refreshing model list from all providers...")
        start_time = datetime.now()
        
        # Load fine-tuned models from registry first
        self._load_finetuned_models_from_registry()
        
        # Refresh Ollama models if available
        if OLLAMA_AVAILABLE:
            await self._refresh_ollama_models()
        
        # Refresh HuggingFace models
        await self._refresh_huggingface_models()
        
        # Register cloud models if API keys are available
        await self._refresh_cloud_models()
        
        models = list(self.models.values())
        
        # Update cache
        _model_list_cache.set(models)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ [MODEL_SERVICE] Model list refreshed: {len(models)} models in {duration:.2f}s")
        
        return models
    
    def invalidate_model_cache(self) -> None:
        """Invalidate the model list cache (call after model changes)."""
        _model_list_cache.invalidate()
    
    async def _refresh_cloud_models(self):
        """Register cloud models based on available API keys."""
        # Gemini models (Updated Jan 2026 - Official Google AI docs)
        # See: https://ai.google.dev/gemini-api/docs/models
        has_gemini_key = bool(settings.google_api_key or settings.gemini_api_key)
        gemini_models = [
            # Gemini 3 (Latest - Preview, Nov/Dec 2025)
            ("gemini-3-pro-preview", "Gemini 3 Pro (Most Intelligent)"),
            ("gemini-3-flash-preview", "Gemini 3 Flash (Balanced)"),
            # Gemini 2.5 (Stable - June/July 2025)
            ("gemini-2.5-pro", "Gemini 2.5 Pro (Advanced Thinking)"),
            ("gemini-2.5-flash", "Gemini 2.5 Flash (Best Price-Performance)"),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite (Ultra Fast)"),
            # Gemini 2.0 (Previous Gen - Feb 2025)
            ("gemini-2.0-flash", "Gemini 2.0 Flash (Legacy)"),
        ]
        for model_name, display_name in gemini_models:
            model_id = f"gemini:{model_name}"
            # Always register models, but set status based on API key
            status = "available" if has_gemini_key else "no_api_key"
            if model_id not in self.models:
                self.models[model_id] = ModelInfoDTO(
                    id=model_id,
                    name=display_name,
                    provider="gemini",
                    status=status,
                    is_trained=False,
                    metadata={"api_key_configured": has_gemini_key}
                )
            else:
                # Update existing model status
                self.models[model_id].status = status
                self.models[model_id].metadata["api_key_configured"] = has_gemini_key
        # Save registry after updating
        self._save_registry()
        
        # Grok models (via Groq API or X.AI API)
        has_groq_key = bool(settings.groq_api_key)
        has_xai_key = bool(settings.xai_api_key)
        has_grok = has_groq_key or has_xai_key
        
        # Groq models (Updated Jan 2026)
        # See: https://console.groq.com/docs/models
        groq_models = [
            # Llama 3.3 (Latest)
            ("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile"),
            ("llama-3.3-70b-specdec", "Llama 3.3 70B SpecDec (Fast)"),
            # Llama 3.2 (Multimodal)
            ("llama-3.2-90b-vision-preview", "Llama 3.2 90B Vision"),
            ("llama-3.2-11b-vision-preview", "Llama 3.2 11B Vision"),
            # Mixtral (Still available)
            ("mixtral-8x7b-32768", "Mixtral 8x7B"),
        ]
        for model_name, display_name in groq_models:
            model_id = f"groq:{model_name}"
            # Always register models, but set status based on API key
            status = "available" if has_grok else "no_api_key"
            if model_id not in self.models:
                self.models[model_id] = ModelInfoDTO(
                    id=model_id,
                    name=display_name,
                    provider="groq",
                    status=status,
                    is_trained=False,
                    metadata={"api_key_configured": has_grok}
                )
            else:
                # Update existing model status
                self.models[model_id].status = status
                self.models[model_id].metadata["api_key_configured"] = has_grok
        # Save registry after updating
        self._save_registry()
        
        # OpenAI models (Updated Jan 2026)
        # See: https://platform.openai.com/docs/models
        has_openai_key = bool(settings.openai_api_key)
        openai_models = [
            # GPT-4o (Latest flagship)
            ("gpt-4o", "GPT-4o (Latest)"),
            ("gpt-4o-mini", "GPT-4o Mini (Fast)"),
            # o1 Reasoning models
            ("o1", "o1 (Reasoning)"),
            ("o1-mini", "o1 Mini (Reasoning Fast)"),
            # Legacy (still available)
            ("gpt-4-turbo", "GPT-4 Turbo (Legacy)"),
        ]
        for model_name, display_name in openai_models:
            model_id = f"openai:{model_name}"
            status = "available" if has_openai_key else "no_api_key"
            if model_id not in self.models:
                self.models[model_id] = ModelInfoDTO(
                    id=model_id,
                    name=display_name,
                    provider="openai",
                    status=status,
                    is_trained=False,
                    metadata={"api_key_configured": has_openai_key}
                )
            else:
                # Update existing model status
                self.models[model_id].status = status
                self.models[model_id].metadata["api_key_configured"] = has_openai_key
        
        # Anthropic Claude models (Updated Jan 2026)
        # See: https://docs.anthropic.com/en/docs/about-claude/models
        has_anthropic_key = bool(settings.anthropic_api_key)
        anthropic_models = [
            # Claude 4 (Latest - if available)
            ("claude-sonnet-4-20250514", "Claude Sonnet 4 (Latest)"),
            ("claude-opus-4-20250514", "Claude Opus 4"),
            # Claude 3.5 (Stable)
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
            ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku (Fast)"),
        ]
        for model_name, display_name in anthropic_models:
            model_id = f"anthropic:{model_name}"
            status = "available" if has_anthropic_key else "no_api_key"
            if model_id not in self.models:
                self.models[model_id] = ModelInfoDTO(
                    id=model_id,
                    name=display_name,
                    provider="anthropic",
                    status=status,
                    is_trained=False,
                    metadata={"api_key_configured": has_anthropic_key}
                )
            else:
                # Update existing model status
                self.models[model_id].status = status
                self.models[model_id].metadata["api_key_configured"] = has_anthropic_key
        
        self._save_registry()
    
    async def _refresh_ollama_models(self):
        """Refresh model list from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    for model_info in data.get("models", []):
                        model_name = model_info.get("name", "")
                        model_id = f"ollama:{model_name}"
                        
                        # Check if this is a fine-tuned model (contains artifact type or _ft_)
                        is_trained = "_ft_" in model_name or any(
                            artifact_type.value in model_name.lower() 
                            for artifact_type in ArtifactType
                        )
                        
                        if model_id not in self.models:
                            self.models[model_id] = ModelInfoDTO(
                                id=model_id,
                                name=model_name,
                                provider="ollama",
                                status="available",
                                is_trained=is_trained,
                                metadata={
                                    "size": model_info.get("size", 0),
                                    "created_at": model_info.get("modified_at", "")
                                }
                            )
                        else:
                            # Update existing model
                            self.models[model_id].status = "available"
                            self.models[model_id].is_trained = is_trained
                    
                    # Also load fine-tuned models from registry file
                    self._load_finetuned_models_from_registry()
                    
                    self._save_registry()
        except Exception as e:
            logger.warning(f"Could not refresh Ollama models: {e}")
    
    async def _refresh_huggingface_models(self):
        """Refresh HuggingFace models from the HuggingFace service registry."""
        try:
            from backend.services.huggingface_service import get_service as get_hf_service
            hf_service = get_hf_service()
            
            # Get all downloaded models from HuggingFace service
            downloaded_models = await hf_service.list_downloaded_models()
            
            for model_data in downloaded_models:
                model_id = model_data.get("id", "")
                if not model_id:
                    continue
                
                # Create model ID in standard format
                clean_model_id = f"huggingface:{model_id.replace('/', '-')}"
                
                # Check if model is already registered
                if clean_model_id not in self.models:
                    self.models[clean_model_id] = ModelInfoDTO(
                        id=clean_model_id,
                        name=f"{model_id} (HuggingFace)",
                        provider="huggingface",
                        status="downloaded",  # Mark as downloaded and available
                        is_trained=False,
                        metadata={
                            "huggingface_id": model_id,
                            "path": model_data.get("path", ""),
                            "actual_file_path": model_data.get("actual_file_path"),
                            "source": "huggingface",
                            "usable_via_transformers": True
                        }
                    )
                    logger.debug(f"Registered HuggingFace model: {clean_model_id}")
                else:
                    # Update existing model status
                    self.models[clean_model_id].status = "downloaded"
                    # Update metadata
                    if "metadata" not in self.models[clean_model_id].metadata:
                        self.models[clean_model_id].metadata = {}
                    self.models[clean_model_id].metadata.update({
                        "huggingface_id": model_id,
                        "path": model_data.get("path", ""),
                        "actual_file_path": model_data.get("actual_file_path"),
                        "usable_via_transformers": True
                    })
            
            # Save registry after updating
            self._save_registry()
            logger.debug(f"Refreshed {len(downloaded_models)} HuggingFace models")
        except Exception as e:
            logger.warning(f"Could not refresh HuggingFace models: {e}")
    
    def _load_finetuned_models_from_registry(self):
        """Load fine-tuned models from the model_registry.json file."""
        try:
            registry_file = self.registry_file
            if registry_file.exists():
                with open(registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Check for "pairs" structure (from finetuning_worker)
                    if "pairs" in data:
                        for pair_key, pair_data in data["pairs"].items():
                            finetuned_model_name = pair_data.get("finetuned_model", "")
                            if finetuned_model_name:
                                model_id = f"ollama:{finetuned_model_name}"
                                artifact_type = pair_data.get("artifact_type", "")
                                
                                if model_id not in self.models:
                                    self.models[model_id] = ModelInfoDTO(
                                        id=model_id,
                                        name=f"{finetuned_model_name} (Fine-tuned)",
                                        provider="ollama",
                                        status="available",
                                        is_trained=True,
                                        metadata={
                                            "artifact_type": artifact_type,
                                            "base_model": pair_data.get("base_model", ""),
                                            "created_at": pair_data.get("created_at", "")
                                        }
                                    )
                                else:
                                    # Update existing model
                                    self.models[model_id].is_trained = True
                                    if "artifact_type" not in self.models[model_id].metadata:
                                        self.models[model_id].metadata["artifact_type"] = artifact_type
                    
                    # Also check for old "models" structure
                    if "models" in data:
                        for artifact_type, model_data in data["models"].items():
                            finetuned_model_name = model_data.get("finetuned_model", "")
                            if finetuned_model_name:
                                model_id = f"ollama:{finetuned_model_name}"
                                
                                if model_id not in self.models:
                                    self.models[model_id] = ModelInfoDTO(
                                        id=model_id,
                                        name=f"{finetuned_model_name} (Fine-tuned)",
                                        provider="ollama",
                                        status="available",
                                        is_trained=True,
                                        metadata={
                                            "artifact_type": artifact_type,
                                            "base_model": model_data.get("base_model", ""),
                                            "created_at": model_data.get("created_at", "")
                                        }
                                    )
        except Exception as e:
            logger.warning(f"Could not load fine-tuned models from registry: {e}")
    
    async def get_model(self, model_id: str) -> Optional[ModelInfoDTO]:
        """
        Get model information by ID.
        
        Args:
            model_id: Model identifier
        
        Returns:
            Model information or None
        """
        return self.models.get(model_id)
    
    def get_routing_for_artifact(self, artifact_type: Union[ArtifactType, str]) -> Optional[ModelRoutingDTO]:
        """
        Get model routing configuration for an artifact type.
        
        Args:
            artifact_type: Artifact type (enum or string for custom types)
        
        Returns:
            Routing configuration or None
        """
        # Get the string key for lookup
        if isinstance(artifact_type, ArtifactType):
            key = artifact_type.value
        else:
            key = str(artifact_type)
        return self.routing.get(key)
    
    def get_routing_for_custom_artifact(self, artifact_type_id: str) -> Optional[ModelRoutingDTO]:
        """
        Get model routing configuration for a custom artifact type by ID.
        
        Args:
            artifact_type_id: Custom artifact type ID (string)
        
        Returns:
            Routing configuration or None
        """
        return self.routing.get(artifact_type_id)
    
    def create_routing_for_custom_type(self, artifact_type_id: str, primary_model: str = "ollama:llama3:latest", 
                                        fallback_models: Optional[List[str]] = None) -> ModelRoutingDTO:
        """
        Create default routing for a custom artifact type.
        
        Args:
            artifact_type_id: Custom artifact type ID
            primary_model: Primary model to use (default: llama3)
            fallback_models: List of fallback models
        
        Returns:
            Created ModelRoutingDTO
        """
        fallbacks = fallback_models or ["ollama:codellama:7b-instruct", "groq:llama-3.3-70b-versatile"]
        
        routing = ModelRoutingDTO(
            artifact_type=artifact_type_id,  # Store as string for custom types
            primary_model=primary_model,
            fallback_models=fallbacks,
            enabled=True
        )
        self.routing[artifact_type_id] = routing
        self._save_routing()
        logger.info(f"Created routing for custom artifact type: {artifact_type_id}")
        return routing
    
    def get_preferred_model_for_artifact(self, artifact_type: Union[ArtifactType, str]) -> Optional[tuple]:
        """
        Get the user's preferred model for an artifact type.
        
        This method returns the user's explicitly configured primary model,
        INCLUDING cloud models (not just local). This allows the generation
        pipeline to respect user preferences for cloud models.
        
        Args:
            artifact_type: Artifact type
        
        Returns:
            Tuple of (provider, model_name) or None if no routing configured.
        """
        routing = self.get_routing_for_artifact(artifact_type)
        if routing and routing.enabled and routing.primary_model:
            provider, model_name = normalize_model_id(routing.primary_model)
            # Handle both enum and string artifact types for logging
            type_str = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
            logger.debug(f"🎯 [MODEL_SERVICE] User's preferred model for {type_str}: {provider}:{model_name}")
            return (provider, model_name)
        return None
    
    def get_models_for_artifact(self, artifact_type: Union[ArtifactType, str]) -> List[str]:
        """
        Get ordered list of models to try for an artifact type.
        
        Priority order:
        1. Fine-tuned models for this artifact type (from registry)
        2. User-configured routing (primary + fallbacks)
        3. Base model mappings (from ArtifactModelMapper)
        4. Any available Ollama models (universal fallback)
        
        Returns only local (Ollama) models for the local phase.
        
        Args:
            artifact_type: Artifact type (enum or string for custom types)
        
        Returns:
            List of model names to try in order (only Ollama models, no "ollama:" prefix)
        """
        models = []
        # Handle both enum and string artifact types
        if isinstance(artifact_type, ArtifactType):
            artifact_type_str = artifact_type.value.lower().replace("-", "_")
        else:
            artifact_type_str = str(artifact_type).lower().replace("-", "_")
        
        # STEP 1: Check for fine-tuned models (HIGHEST PRIORITY)
        # Load fine-tuned models from registry
        self._load_finetuned_models_from_registry()
        
        # Find fine-tuned models for this artifact type
        for model_id, model_info in self.models.items():
            if model_info.is_trained and model_info.provider in ["ollama", "huggingface"]:
                # Check if this fine-tuned model is for this artifact type
                model_artifact_type = model_info.metadata.get("artifact_type", "").lower().replace("-", "_")
                
                # Match by exact artifact type or by name pattern
                if (model_artifact_type == artifact_type_str or 
                    artifact_type_str in model_id.lower() or
                    artifact_type_str in model_info.name.lower()):
                    # Use normalization to extract model name
                    if model_info.provider == "ollama":
                        model_name = get_ollama_model_name(model_id)
                        if model_name not in models:
                            models.append(model_name)
                            logger.info(f"✅ Found fine-tuned model for {artifact_type_str}: {model_name}")
                    elif model_info.provider == "huggingface":
                        # Keep full model_id for HuggingFace (with provider prefix)
                        if model_id not in models:
                            models.append(model_id)
                            logger.info(f"✅ Found fine-tuned HuggingFace model for {artifact_type_str}: {model_id}")
        
        # STEP 2: Check user-configured routing
        routing = self.get_routing_for_artifact(artifact_type)
        if routing and routing.enabled:
            logger.info(f"📋 [MODEL_SERVICE] Found routing for {artifact_type_str}: primary={routing.primary_model}, fallbacks={routing.fallback_models}")
            
            # Add primary model using normalization
            primary = routing.primary_model
            provider, model_name = normalize_model_id(primary, "ollama")
            
            # Add local models (Ollama or HuggingFace) to local models list
            if provider in ["ollama", "huggingface"]:
                if provider == "ollama" and model_name and model_name not in models:
                    models.append(model_name)
                    logger.info(f"✅ [MODEL_SERVICE] Added primary model: {model_name}")
                elif provider == "huggingface" and primary not in models:
                    models.append(primary)  # Keep full ID with provider prefix
                    logger.info(f"✅ [MODEL_SERVICE] Added primary HuggingFace model: {primary}")
            
            # Add fallback models (Ollama or HuggingFace)
            for fallback in routing.fallback_models:
                provider, model_name = normalize_model_id(fallback, "ollama")
                
                # Add local models to local models list
                if provider == "ollama" and model_name and model_name not in models:
                    models.append(model_name)
                    logger.debug(f"✅ [MODEL_SERVICE] Added fallback model: {model_name}")
                elif provider == "huggingface" and fallback not in models:
                    models.append(fallback)  # Keep full ID with provider prefix
                    logger.debug(f"✅ [MODEL_SERVICE] Added fallback HuggingFace model: {fallback}")
        else:
            if routing:
                logger.warning(f"⚠️ [MODEL_SERVICE] Routing for {artifact_type_str} exists but is disabled")
            else:
                logger.debug(f"📋 [MODEL_SERVICE] No routing found for {artifact_type_str}, using defaults")
        
        # STEP 3: Check base model mappings (from ArtifactModelMapper)
        try:
            from config.artifact_model_mapping import get_artifact_mapper
            artifact_mapper = get_artifact_mapper()
            mapping = artifact_mapper.get_model_for_artifact(artifact_type_str, prefer_fine_tuned=False)
            
            # Add base model and priority models
            if mapping.base_model and mapping.base_model not in models:
                models.append(mapping.base_model)
            
            if mapping.priority_models:
                for priority_model in mapping.priority_models:
                    if priority_model not in models:
                        models.append(priority_model)
        except Exception as e:
            logger.debug(f"Could not load base model mappings: {e}")
        
        # STEP 4: AUTO-ADD DOWNLOADED HUGGINGFACE MODELS
        # This ensures downloaded HuggingFace models are automatically available
        # even if not explicitly configured in routing
        for model_id, model_info in self.models.items():
            if model_info.provider == "huggingface" and model_info.status in ["available", "downloaded"]:
                # Check if this HuggingFace model is usable via transformers
                if model_info.metadata.get("usable_via_transformers", False):
                    if model_id not in models:
                        models.append(model_id)
                        logger.info(f"✅ [MODEL_SERVICE] Auto-added downloaded HuggingFace model: {model_id}")
        
        # STEP 5: Universal fallback - any available local model (Ollama or HuggingFace)
        # This ensures ANY model can work with ANY artifact
        if not models:
            # Get all available local models (Ollama and HuggingFace)
            for model_id, model_info in self.models.items():
                if model_info.provider == "ollama" and model_info.status in ["available", "downloaded"]:
                    model_name = get_ollama_model_name(model_id)
                    if model_name not in models:
                        models.append(model_name)
                elif model_info.provider == "huggingface" and model_info.status in ["available", "downloaded"]:
                    # Add HuggingFace models with provider prefix
                    if model_id not in models:
                        models.append(model_id)
            
            # If still no models, use defaults
            if not models:
                models = ["llama3", "codellama"]
                logger.warning(f"No models found for {artifact_type_str}, using defaults: {models}")
        
        logger.info(f"📋 Models for {artifact_type_str}: {models[:5]}... ({len(models)} total)")
        return models
    
    def update_routing(self, routings: List[ModelRoutingDTO]) -> bool:
        """
        Update model routing configuration.
        
        Args:
            routings: List of routing configurations (supports both enum and string artifact types)
        
        Returns:
            True if successful
        """
        for routing in routings:
            # Handle both enum and string artifact types
            if isinstance(routing.artifact_type, ArtifactType):
                key = routing.artifact_type.value
            else:
                key = str(routing.artifact_type)
            self.routing[key] = routing
        
        self._save_routing()
        logger.info(f"Updated routing for {len(routings)} artifact types")
        return True
    
    async def download_model(self, model_id: str, provider: str = "ollama") -> bool:
        """
        Download a model (Ollama only for now).
        
        Args:
            model_id: Model identifier
            provider: Model provider
        
        Returns:
            True if successful
        """
        if provider == "ollama" and OLLAMA_AVAILABLE:
            try:
                # Extract model name from ID (format: "ollama:model-name")
                model_name = model_id.split(":", 1)[1] if ":" in model_id else model_id
                
                # Update status to downloading
                if model_id not in self.models:
                    self.models[model_id] = ModelInfoDTO(
                        id=model_id,
                        name=model_name,
                        provider="ollama",
                        status="downloading",
                        is_trained=False
                    )
                else:
                    self.models[model_id].status = "downloading"
                self._save_registry()
                
                # Stream download progress
                async with httpx.AsyncClient(timeout=600.0) as client:
                    async with client.stream(
                        "POST",
                        f"{settings.ollama_base_url}/api/pull",
                        json={"name": model_name}
                    ) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        import json
                                        data = json.loads(line)
                                        if "status" in data:
                                            logger.debug(f"Download progress: {data.get('status', '')}")
                                    except json.JSONDecodeError:
                                        pass  # Progress lines may not always be valid JSON
                            
                            # Update registry after successful download
                            if model_id not in self.models:
                                self.models[model_id] = ModelInfoDTO(
                                    id=model_id,
                                    name=model_name,
                                    provider="ollama",
                                    status="downloaded",
                                    is_trained=False
                                )
                            else:
                                self.models[model_id].status = "downloaded"
                            
                            self._save_registry()
                            logger.info(f"✅ Downloaded model: {model_id}")
                            
                            # Refresh Ollama models to ensure it's in the list
                            await self._refresh_ollama_models()
                            
                            # Invalidate cache so next list_models() picks up the new model
                            self.invalidate_model_cache()
                            
                            return True
                        else:
                            error_text = await response.aread()
                            raise Exception(f"Download failed: {error_text.decode()}")
            except Exception as e:
                logger.error(f"Error downloading model {model_id}: {e}")
                # Update status to failed
                if model_id in self.models:
                    self.models[model_id].status = "failed"
                    self._save_registry()
                return False
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get model service statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_models": len(self.models),
            "models_by_provider": {
                provider: sum(1 for m in self.models.values() if m.provider == provider)
                for provider in ["ollama", "huggingface", "openai", "anthropic"]
            },
            "routing_configs": len(self.routing),
            "enabled_routings": sum(1 for r in self.routing.values() if r.enabled)
        }


# Global service instance
_service: Optional[ModelService] = None


def get_service() -> ModelService:
    """Get or create global Model Service instance."""
    global _service
    if _service is None:
        _service = ModelService()
    return _service



