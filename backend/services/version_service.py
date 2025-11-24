"""
Artifact Version Service - Tracks and manages artifact versions.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json
import shutil

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class VersionService:
    """
    Service for managing artifact versions.
    
    Features:
    - Track artifact versions
    - Compare versions
    - Restore previous versions
    - Automatic versioning on regeneration
    """
    
    def __init__(self):
        """Initialize Version Service."""
        self.versions_dir = Path("data/versions")
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory version store
        self.versions: Dict[str, List[Dict[str, Any]]] = {}  # artifact_id -> versions
        
        # Load existing versions
        self._load_versions()
        
        logger.info("Version Service initialized")
    
    def _load_versions(self):
        """Load version history from disk."""
        for artifact_file in self.versions_dir.glob("*.json"):
            try:
                artifact_id = artifact_file.stem
                with open(artifact_file, 'r', encoding='utf-8') as f:
                    self.versions[artifact_id] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading versions for {artifact_file}: {e}")
    
    def _save_versions(self, artifact_id: str):
        """Save version history to disk."""
        version_file = self.versions_dir / f"{artifact_id}.json"
        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(self.versions.get(artifact_id, []), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving versions for {artifact_id}: {e}")
    
    def create_version(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new version of an artifact.
        
        Args:
            artifact_id: Artifact identifier
            artifact_type: Type of artifact
            content: Artifact content
            metadata: Optional metadata (validation_score, model_used, etc.)
        
        Returns:
            Version information
        """
        if artifact_id not in self.versions:
            self.versions[artifact_id] = []
        
        version_number = len(self.versions[artifact_id]) + 1
        version = {
            "version": version_number,
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "is_current": True
        }
        
        # Mark previous versions as not current
        for v in self.versions[artifact_id]:
            v["is_current"] = False
        
        # Add new version
        self.versions[artifact_id].append(version)
        
        # Keep only last 50 versions per artifact
        if len(self.versions[artifact_id]) > 50:
            self.versions[artifact_id] = self.versions[artifact_id][-50:]
        
        # Save to disk
        self._save_versions(artifact_id)
        
        logger.info(f"Created version {version_number} for artifact {artifact_id}")
        return version
    
    def get_versions(self, artifact_id: str) -> List[Dict[str, Any]]:
        """Get all versions for an artifact."""
        return self.versions.get(artifact_id, [])
    
    def get_current_version(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get the current version of an artifact."""
        versions = self.get_versions(artifact_id)
        for version in reversed(versions):
            if version.get("is_current", False):
                return version
        return versions[-1] if versions else None
    
    def get_version(self, artifact_id: str, version_number: int) -> Optional[Dict[str, Any]]:
        """Get a specific version of an artifact."""
        versions = self.get_versions(artifact_id)
        for version in versions:
            if version.get("version") == version_number:
                return version
        return None
    
    def compare_versions(
        self,
        artifact_id: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of an artifact.
        
        Returns:
            Dictionary with differences and statistics
        """
        v1 = self.get_version(artifact_id, version1)
        v2 = self.get_version(artifact_id, version2)
        
        if not v1 or not v2:
            return {"error": "One or both versions not found"}
        
        content1 = v1.get("content", "")
        content2 = v2.get("content", "")
        
        # Simple diff (could be enhanced with proper diff algorithm)
        lines1 = content1.split('\n')
        lines2 = content2.split('\n')
        
        return {
            "version1": {
                "version": version1,
                "created_at": v1.get("created_at"),
                "size": len(content1),
                "lines": len(lines1)
            },
            "version2": {
                "version": version2,
                "created_at": v2.get("created_at"),
                "size": len(content2),
                "lines": len(lines2)
            },
            "differences": {
                "size_diff": len(content2) - len(content1),
                "lines_diff": len(lines2) - len(lines1),
                "similarity": self._calculate_similarity(content1, content2)
            }
        }
    
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings (0-1)."""
        if not content1 and not content2:
            return 1.0
        if not content1 or not content2:
            return 0.0
        
        # Simple character-based similarity
        set1 = set(content1)
        set2 = set(content2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def restore_version(self, artifact_id: str, version_number: int) -> Dict[str, Any]:
        """
        Restore a previous version (creates a new version with old content).
        
        Args:
            artifact_id: Artifact identifier
            version_number: Version to restore
        
        Returns:
            New version information
        """
        old_version = self.get_version(artifact_id, version_number)
        if not old_version:
            return {"error": "Version not found"}
        
        # Create new version with old content
        new_version = self.create_version(
            artifact_id=artifact_id,
            artifact_type=old_version.get("artifact_type", ""),
            content=old_version.get("content", ""),
            metadata={
                **old_version.get("metadata", {}),
                "restored_from": version_number,
                "restored_at": datetime.now().isoformat()
            }
        )
        
        logger.info(f"Restored version {version_number} for artifact {artifact_id}")
        return new_version


# Global service instance
_version_service: Optional[VersionService] = None


def get_version_service() -> VersionService:
    """Get or create global Version Service instance."""
    global _version_service
    if _version_service is None:
        _version_service = VersionService()
    return _version_service

