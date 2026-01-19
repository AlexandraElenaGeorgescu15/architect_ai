"""
Custom Artifact Type Service - Allows users to define custom artifact types.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import json
from datetime import datetime
from dataclasses import dataclass, asdict, field

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CustomArtifactType:
    """A user-defined custom artifact type."""
    id: str  # e.g., "security_review"
    name: str  # "Security Review"
    category: str  # "Security" (can be custom)
    prompt_template: str  # Template for generating this artifact
    description: str = ""  # Brief description
    validation_rules: List[str] = field(default_factory=list)  # Optional validation rules
    default_model: Optional[str] = None  # Preferred model for this type
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default categories for artifact types
DEFAULT_CATEGORIES = [
    "Design",
    "Development", 
    "Testing",
    "Documentation",
    "Project Management",
    "Security",
    "DevOps",
    "Custom"
]


class CustomArtifactService:
    """
    Service for managing user-defined custom artifact types.
    
    Features:
    - Create, read, update, delete custom artifact types
    - Persist to JSON file
    - Merge with built-in types at runtime
    - Category management
    """
    
    def __init__(self):
        """Initialize Custom Artifact Service."""
        base_path = Path(settings.base_path)
        self.storage_file = base_path / "data" / "custom_artifact_types.json"
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory store
        self.custom_types: Dict[str, CustomArtifactType] = {}
        self.custom_categories: List[str] = []
        
        # Load existing custom types
        self._load()
        
        logger.info(f"Custom Artifact Service initialized with {len(self.custom_types)} custom types")
    
    def _load(self):
        """Load custom artifact types from storage."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                
                # Load custom types
                for type_id, type_data in data.get("types", {}).items():
                    self.custom_types[type_id] = CustomArtifactType(**type_data)
                
                # Load custom categories
                self.custom_categories = data.get("custom_categories", [])
                
                logger.info(f"Loaded {len(self.custom_types)} custom artifact types")
            except Exception as e:
                logger.error(f"Error loading custom artifact types: {e}")
    
    def _save(self):
        """Save custom artifact types to storage."""
        try:
            data = {
                "types": {
                    type_id: cat.to_dict() for type_id, cat in self.custom_types.items()
                },
                "custom_categories": self.custom_categories,
                "updated_at": datetime.now().isoformat()
            }
            self.storage_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info(f"Saved {len(self.custom_types)} custom artifact types")
        except Exception as e:
            logger.error(f"Error saving custom artifact types: {e}")
    
    def create_type(
        self,
        id: str,
        name: str,
        category: str,
        prompt_template: str,
        description: str = "",
        validation_rules: Optional[List[str]] = None,
        default_model: Optional[str] = None
    ) -> CustomArtifactType:
        """
        Create a new custom artifact type.
        
        Args:
            id: Unique identifier (snake_case)
            name: Display name
            category: Category for grouping
            prompt_template: Template for AI generation
            description: Brief description
            validation_rules: Optional list of validation rules
            default_model: Optional preferred model
        
        Returns:
            Created CustomArtifactType
        
        Raises:
            ValueError: If id already exists or is invalid
        """
        # Normalize ID
        id = id.lower().replace(" ", "_").replace("-", "_")
        
        # Check for existing type (including built-in)
        if id in self.custom_types:
            raise ValueError(f"Custom artifact type '{id}' already exists")
        
        # Check against built-in types
        from backend.models.dto import ArtifactType
        built_in_ids = [t.value for t in ArtifactType]
        if id in built_in_ids:
            raise ValueError(f"Cannot override built-in artifact type '{id}'")
        
        # Validate ID format
        if not id or len(id) < 3 or len(id) > 50:
            raise ValueError("ID must be 3-50 characters")
        if not id.replace("_", "").isalnum():
            raise ValueError("ID must be alphanumeric with underscores only")
        
        # Add custom category if new
        if category not in DEFAULT_CATEGORIES and category not in self.custom_categories:
            self.custom_categories.append(category)
        
        # Create type
        custom_type = CustomArtifactType(
            id=id,
            name=name,
            category=category,
            prompt_template=prompt_template,
            description=description,
            validation_rules=validation_rules or [],
            default_model=default_model
        )
        
        self.custom_types[id] = custom_type
        self._save()
        
        logger.info(f"Created custom artifact type: {id}")
        return custom_type
    
    def get_type(self, type_id: str) -> Optional[CustomArtifactType]:
        """Get a custom artifact type by ID."""
        return self.custom_types.get(type_id)
    
    def list_types(self, include_disabled: bool = False) -> List[CustomArtifactType]:
        """List all custom artifact types."""
        types = list(self.custom_types.values())
        if not include_disabled:
            types = [t for t in types if t.is_enabled]
        return sorted(types, key=lambda t: (t.category, t.name))
    
    def update_type(
        self,
        type_id: str,
        **updates
    ) -> Optional[CustomArtifactType]:
        """
        Update a custom artifact type.
        
        Args:
            type_id: ID of type to update
            **updates: Fields to update
        
        Returns:
            Updated CustomArtifactType or None if not found
        """
        if type_id not in self.custom_types:
            return None
        
        custom_type = self.custom_types[type_id]
        
        # Update allowed fields
        allowed_fields = ["name", "category", "prompt_template", "description", 
                        "validation_rules", "default_model", "is_enabled"]
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(custom_type, field, value)
        
        custom_type.updated_at = datetime.now().isoformat()
        
        # Add new category if needed
        if "category" in updates:
            category = updates["category"]
            if category not in DEFAULT_CATEGORIES and category not in self.custom_categories:
                self.custom_categories.append(category)
        
        self._save()
        logger.info(f"Updated custom artifact type: {type_id}")
        return custom_type
    
    def delete_type(self, type_id: str) -> bool:
        """
        Delete a custom artifact type.
        
        Args:
            type_id: ID of type to delete
        
        Returns:
            True if deleted, False if not found
        """
        if type_id not in self.custom_types:
            return False
        
        del self.custom_types[type_id]
        self._save()
        
        logger.info(f"Deleted custom artifact type: {type_id}")
        return True
    
    def get_categories(self) -> List[str]:
        """Get all available categories (default + custom)."""
        return DEFAULT_CATEGORIES + self.custom_categories
    
    def add_category(self, category: str) -> bool:
        """Add a custom category."""
        if category in DEFAULT_CATEGORIES or category in self.custom_categories:
            return False
        
        self.custom_categories.append(category)
        self._save()
        return True
    
    def get_all_artifact_types(self) -> List[Dict[str, Any]]:
        """
        Get all artifact types (built-in + custom) with metadata.
        
        Returns list of dicts with: id, name, category, is_custom, is_enabled
        """
        from backend.models.dto import ArtifactType
        
        all_types = []
        
        # Add built-in types
        builtin_categories = {
            "mermaid_": "Design",
            "html_": "Design",
            "code_": "Development",
            "dev_": "Development",
            "api_": "Documentation",
            "jira": "Project Management",
            "workflows": "Project Management",
            "backlog": "Project Management",
            "personas": "Project Management",
            "estimations": "Project Management",
            "feature_": "Project Management",
        }
        
        for artifact_type in ArtifactType:
            type_value = artifact_type.value
            
            # Determine category
            category = "Other"
            for prefix, cat in builtin_categories.items():
                if type_value.startswith(prefix) or type_value == prefix.rstrip("_"):
                    category = cat
                    break
            
            all_types.append({
                "id": type_value,
                "name": type_value.replace("_", " ").title(),
                "category": category,
                "is_custom": False,
                "is_enabled": True
            })
        
        # Add custom types
        for custom_type in self.custom_types.values():
            all_types.append({
                "id": custom_type.id,
                "name": custom_type.name,
                "category": custom_type.category,
                "is_custom": True,
                "is_enabled": custom_type.is_enabled,
                "description": custom_type.description,
                "default_model": custom_type.default_model
            })
        
        return sorted(all_types, key=lambda t: (t["category"], t["name"]))


# Global instance
_custom_artifact_service: Optional[CustomArtifactService] = None


def get_service() -> CustomArtifactService:
    """Get or create the global Custom Artifact Service instance."""
    global _custom_artifact_service
    if _custom_artifact_service is None:
        _custom_artifact_service = CustomArtifactService()
    return _custom_artifact_service
