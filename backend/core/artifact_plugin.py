"""
Artifact plugin system architecture.

Defines the base Artifact class and registry for plugin-based artifact generation.
Supports auto-discovery of artifact plugins from the backend/artifacts/ directory.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from enum import Enum
from pathlib import Path
import importlib
import importlib.util
import inspect
import logging

from backend.models.dto import ArtifactType, ValidationResultDTO

logger = logging.getLogger(__name__)


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
    
    def auto_discover(self, artifacts_dir: Optional[Path] = None):
        """
        Auto-discover and register artifact plugins.
        
        Scans backend/artifacts/ directory for Python files containing
        classes that inherit from Artifact, instantiates them, and registers them.
        
        Args:
            artifacts_dir: Optional path to artifacts directory. If None, uses default.
        """
        if artifacts_dir is None:
            # Default to backend/artifacts/ relative to this file
            artifacts_dir = Path(__file__).parent.parent / "artifacts"
        
        if not artifacts_dir.exists():
            logger.debug(f"Artifacts directory not found: {artifacts_dir}")
            # Create the directory so plugins can be added later
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            return
        
        discovered_count = 0
        
        # Scan all Python files in the artifacts directory
        for py_file in artifacts_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue  # Skip __init__.py and private modules
            
            try:
                # Load the module
                module_name = f"backend.artifacts.{py_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load spec for {py_file}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find all classes in the module that inherit from Artifact
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a subclass of Artifact (but not Artifact itself)
                    if (
                        issubclass(obj, Artifact) and 
                        obj is not Artifact and
                        not inspect.isabstract(obj)
                    ):
                        try:
                            # Instantiate and register the artifact
                            instance = obj()
                            self.register(instance)
                            discovered_count += 1
                            logger.info(f"Auto-discovered artifact plugin: {name} ({instance.artifact_type})")
                        except Exception as e:
                            logger.error(f"Failed to instantiate artifact plugin {name}: {e}")
                            
            except Exception as e:
                logger.error(f"Failed to load artifact module {py_file}: {e}")
        
        if discovered_count > 0:
            logger.info(f"Auto-discovered {discovered_count} artifact plugins")
        else:
            logger.debug("No artifact plugins discovered")
    
    def get_all_artifacts(self) -> Dict[ArtifactType, 'Artifact']:
        """
        Get all registered artifacts.
        
        Returns:
            Dictionary mapping artifact types to plugin instances
        """
        return self._artifacts.copy()
    
    def is_registered(self, artifact_type: ArtifactType) -> bool:
        """
        Check if an artifact type is registered.
        
        Args:
            artifact_type: Artifact type to check
            
        Returns:
            True if registered, False otherwise
        """
        return artifact_type in self._artifacts


# Global artifact registry
artifact_registry = ArtifactRegistry()


def get_artifact_registry() -> ArtifactRegistry:
    """Get the global artifact registry."""
    return artifact_registry


def discover_artifacts():
    """Convenience function to run auto-discovery on the global registry."""
    artifact_registry.auto_discover()



