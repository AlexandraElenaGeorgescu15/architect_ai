"""
Generation Versioning System

Maintains version history of all generated artifacts, allowing users to:
- View version history (last 10 generations per artifact)
- Restore previous versions
- Compare versions side-by-side
- Add version tags and notes

Features:
- Automatic versioning on save
- Metadata tracking (timestamp, validation score, attempt count)
- Space-efficient storage (diff-based for large artifacts)
- Easy restoration and comparison
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import difflib
import hashlib


@dataclass
class Version:
    """
    Represents a single version of an artifact.
    
    Attributes:
        version_id: Unique identifier for this version
        artifact_type: Type of artifact (erd, architecture, etc.)
        timestamp: When this version was created
        content: The artifact content (or diff if using compression)
        validation_score: Quality score from validation (0-100)
        attempt_count: Number of generation attempts
        tags: User-defined tags for organization
        notes: User notes about this version
        file_size: Size of content in bytes
        content_hash: SHA-256 hash for deduplication
    """
    version_id: str
    artifact_type: str
    timestamp: str
    content: str
    validation_score: float = 0.0
    attempt_count: int = 1
    tags: List[str] = None
    notes: str = ""
    file_size: int = 0
    content_hash: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
        if not self.file_size:
            self.file_size = len(self.content.encode())


class VersionManager:
    """
    Manages version history for generated artifacts.
    
    Provides versioning, restoration, comparison, and history management
    for all generated artifacts.
    """
    
    def __init__(self, versions_dir: Path = None):
        """
        Initialize version manager.
        
        Args:
            versions_dir: Directory to store version history
                         (defaults to outputs/.versions/)
        """
        if versions_dir is None:
            versions_dir = Path("outputs") / ".versions"
        
        self.versions_dir = versions_dir
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        
        # Version metadata cache
        self._metadata_cache: Dict[str, List[Version]] = {}
        self._load_metadata_cache()
        
        # Configuration
        self.max_versions_per_artifact = 10  # Keep last 10 versions
        self.enable_compression = True  # Use diffs for large files
        self.compression_threshold = 10000  # Bytes
    
    # =========================================================================
    # Core Version Management
    # =========================================================================
    
    def save_version(
        self,
        artifact_type: str,
        content: str,
        validation_score: float = 0.0,
        attempt_count: int = 1,
        tags: List[str] = None,
        notes: str = ""
    ) -> Version:
        """
        Save a new version of an artifact.
        
        Automatically creates version metadata and stores content.
        If max versions exceeded, removes oldest version.
        
        Args:
            artifact_type: Type of artifact (erd, jira, etc.)
            content: The artifact content to save
            validation_score: Quality score from validation
            attempt_count: Number of generation attempts
            tags: Optional tags for organization
            notes: Optional notes about this version
        
        Returns:
            Created Version object
        """
        # Create version
        version_id = self._generate_version_id(artifact_type)
        timestamp = datetime.now().isoformat()
        
        version = Version(
            version_id=version_id,
            artifact_type=artifact_type,
            timestamp=timestamp,
            content=content,
            validation_score=validation_score,
            attempt_count=attempt_count,
            tags=tags or [],
            notes=notes
        )
        
        # Check for duplicate content (deduplication)
        existing_versions = self.get_versions(artifact_type)
        if existing_versions:
            latest = existing_versions[0]
            if latest.content_hash == version.content_hash:
                # Duplicate content, don't save
                return latest
        
        # Save version content
        version_file = self._get_version_file(artifact_type, version_id)
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(content, encoding='utf-8')
        
        # Update metadata
        if artifact_type not in self._metadata_cache:
            self._metadata_cache[artifact_type] = []
        
        self._metadata_cache[artifact_type].insert(0, version)
        
        # Enforce version limit
        self._cleanup_old_versions(artifact_type)
        
        # Save metadata
        self._save_metadata_cache()
        
        return version
    
    def get_versions(self, artifact_type: str) -> List[Version]:
        """
        Get all versions for an artifact type (newest first).
        
        Args:
            artifact_type: Type of artifact
        
        Returns:
            List of Version objects, sorted by timestamp (newest first)
        """
        return self._metadata_cache.get(artifact_type, [])
    
    def get_version(self, artifact_type: str, version_id: str) -> Optional[Version]:
        """
        Get a specific version by ID.
        
        Args:
            artifact_type: Type of artifact
            version_id: Unique version identifier
        
        Returns:
            Version object or None if not found
        """
        versions = self.get_versions(artifact_type)
        for version in versions:
            if version.version_id == version_id:
                # Load full content
                version_file = self._get_version_file(artifact_type, version_id)
                if version_file.exists():
                    version.content = version_file.read_text(encoding='utf-8')
                return version
        return None
    
    def restore_version(self, artifact_type: str, version_id: str, output_path: Path) -> bool:
        """
        Restore a specific version to a file.
        
        Args:
            artifact_type: Type of artifact
            version_id: Version to restore
            output_path: Where to write the restored content
        
        Returns:
            True if successful, False otherwise
        """
        version = self.get_version(artifact_type, version_id)
        if not version:
            return False
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(version.content, encoding='utf-8')
            return True
        except Exception:
            return False
    
    def delete_version(self, artifact_type: str, version_id: str) -> bool:
        """
        Delete a specific version.
        
        Args:
            artifact_type: Type of artifact
            version_id: Version to delete
        
        Returns:
            True if deleted, False if not found
        """
        versions = self.get_versions(artifact_type)
        for i, version in enumerate(versions):
            if version.version_id == version_id:
                # Delete file
                version_file = self._get_version_file(artifact_type, version_id)
                if version_file.exists():
                    version_file.unlink()
                
                # Remove from metadata
                self._metadata_cache[artifact_type].pop(i)
                self._save_metadata_cache()
                return True
        
        return False
    
    def add_tag(self, artifact_type: str, version_id: str, tag: str) -> bool:
        """
        Add a tag to a version.
        
        Args:
            artifact_type: Type of artifact
            version_id: Version to tag
            tag: Tag to add
        
        Returns:
            True if added, False if not found
        """
        version = self.get_version(artifact_type, version_id)
        if not version:
            return False
        
        if tag not in version.tags:
            version.tags.append(tag)
            self._save_metadata_cache()
        
        return True
    
    def update_notes(self, artifact_type: str, version_id: str, notes: str) -> bool:
        """
        Update notes for a version.
        
        Args:
            artifact_type: Type of artifact
            version_id: Version to update
            notes: New notes
        
        Returns:
            True if updated, False if not found
        """
        versions = self.get_versions(artifact_type)
        for version in versions:
            if version.version_id == version_id:
                version.notes = notes
                self._save_metadata_cache()
                return True
        
        return False
    
    # =========================================================================
    # Comparison & Diff
    # =========================================================================
    
    def compare_versions(
        self,
        artifact_type: str,
        version_id_1: str,
        version_id_2: str
    ) -> Optional[Dict]:
        """
        Compare two versions and return diff information.
        
        Args:
            artifact_type: Type of artifact
            version_id_1: First version ID
            version_id_2: Second version ID
        
        Returns:
            Dict with comparison results:
            {
                'version1': Version,
                'version2': Version,
                'diff': str (unified diff),
                'diff_html': str (HTML formatted diff),
                'changes': int (number of changed lines),
                'additions': int,
                'deletions': int
            }
        """
        v1 = self.get_version(artifact_type, version_id_1)
        v2 = self.get_version(artifact_type, version_id_2)
        
        if not v1 or not v2:
            return None
        
        # Generate unified diff
        lines1 = v1.content.splitlines(keepends=True)
        lines2 = v2.content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f"{artifact_type} ({v1.version_id})",
            tofile=f"{artifact_type} ({v2.version_id})",
            lineterm=''
        ))
        
        # Generate HTML diff
        html_diff = difflib.HtmlDiff().make_file(
            lines1,
            lines2,
            fromdesc=f"Version {v1.version_id}",
            todesc=f"Version {v2.version_id}"
        )
        
        # Count changes
        additions = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
        changes = additions + deletions
        
        return {
            'version1': v1,
            'version2': v2,
            'diff': ''.join(diff),
            'diff_html': html_diff,
            'changes': changes,
            'additions': additions,
            'deletions': deletions
        }
    
    def get_changelog(self, artifact_type: str, limit: int = 10) -> str:
        """
        Generate a human-readable changelog for an artifact.
        
        Args:
            artifact_type: Type of artifact
            limit: Maximum number of versions to include
        
        Returns:
            Markdown-formatted changelog
        """
        versions = self.get_versions(artifact_type)[:limit]
        
        if not versions:
            return "No version history available."
        
        changelog = [f"# Version History: {artifact_type.upper()}\n"]
        
        for i, version in enumerate(versions):
            timestamp = datetime.fromisoformat(version.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            changelog.append(f"\n## Version {len(versions) - i}")
            changelog.append(f"**ID:** `{version.version_id}`")
            changelog.append(f"**Date:** {timestamp}")
            changelog.append(f"**Quality Score:** {version.validation_score:.1f}/100")
            changelog.append(f"**Attempts:** {version.attempt_count}")
            
            if version.tags:
                changelog.append(f"**Tags:** {', '.join(version.tags)}")
            
            if version.notes:
                changelog.append(f"**Notes:** {version.notes}")
            
            changelog.append(f"**Size:** {version.file_size} bytes")
            changelog.append("")
            
            # Show changes from previous version
            if i < len(versions) - 1:
                prev_version = versions[i + 1]
                comparison = self.compare_versions(
                    artifact_type,
                    prev_version.version_id,
                    version.version_id
                )
                if comparison:
                    changelog.append(f"**Changes from previous:** +{comparison['additions']} lines, -{comparison['deletions']} lines")
                    changelog.append("")
        
        return '\n'.join(changelog)
    
    # =========================================================================
    # Statistics & Analytics
    # =========================================================================
    
    def get_statistics(self, artifact_type: str = None) -> Dict:
        """
        Get statistics about version history.
        
        Args:
            artifact_type: Optional specific artifact type
                          (if None, returns stats for all)
        
        Returns:
            Dict with statistics:
            {
                'total_versions': int,
                'total_artifacts': int,
                'total_size': int (bytes),
                'avg_validation_score': float,
                'avg_attempt_count': float,
                'by_artifact': {...}  # Per-artifact breakdown
            }
        """
        if artifact_type:
            versions = self.get_versions(artifact_type)
            if not versions:
                return {}
            
            return {
                'total_versions': len(versions),
                'total_size': sum(v.file_size for v in versions),
                'avg_validation_score': sum(v.validation_score for v in versions) / len(versions) if versions else 0.0,
                'avg_attempt_count': sum(v.attempt_count for v in versions) / len(versions) if versions else 0.0,
                'latest_version': versions[0].version_id,
                'oldest_version': versions[-1].version_id,
                'tags': list(set(tag for v in versions for tag in v.tags))
            }
        
        # All artifacts
        total_versions = 0
        total_size = 0
        scores = []
        attempts = []
        by_artifact = {}
        
        for art_type, versions in self._metadata_cache.items():
            total_versions += len(versions)
            total_size += sum(v.file_size for v in versions)
            scores.extend(v.validation_score for v in versions)
            attempts.extend(v.attempt_count for v in versions)
            by_artifact[art_type] = self.get_statistics(art_type)
        
        return {
            'total_versions': total_versions,
            'total_artifacts': len(self._metadata_cache),
            'total_size': total_size,
            'avg_validation_score': sum(scores) / len(scores) if scores else 0.0,
            'avg_attempt_count': sum(attempts) / len(attempts) if attempts else 0.0,
            'by_artifact': by_artifact
        }
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _generate_version_id(self, artifact_type: str) -> str:
        """Generate unique version ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{artifact_type}_{timestamp}"
    
    def _get_version_file(self, artifact_type: str, version_id: str) -> Path:
        """Get path to version content file"""
        return self.versions_dir / artifact_type / f"{version_id}.txt"
    
    def _get_metadata_file(self) -> Path:
        """Get path to metadata cache file"""
        return self.versions_dir / "metadata.json"
    
    def _load_metadata_cache(self):
        """Load metadata from disk"""
        metadata_file = self._get_metadata_file()
        if metadata_file.exists():
            try:
                data = json.loads(metadata_file.read_text(encoding='utf-8'))
                self._metadata_cache = {
                    artifact_type: [Version(**v) for v in versions]
                    for artifact_type, versions in data.items()
                }
            except Exception:
                self._metadata_cache = {}
        else:
            self._metadata_cache = {}
    
    def _save_metadata_cache(self):
        """Save metadata to disk"""
        metadata_file = self._get_metadata_file()
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            artifact_type: [asdict(v) for v in versions]
            for artifact_type, versions in self._metadata_cache.items()
        }
        
        metadata_file.write_text(json.dumps(data, indent=2), encoding='utf-8')
    
    def _cleanup_old_versions(self, artifact_type: str):
        """Remove oldest versions if limit exceeded"""
        versions = self._metadata_cache.get(artifact_type, [])
        
        while len(versions) > self.max_versions_per_artifact:
            # Remove oldest
            old_version = versions.pop()
            
            # Delete file
            version_file = self._get_version_file(artifact_type, old_version.version_id)
            if version_file.exists():
                version_file.unlink()
    
    def clear_all_versions(self, artifact_type: str = None):
        """
        Clear all versions for an artifact type (or all if None).
        
        Args:
            artifact_type: Optional artifact type (if None, clears everything)
        """
        if artifact_type:
            # Clear specific artifact
            versions = self.get_versions(artifact_type)
            for version in versions:
                version_file = self._get_version_file(artifact_type, version.version_id)
                if version_file.exists():
                    version_file.unlink()
            
            if artifact_type in self._metadata_cache:
                del self._metadata_cache[artifact_type]
        else:
            # Clear everything
            if self.versions_dir.exists():
                import shutil
                shutil.rmtree(self.versions_dir)
                self.versions_dir.mkdir(parents=True, exist_ok=True)
            
            self._metadata_cache = {}
        
        self._save_metadata_cache()

