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
        # Use settings.base_path to ensure correct path resolution regardless of CWD
        base_path = Path(settings.base_path)
        self.versions_dir = base_path / "data" / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory version store
        self.versions: Dict[str, List[Dict[str, Any]]] = {}  # artifact_id -> versions
        
        # Load existing versions
        self._load_versions()
        
        # Auto-migrate legacy timestamped artifacts on startup
        self._auto_migrate_legacy()
        
        logger.info("Version Service initialized")
    
    def _auto_migrate_legacy(self):
        """Automatically migrate legacy timestamped artifacts on startup."""
        preview = self.get_migration_preview()
        if preview.get("needs_migration"):
            logger.info(f"🔄 Auto-migrating {len(preview.get('legacy_groups', {}))} legacy artifact groups...")
            result = self.migrate_legacy_versions()
            logger.info(f"✅ Auto-migration complete: {result.get('migrated_versions', 0)} versions consolidated")
    
    def _load_versions(self):
        """Load version history from disk."""
        logger.info(f"Loading versions from {self.versions_dir}")
        count = 0
        for artifact_file in self.versions_dir.glob("*.json"):
            try:
                artifact_id = artifact_file.stem
                with open(artifact_file, 'r', encoding='utf-8') as f:
                    self.versions[artifact_id] = json.load(f)
                    count += 1
            except Exception as e:
                logger.error(f"Error loading versions for {artifact_file}: {e}")
        logger.info(f"Loaded versions for {count} artifacts")
    
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
    
    def migrate_legacy_versions(self) -> Dict[str, Any]:
        """
        Migrate legacy timestamped artifact IDs to stable artifact type IDs.
        
        Legacy format: mermaid_erd_20251209_123456
        New format: mermaid_erd
        
        This consolidates all versions of the same artifact type into one stable ID,
        allowing proper versioning (v1, v2, v3, etc.) instead of each generation being v1.
        
        Returns:
            Migration statistics
        """
        import re
        
        # Pattern to match timestamped artifact IDs
        # e.g., mermaid_erd_20251209_123456, html_erd_20251208_094523
        timestamp_pattern = re.compile(r'^(.+)_(\d{8}_\d{6})$')
        
        # Group legacy artifacts by their base type
        legacy_groups: Dict[str, List[str]] = {}  # base_type -> list of artifact_ids
        stable_ids = []  # Already stable IDs
        
        for artifact_id in list(self.versions.keys()):
            match = timestamp_pattern.match(artifact_id)
            if match:
                base_type = match.group(1)  # e.g., "mermaid_erd"
                if base_type not in legacy_groups:
                    legacy_groups[base_type] = []
                legacy_groups[base_type].append(artifact_id)
            else:
                stable_ids.append(artifact_id)
        
        migrated_count = 0
        artifacts_consolidated = 0
        
        # Process each legacy group
        for base_type, legacy_ids in legacy_groups.items():
            # Sort by timestamp (embedded in the ID) to preserve chronological order
            legacy_ids.sort()
            
            # Collect all versions from legacy artifacts
            all_legacy_versions = []
            for legacy_id in legacy_ids:
                versions = self.versions.get(legacy_id, [])
                for v in versions:
                    # Add original artifact_id to metadata for reference
                    v["metadata"] = v.get("metadata", {})
                    v["metadata"]["migrated_from"] = legacy_id
                    all_legacy_versions.append(v)
            
            if not all_legacy_versions:
                continue
            
            # Sort all versions by created_at
            all_legacy_versions.sort(key=lambda v: v.get("created_at", ""))
            
            # Check if we already have a stable artifact with this base_type
            if base_type in self.versions:
                # Append to existing stable artifact
                existing_versions = self.versions[base_type]
                start_version = len(existing_versions) + 1
            else:
                # Create new stable artifact
                self.versions[base_type] = []
                existing_versions = self.versions[base_type]
                start_version = 1
            
            # Mark all existing versions as not current
            for v in existing_versions:
                v["is_current"] = False
            
            # Add all legacy versions with renumbered version numbers
            for i, legacy_version in enumerate(all_legacy_versions):
                new_version_num = start_version + i
                legacy_version["version"] = new_version_num
                legacy_version["artifact_id"] = base_type
                legacy_version["is_current"] = (i == len(all_legacy_versions) - 1)  # Last one is current
                existing_versions.append(legacy_version)
                migrated_count += 1
            
            # Save the consolidated stable artifact
            self._save_versions(base_type)
            
            # Delete legacy artifact files
            for legacy_id in legacy_ids:
                legacy_file = self.versions_dir / f"{legacy_id}.json"
                if legacy_file.exists():
                    legacy_file.unlink()
                    logger.info(f"Deleted legacy version file: {legacy_file}")
                # Remove from in-memory store
                if legacy_id in self.versions:
                    del self.versions[legacy_id]
            
            artifacts_consolidated += len(legacy_ids)
            logger.info(f"Migrated {len(legacy_ids)} legacy artifacts to {base_type} with {len(all_legacy_versions)} total versions")
        
        logger.info(f"Migration complete: {migrated_count} versions migrated, {artifacts_consolidated} legacy artifacts consolidated")
        
        return {
            "success": True,
            "migrated_versions": migrated_count,
            "artifacts_consolidated": artifacts_consolidated,
            "legacy_groups": len(legacy_groups),
            "stable_ids_unchanged": len(stable_ids)
        }
    
    def get_migration_preview(self) -> Dict[str, Any]:
        """
        Preview what would be migrated without actually migrating.
        
        Returns:
            Preview of migration that would occur
        """
        import re
        
        timestamp_pattern = re.compile(r'^(.+)_(\d{8}_\d{6})$')
        
        legacy_groups: Dict[str, List[Dict[str, Any]]] = {}
        stable_artifacts = []
        
        for artifact_id, versions in self.versions.items():
            match = timestamp_pattern.match(artifact_id)
            if match:
                base_type = match.group(1)
                if base_type not in legacy_groups:
                    legacy_groups[base_type] = []
                legacy_groups[base_type].append({
                    "artifact_id": artifact_id,
                    "version_count": len(versions),
                    "created_at": versions[0].get("created_at") if versions else None
                })
            else:
                stable_artifacts.append({
                    "artifact_id": artifact_id,
                    "version_count": len(versions)
                })
        
        return {
            "legacy_groups": {
                base_type: {
                    "artifacts": artifacts,
                    "total_versions": sum(a["version_count"] for a in artifacts)
                }
                for base_type, artifacts in legacy_groups.items()
            },
            "stable_artifacts": stable_artifacts,
            "needs_migration": len(legacy_groups) > 0
        }
    
    def delete_all_versions(self, artifact_id: str) -> Dict[str, Any]:
        """
        Delete all versions for an artifact.
        
        Args:
            artifact_id: Artifact identifier
        
        Returns:
            Deletion result
        """
        if artifact_id not in self.versions:
            return {"error": "Artifact not found"}
        
        version_count = len(self.versions[artifact_id])
        
        # Remove from memory
        del self.versions[artifact_id]
        
        # Remove from disk
        version_file = self.versions_dir / f"{artifact_id}.json"
        if version_file.exists():
            version_file.unlink()
        
        logger.info(f"Deleted all {version_count} versions for artifact {artifact_id}")
        return {
            "success": True,
            "artifact_id": artifact_id,
            "versions_deleted": version_count
        }


# Global service instance
_version_service: Optional[VersionService] = None


def get_version_service() -> VersionService:
    """Get or create global Version Service instance."""
    global _version_service
    if _version_service is None:
        _version_service = VersionService()
    return _version_service

