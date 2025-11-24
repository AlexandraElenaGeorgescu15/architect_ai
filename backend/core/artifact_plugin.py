"""
Artifact plugin system architecture.

Defines the base Artifact class and registry for plugin-based artifact generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from backend.models.dto import ArtifactType, ValidationResultDTO


class Artifact(ABC):
    """
    Base abstract class for all artifact plugins.
    
    Each artifact type (Mermaid ERD, HTML ERD, Code Prototype, etc.) 
    implements this interface to provide:
    - Generation logic
    - Validation rules
    - Dataset builder
    - Prompt templates
    """
    
    @property
    @abstractmethod
    def artifact_type(self) -> ArtifactType:
        """Return the artifact type enum."""
        pass
    
    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the prompt template for this artifact type."""
        pass
    
    @property
    @abstractmethod
    def validators(self) -> List[str]:
        """Return list of validator names to apply."""
        pass
    
    @abstractmethod
    async def generate(
        self,
        context: str,
        meeting_notes: str,
        options: Dict[str, Any]
    ) -> str:
        """
        Generate artifact content.
        
        Args:
            context: Assembled context (RAG + KG + PM + ML)
            meeting_notes: Original meeting notes
            options: Generation options (temperature, model, etc.)
        
        Returns:
            Generated artifact content (Mermaid syntax, HTML, code, etc.)
        """
        pass
    
    @abstractmethod
    def validate(self, content: str) -> ValidationResultDTO:
        """
        Validate generated artifact.
        
        Args:
            content: Generated artifact content
        
        Returns:
            Validation result with score and errors
        """
        pass
    
    @abstractmethod
    def get_dataset_builder(self) -> Optional['DatasetBuilder']:
        """
        Get dataset builder for this artifact type.
        
        Returns:
            DatasetBuilder instance or None if not supported
        """
        pass


class DatasetBuilder(ABC):
    """
    Base abstract class for dataset builders.
    
    Each artifact type can have a dataset builder that generates
    training examples for fine-tuning.
    """
    
    @abstractmethod
    def generate_examples(self, count: int, domain: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Generate training examples.
        
        Args:
            count: Number of examples to generate
            domain: Optional domain (e-commerce, healthcare, etc.)
        
        Returns:
            List of training examples with instruction, input, output
        """
        pass


class ArtifactRegistry:
    """
    Registry for artifact plugins.
    
    Provides:
    - Plugin registration
    - Auto-discovery
    - Type-based lookup
    """
    
    def __init__(self):
        """Initialize artifact registry."""
        self._artifacts: Dict[ArtifactType, Artifact] = {}
    
    def register(self, artifact: Artifact):
        """
        Register an artifact plugin.
        
        Args:
            artifact: Artifact plugin instance
        """
        self._artifacts[artifact.artifact_type] = artifact
    
    def get_artifact(self, artifact_type: ArtifactType) -> Optional[Artifact]:
        """
        Get artifact plugin by type.
        
        Args:
            artifact_type: Artifact type enum
        
        Returns:
            Artifact plugin instance or None if not found
        """
        return self._artifacts.get(artifact_type)
    
    def list_artifacts(self) -> List[ArtifactType]:
        """
        List all registered artifact types.
        
        Returns:
            List of registered artifact types
        """
        return list(self._artifacts.keys())
    
    def auto_discover(self):
        """
        Auto-discover and register artifact plugins.
        
        Scans backend/artifacts/ directory for plugin implementations.
        """
        # TODO: Implement auto-discovery
        # This will scan for classes inheriting from Artifact
        # and automatically register them
        pass


# Global artifact registry
artifact_registry = ArtifactRegistry()



