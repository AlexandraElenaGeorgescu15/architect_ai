"""
Artifact-to-Model Mapping System

Automatically maps artifact types to appropriate Ollama models.
Supports both base models and fine-tuned models for each artifact type.
"""

import logging
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ArtifactType(Enum):
    """All supported artifact types"""
    # Diagrams
    ERD = "erd"
    ARCHITECTURE = "architecture"
    DATA_FLOW = "data_flow"
    USER_FLOW = "user_flow"
    SYSTEM_OVERVIEW = "system_overview"
    COMPONENTS_DIAGRAM = "components_diagram"
    API_SEQUENCE = "api_sequence"
    ALL_DIAGRAMS = "all_diagrams"
    
    # Code
    CODE_PROTOTYPE = "code_prototype"
    VISUAL_PROTOTYPE_DEV = "visual_prototype_dev"
    
    # Documentation
    API_DOCS = "api_docs"
    DOCUMENTATION = "documentation"
    
    # Project Management
    JIRA = "jira"
    WORKFLOWS = "workflows"
    
    # Other
    OPENAPI = "openapi"
    API_CLIENT_PYTHON = "api_client_python"
    API_CLIENT_TYPESCRIPT = "api_client_typescript"


@dataclass
class ModelMapping:
    """Model mapping configuration for an artifact type"""
    artifact_type: str
    base_model: str  # Base Ollama model name (primary)
    priority_models: Optional[List[str]] = None  # Priority list of models to try
    fine_tuned_model: Optional[str] = None  # Fine-tuned model name if available
    task_type: str = "code"  # Task type for routing
    description: str = ""
    persistent: bool = True  # Whether model stays loaded in VRAM
    min_quality_score: int = 80  # Minimum quality score threshold


class ArtifactModelMapper:
    """
    Maps artifact types to appropriate Ollama models.
    
    Automatically selects:
    1. Fine-tuned model if available for artifact type
    2. Base model as fallback
    3. Cloud provider if local models fail validation
    """
    
    # Base model mappings (Ollama models)
    BASE_MODEL_MAPPINGS: Dict[str, ModelMapping] = {
        # Mermaid/Diagram artifacts - ENHANCED with priority models
        ArtifactType.ERD.value: ModelMapping(
            artifact_type=ArtifactType.ERD.value,
            base_model="mistral:7b-instruct-q4_K_M",
            priority_models=["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            task_type="mermaid",
            description="Entity Relationship Diagrams",
            persistent=False,  # Swap model
            min_quality_score=80
        ),
        ArtifactType.ARCHITECTURE.value: ModelMapping(
            artifact_type=ArtifactType.ARCHITECTURE.value,
            base_model="llama3:8b-instruct-q4_K_M",  # Changed from mistral for better complex diagrams
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            task_type="mermaid",
            description="Architecture diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.DATA_FLOW.value: ModelMapping(
            artifact_type=ArtifactType.DATA_FLOW.value,
            base_model="mistral:7b-instruct-q4_K_M",
            priority_models=["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="mermaid",
            description="Data flow diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.USER_FLOW.value: ModelMapping(
            artifact_type=ArtifactType.USER_FLOW.value,
            base_model="mistral:7b-instruct-q4_K_M",
            priority_models=["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="mermaid",
            description="User flow diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.SYSTEM_OVERVIEW.value: ModelMapping(
            artifact_type=ArtifactType.SYSTEM_OVERVIEW.value,
            base_model="llama3:8b-instruct-q4_K_M",  # Changed to llama3 for better complex overviews
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M"],
            task_type="mermaid",
            description="System overview diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.COMPONENTS_DIAGRAM.value: ModelMapping(
            artifact_type=ArtifactType.COMPONENTS_DIAGRAM.value,
            base_model="llama3:8b-instruct-q4_K_M",  # Changed to llama3 for better component relationships
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M"],
            task_type="mermaid",
            description="Component diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.API_SEQUENCE.value: ModelMapping(
            artifact_type=ArtifactType.API_SEQUENCE.value,
            base_model="mistral:7b-instruct-q4_K_M",
            priority_models=["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="mermaid",
            description="API sequence diagrams",
            persistent=False,
            min_quality_score=80
        ),
        ArtifactType.ALL_DIAGRAMS.value: ModelMapping(
            artifact_type=ArtifactType.ALL_DIAGRAMS.value,
            base_model="mistral:7b-instruct-q4_K_M",
            priority_models=["mistral:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="mermaid",
            description="All diagram types",
            persistent=False,
            min_quality_score=80
        ),
        
        # Code artifacts
        ArtifactType.CODE_PROTOTYPE.value: ModelMapping(
            artifact_type=ArtifactType.CODE_PROTOTYPE.value,
            base_model="codellama:7b-instruct-q4_K_M",
            priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="code",
            description="Code prototypes",
            persistent=True,
            min_quality_score=80
        ),
        
        # HTML/Visual artifacts - CHANGED to llama3 (better at HTML generation)
        ArtifactType.VISUAL_PROTOTYPE_DEV.value: ModelMapping(
            artifact_type=ArtifactType.VISUAL_PROTOTYPE_DEV.value,
            base_model="llama3:8b-instruct-q4_K_M",  # Changed from codellama
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            task_type="html",
            description="Visual prototypes (HTML)",
            persistent=True,
            min_quality_score=80
        ),
        
        # Documentation artifacts
        ArtifactType.API_DOCS.value: ModelMapping(
            artifact_type=ArtifactType.API_DOCS.value,
            base_model="codellama:7b-instruct-q4_K_M",
            priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="documentation",
            description="API documentation",
            persistent=True,
            min_quality_score=80
        ),
        ArtifactType.DOCUMENTATION.value: ModelMapping(
            artifact_type=ArtifactType.DOCUMENTATION.value,
            base_model="llama3:8b-instruct-q4_K_M",  # Changed to llama3 for better natural language
            priority_models=["llama3:8b-instruct-q4_K_M", "codellama:7b-instruct-q4_K_M"],
            task_type="documentation",
            description="General documentation",
            persistent=True,
            min_quality_score=80
        ),
        
        # Project Management artifacts
        ArtifactType.JIRA.value: ModelMapping(
            artifact_type=ArtifactType.JIRA.value,
            base_model="llama3:8b-instruct-q4_K_M",
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M"],
            task_type="jira",
            description="JIRA tasks",
            persistent=True,
            min_quality_score=80
        ),
        ArtifactType.WORKFLOWS.value: ModelMapping(
            artifact_type=ArtifactType.WORKFLOWS.value,
            base_model="llama3:8b-instruct-q4_K_M",
            priority_models=["llama3:8b-instruct-q4_K_M", "mistral:7b-instruct-q4_K_M"],
            task_type="planning",
            description="Workflows",
            persistent=True,
            min_quality_score=80
        ),
        
        # API artifacts
        ArtifactType.OPENAPI.value: ModelMapping(
            artifact_type=ArtifactType.OPENAPI.value,
            base_model="codellama:7b-instruct-q4_K_M",
            priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="code",
            description="OpenAPI specifications",
            persistent=True,
            min_quality_score=80
        ),
        ArtifactType.API_CLIENT_PYTHON.value: ModelMapping(
            artifact_type=ArtifactType.API_CLIENT_PYTHON.value,
            base_model="codellama:7b-instruct-q4_K_M",
            priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="code",
            description="Python API clients",
            persistent=True,
            min_quality_score=80
        ),
        ArtifactType.API_CLIENT_TYPESCRIPT.value: ModelMapping(
            artifact_type=ArtifactType.API_CLIENT_TYPESCRIPT.value,
            base_model="codellama:7b-instruct-q4_K_M",
            priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
            task_type="code",
            description="TypeScript API clients",
            persistent=True,
            min_quality_score=80
        ),
    }
    
    def __init__(self):
        """Initialize mapper with fine-tuned model registry"""
        self.fine_tuned_models: Dict[str, str] = {}  # artifact_type -> fine_tuned_model_name
        self._load_fine_tuned_models()
    
    def _load_fine_tuned_models(self):
        """Load fine-tuned models from registry"""
        try:
            # Try ModelService first (newer system)
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from backend.services.model_service import get_service
                model_service = get_service()
                
                # Load fine-tuned models from registry
                model_service._load_finetuned_models_from_registry()
                
                # Map fine-tuned models by artifact type
                for model_id, model_info in model_service.models.items():
                    if model_info.is_trained and model_info.provider == "ollama":
                        artifact_type = model_info.metadata.get("artifact_type", "")
                        if artifact_type:
                            # Extract model name (remove "ollama:" prefix)
                            model_name = model_id.split(":", 1)[1] if ":" in model_id else model_id
                            self.fine_tuned_models[artifact_type.lower().replace("-", "_")] = model_name
                            logger.info(f"✅ Loaded fine-tuned model: {artifact_type} -> {model_name}")
            except Exception as e:
                logger.debug(f"Could not load from ModelService: {e}")
            
            # Fallback: Try old model_registry
            try:
                from components.model_registry import model_registry
                trained_models = model_registry.get_trained_models()
                
                # Map fine-tuned models by artifact type
                for model in trained_models:
                    # Extract artifact type from model name or metadata
                    model_name_lower = model.model_name.lower()
                    
                    # Try to match artifact types
                    for artifact_type in ArtifactType:
                        if artifact_type.value in model_name_lower:
                            self.fine_tuned_models[artifact_type.value] = model.model_name
                            break
            except Exception:
                pass  # Silently fail if registry not available
        except Exception as e:
            logger.debug(f"Error loading fine-tuned models: {e}")
    
    def get_model_for_artifact(
        self, 
        artifact_type: str, 
        prefer_fine_tuned: bool = True
    ) -> ModelMapping:
        """
        Get model mapping for artifact type.
        
        Args:
            artifact_type: Type of artifact to generate
            prefer_fine_tuned: Prefer fine-tuned model if available
            
        Returns:
            ModelMapping with model configuration
        """
        # Normalize artifact type
        artifact_type = artifact_type.lower().replace("-", "_")
        
        # Get base mapping
        mapping = self.BASE_MODEL_MAPPINGS.get(artifact_type)
        if not mapping:
            # Default to code model with priority list
            mapping = ModelMapping(
                artifact_type=artifact_type,
                base_model="codellama:7b-instruct-q4_K_M",
                priority_models=["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"],
                task_type="code",
                description=f"{artifact_type} generation",
                persistent=True,
                min_quality_score=80
            )
        
        # Check for fine-tuned model
        if prefer_fine_tuned and artifact_type in self.fine_tuned_models:
            mapping.fine_tuned_model = self.fine_tuned_models[artifact_type]
        
        return mapping
    
    def get_model_name(
        self, 
        artifact_type: str, 
        prefer_fine_tuned: bool = True
    ) -> str:
        """
        Get model name for artifact type (fine-tuned or base).
        
        Args:
            artifact_type: Type of artifact to generate
            prefer_fine_tuned: Prefer fine-tuned model if available
            
        Returns:
            Model name to use
        """
        mapping = self.get_model_for_artifact(artifact_type, prefer_fine_tuned)
        
        # Return fine-tuned if available and preferred, otherwise base
        if prefer_fine_tuned and mapping.fine_tuned_model:
            return mapping.fine_tuned_model
        
        return mapping.base_model
    
    def get_task_type(self, artifact_type: str) -> str:
        """
        Get task type for artifact (for routing).
        
        Args:
            artifact_type: Type of artifact to generate
            
        Returns:
            Task type string
        """
        mapping = self.get_model_for_artifact(artifact_type)
        return mapping.task_type
    
    def is_persistent_model(self, artifact_type: str) -> bool:
        """
        Check if model for artifact type is persistent (stays loaded).
        
        Args:
            artifact_type: Type of artifact to generate
            
        Returns:
            True if persistent, False if swap model
        """
        mapping = self.get_model_for_artifact(artifact_type)
        return mapping.persistent
    
    def get_priority_models(self, artifact_type: str) -> List[str]:
        """
        Get priority list of models for artifact type.
        
        Args:
            artifact_type: Type of artifact to generate
            
        Returns:
            List of model names in priority order
        """
        mapping = self.get_model_for_artifact(artifact_type)
        return mapping.priority_models or [mapping.base_model]
    
    def get_quality_threshold(self, artifact_type: str) -> int:
        """
        Get minimum quality threshold for artifact type.
        
        Args:
            artifact_type: Type of artifact to generate
            
        Returns:
            Minimum quality score (0-100)
        """
        mapping = self.get_model_for_artifact(artifact_type)
        return mapping.min_quality_score
    
    def list_required_models(self) -> List[str]:
        """
        List all required base models for all artifact types.
        
        Returns:
            List of unique model names
        """
        models = set()
        for mapping in self.BASE_MODEL_MAPPINGS.values():
            models.add(mapping.base_model)
            if mapping.priority_models:
                models.update(mapping.priority_models)
        return sorted(list(models))


# Global mapper instance
_mapper_instance: Optional[ArtifactModelMapper] = None


def get_artifact_mapper() -> ArtifactModelMapper:
    """Get or create global artifact model mapper instance"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = ArtifactModelMapper()
    return _mapper_instance

