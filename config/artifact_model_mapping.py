"""
Artifact-to-Model Mapping System

Automatically maps artifact types to appropriate Ollama models.
Supports both base models and fine-tuned models for each artifact type.
"""

from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass


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
    base_model: str  # Base Ollama model name
    fine_tuned_model: Optional[str] = None  # Fine-tuned model name if available
    task_type: str = "code"  # Task type for routing
    description: str = ""
    persistent: bool = True  # Whether model stays loaded in VRAM


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
        # Mermaid/Diagram artifacts (using mistral:7b - good for structured text generation)
        ArtifactType.ERD.value: ModelMapping(
            artifact_type=ArtifactType.ERD.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="Entity Relationship Diagrams",
            persistent=False  # Swap model
        ),
        ArtifactType.ARCHITECTURE.value: ModelMapping(
            artifact_type=ArtifactType.ARCHITECTURE.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="Architecture diagrams",
            persistent=False
        ),
        ArtifactType.DATA_FLOW.value: ModelMapping(
            artifact_type=ArtifactType.DATA_FLOW.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="Data flow diagrams",
            persistent=False
        ),
        ArtifactType.USER_FLOW.value: ModelMapping(
            artifact_type=ArtifactType.USER_FLOW.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="User flow diagrams",
            persistent=False
        ),
        ArtifactType.SYSTEM_OVERVIEW.value: ModelMapping(
            artifact_type=ArtifactType.SYSTEM_OVERVIEW.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="System overview diagrams",
            persistent=False
        ),
        ArtifactType.COMPONENTS_DIAGRAM.value: ModelMapping(
            artifact_type=ArtifactType.COMPONENTS_DIAGRAM.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="Component diagrams",
            persistent=False
        ),
        ArtifactType.API_SEQUENCE.value: ModelMapping(
            artifact_type=ArtifactType.API_SEQUENCE.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="API sequence diagrams",
            persistent=False
        ),
        ArtifactType.ALL_DIAGRAMS.value: ModelMapping(
            artifact_type=ArtifactType.ALL_DIAGRAMS.value,
            base_model="mistral:7b-instruct-q4_K_M",
            task_type="mermaid",
            description="All diagram types",
            persistent=False
        ),
        
        # Code artifacts
        ArtifactType.CODE_PROTOTYPE.value: ModelMapping(
            artifact_type=ArtifactType.CODE_PROTOTYPE.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="code",
            description="Code prototypes",
            persistent=True
        ),
        
        # HTML/Visual artifacts
        ArtifactType.VISUAL_PROTOTYPE_DEV.value: ModelMapping(
            artifact_type=ArtifactType.VISUAL_PROTOTYPE_DEV.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="html",
            description="Visual prototypes (HTML)",
            persistent=True
        ),
        
        # Documentation artifacts
        ArtifactType.API_DOCS.value: ModelMapping(
            artifact_type=ArtifactType.API_DOCS.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="documentation",
            description="API documentation",
            persistent=True
        ),
        ArtifactType.DOCUMENTATION.value: ModelMapping(
            artifact_type=ArtifactType.DOCUMENTATION.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="documentation",
            description="General documentation",
            persistent=True
        ),
        
        # Project Management artifacts
        ArtifactType.JIRA.value: ModelMapping(
            artifact_type=ArtifactType.JIRA.value,
            base_model="llama3:8b-instruct-q4_K_M",
            task_type="jira",
            description="JIRA tasks",
            persistent=True
        ),
        ArtifactType.WORKFLOWS.value: ModelMapping(
            artifact_type=ArtifactType.WORKFLOWS.value,
            base_model="llama3:8b-instruct-q4_K_M",
            task_type="planning",
            description="Workflows",
            persistent=True
        ),
        
        # API artifacts
        ArtifactType.OPENAPI.value: ModelMapping(
            artifact_type=ArtifactType.OPENAPI.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="code",
            description="OpenAPI specifications",
            persistent=True
        ),
        ArtifactType.API_CLIENT_PYTHON.value: ModelMapping(
            artifact_type=ArtifactType.API_CLIENT_PYTHON.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="code",
            description="Python API clients",
            persistent=True
        ),
        ArtifactType.API_CLIENT_TYPESCRIPT.value: ModelMapping(
            artifact_type=ArtifactType.API_CLIENT_TYPESCRIPT.value,
            base_model="codellama:7b-instruct-q4_K_M",
            task_type="code",
            description="TypeScript API clients",
            persistent=True
        ),
    }
    
    def __init__(self):
        """Initialize mapper with fine-tuned model registry"""
        self.fine_tuned_models: Dict[str, str] = {}  # artifact_type -> fine_tuned_model_name
        self._load_fine_tuned_models()
    
    def _load_fine_tuned_models(self):
        """Load fine-tuned models from registry"""
        try:
            from components.model_registry import model_registry
            trained_models = model_registry.get_trained_models()
            
            # Map fine-tuned models by artifact type
            for model in trained_models:
                # Extract artifact type from model name or metadata
                # Format: "{artifact_type}_finetuned" or similar
                model_name_lower = model.model_name.lower()
                
                # Try to match artifact types
                for artifact_type in ArtifactType:
                    if artifact_type.value in model_name_lower:
                        self.fine_tuned_models[artifact_type.value] = model.model_name
                        break
        except Exception:
            pass  # Silently fail if registry not available
    
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
            # Default to code model
            mapping = ModelMapping(
                artifact_type=artifact_type,
                base_model="codellama:7b-instruct-q4_K_M",
                task_type="code",
                description=f"{artifact_type} generation",
                persistent=True
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
    
    def list_required_models(self) -> List[str]:
        """
        List all required base models for all artifact types.
        
        Returns:
            List of unique model names
        """
        models = set()
        for mapping in self.BASE_MODEL_MAPPINGS.values():
            models.add(mapping.base_model)
        return sorted(list(models))


# Global mapper instance
_mapper_instance: Optional[ArtifactModelMapper] = None


def get_artifact_mapper() -> ArtifactModelMapper:
    """Get or create global artifact model mapper instance"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = ArtifactModelMapper()
    return _mapper_instance

