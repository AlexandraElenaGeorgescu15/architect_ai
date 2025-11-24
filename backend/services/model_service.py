"""
Model Management Service - Handles model registry, routing, and management.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json
import yaml

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.models.dto import (
    ModelInfoDTO, ModelRoutingDTO, ArtifactType
)

logger = logging.getLogger(__name__)

# Optional imports for Ollama (graceful degradation)
try:
    import httpx
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("httpx not available. Ollama integration disabled.")


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
                        self.routing[artifact_type] = ModelRoutingDTO(
                            artifact_type=ArtifactType(artifact_type),
                            **routing_data
                        )
                logger.info(f"Loaded routing for {len(self.routing)} artifact types")
            except Exception as e:
                logger.error(f"Error loading routing config: {e}")
        else:
            # Create default routing
            self._create_default_routing()
    
    def _save_routing(self):
        """Save model routing configuration to file."""
        try:
            data = {
                routing.artifact_type.value: {
                    "primary_model": routing.primary_model,
                    "fallback_models": routing.fallback_models,
                    "enabled": routing.enabled
                }
                for routing in self.routing.values()
            }
            with open(self.routing_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Error saving routing config: {e}")
    
    def _create_default_routing(self):
        """Create default model routing configuration for all artifact types."""
        # Default models for different artifact categories
        mermaid_models = ["llama3", "codellama", "gemini-2.0-flash-exp"]
        html_models = ["llama3", "gemini-2.0-flash-exp", "gpt-4-turbo"]
        code_models = ["codellama", "llama3", "gemini-2.0-flash-exp"]
        pm_models = ["llama3", "gemini-2.0-flash-exp", "gpt-4-turbo"]
        
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
                fallback_models=["ollama:codellama", "gemini:gemini-2.0-flash-exp"],  # Use full model IDs
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
                fallback_models=["gemini:gemini-2.0-flash-exp", "openai:gpt-4-turbo"],  # Use full model IDs
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
                fallback_models=["ollama:llama3", "gemini:gemini-2.0-flash-exp"],  # Use full model IDs
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
                fallback_models=["gemini:gemini-2.0-flash-exp", "openai:gpt-4-turbo"],  # Use full model IDs
                enabled=True
            )
        
        # Save all routings
        for artifact_type, routing in default_routing.items():
            self.routing[artifact_type.value] = routing
        
        self._save_routing()
        logger.info(f"Created default model routing configuration for {len(default_routing)} artifact types")
    
    async def list_models(self) -> List[ModelInfoDTO]:
        """
        List all registered models.
        
        Returns:
            List of model information
        """
        # Refresh Ollama models if available
        if OLLAMA_AVAILABLE:
            await self._refresh_ollama_models()
        
        # Register cloud models if API keys are available
        await self._refresh_cloud_models()
        
        return list(self.models.values())
    
    async def _refresh_cloud_models(self):
        """Register cloud models based on available API keys."""
        # Gemini models
        has_gemini_key = bool(settings.google_api_key or settings.gemini_api_key)
        gemini_models = [
            ("gemini-2.0-flash-exp", "Gemini 2.0 Flash Experimental"),
            ("gemini-1.5-pro", "Gemini 1.5 Pro"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash"),
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
        
        groq_models = [
            ("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile"),
            ("llama-3.1-70b-versatile", "Llama 3.1 70B Versatile"),
            ("llama-3.1-8b-instant", "Llama 3.1 8B Instant"),
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
        
        # OpenAI models
        has_openai_key = bool(settings.openai_api_key)
        openai_models = [
            ("gpt-4-turbo", "GPT-4 Turbo"),
            ("gpt-4", "GPT-4"),
            ("gpt-3.5-turbo", "GPT-3.5 Turbo"),
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
        
        # Anthropic models
        has_anthropic_key = bool(settings.anthropic_api_key)
        anthropic_models = [
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
            ("claude-3-opus-20240229", "Claude 3 Opus"),
            ("claude-3-sonnet-20240229", "Claude 3 Sonnet"),
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
                        
                        if model_id not in self.models:
                            self.models[model_id] = ModelInfoDTO(
                                id=model_id,
                                name=model_name,
                                provider="ollama",
                                status="available",
                                is_trained=False,
                                metadata={"size": model_info.get("size", 0)}
                            )
                        else:
                            # Update existing model
                            self.models[model_id].status = "available"
                    
                    self._save_registry()
        except Exception as e:
            logger.warning(f"Could not refresh Ollama models: {e}")
    
    async def get_model(self, model_id: str) -> Optional[ModelInfoDTO]:
        """
        Get model information by ID.
        
        Args:
            model_id: Model identifier
        
        Returns:
            Model information or None
        """
        return self.models.get(model_id)
    
    def get_routing_for_artifact(self, artifact_type: ArtifactType) -> Optional[ModelRoutingDTO]:
        """
        Get model routing configuration for an artifact type.
        
        Args:
            artifact_type: Artifact type
        
        Returns:
            Routing configuration or None
        """
        return self.routing.get(artifact_type.value)
    
    def get_models_for_artifact(self, artifact_type: ArtifactType) -> List[str]:
        """
        Get ordered list of models to try for an artifact type.
        Returns only local (Ollama) models for the local phase.
        
        Args:
            artifact_type: Artifact type
        
        Returns:
            List of model IDs to try in order (only Ollama models)
        """
        routing = self.get_routing_for_artifact(artifact_type)
        if not routing or not routing.enabled:
            # Default fallback (Ollama models only) - return model names without prefix
            return ["llama3", "codellama"]
        
        models = []
        # Add primary model (extract Ollama model name)
        primary = routing.primary_model
        if primary.startswith("ollama:"):
            models.append(primary.split(":", 1)[1])  # Extract model name (e.g., "llama3")
        elif ":" not in primary:
            # Assume Ollama if no prefix (backward compatibility)
            models.append(primary)
        # Skip cloud models in primary (they'll be tried in cloud phase)
        
        # Add fallback models (only Ollama)
        for fallback in routing.fallback_models:
            if fallback.startswith("ollama:"):
                model_name = fallback.split(":", 1)[1]
                if model_name not in models:
                    models.append(model_name)  # Extract model name
            elif ":" not in fallback:
                # Assume Ollama if no prefix (backward compatibility)
                if fallback not in models:
                    models.append(fallback)
            # Skip cloud models (they'll be tried in cloud phase)
        
        # If no Ollama models found, return defaults
        if not models:
            return ["llama3", "codellama"]
        
        return models
    
    def update_routing(self, routings: List[ModelRoutingDTO]) -> bool:
        """
        Update model routing configuration.
        
        Args:
            routings: List of routing configurations
        
        Returns:
            True if successful
        """
        for routing in routings:
            self.routing[routing.artifact_type.value] = routing
        
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
                
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        f"{settings.ollama_base_url}/api/pull",
                        json={"name": model_name}
                    )
                    if response.status_code == 200:
                        # Update registry
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
                        logger.info(f"Downloaded model: {model_id}")
                        return True
            except Exception as e:
                logger.error(f"Error downloading model {model_id}: {e}")
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



