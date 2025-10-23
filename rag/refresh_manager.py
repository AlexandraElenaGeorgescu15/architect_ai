"""
RAG Index Refresh Manager

Manages RAG index freshness, detects staleness, and provides
automatic refresh recommendations.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib


class RAGRefreshManager:
    """Manage RAG index freshness and refresh strategies"""
    
    def __init__(self, index_path: str = "rag/index"):
        self.index_path = Path(index_path)
        self.manifest_path = self.index_path / "manifest.json"
        self.metadata_path = self.index_path / "metadata.json"
    
    def check_freshness(self) -> Dict[str, Any]:
        """
        Check RAG index freshness and return detailed status.
        
        Returns:
            Dict with:
            - is_fresh: bool
            - last_updated: datetime or None
            - hours_old: float
            - indexed_files: int
            - recommendation: str
        """
        if not self.manifest_path.exists():
            return {
                "is_fresh": False,
                "last_updated": None,
                "hours_old": float('inf'),
                "indexed_files": 0,
                "recommendation": "No RAG index found. Run: python rag/ingest.py"
            }
        
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding='utf-8'))
            last_updated_str = manifest.get('last_updated')
            indexed_files = manifest.get('count', 0)
            
            if not last_updated_str:
                # Old manifest format - use file modification time
                last_updated = datetime.fromtimestamp(self.manifest_path.stat().st_mtime)
            else:
                last_updated = datetime.fromisoformat(last_updated_str)
            
            hours_old = (datetime.now() - last_updated).total_seconds() / 3600
            
            # Freshness thresholds
            if hours_old < 24:
                is_fresh = True
                recommendation = "✅ RAG index is fresh"
            elif hours_old < 72:
                is_fresh = False
                recommendation = "⚠️ RAG index is 1-3 days old. Consider refreshing for latest context."
            else:
                is_fresh = False
                recommendation = f"🔴 RAG index is {int(hours_old/24)} days old. Refresh recommended: python rag/ingest.py"
            
            return {
                "is_fresh": is_fresh,
                "last_updated": last_updated,
                "hours_old": hours_old,
                "indexed_files": indexed_files,
                "recommendation": recommendation
            }
            
        except Exception as e:
            return {
                "is_fresh": False,
                "last_updated": None,
                "hours_old": float('inf'),
                "indexed_files": 0,
                "recommendation": f"❌ Error reading RAG index: {str(e)}"
            }
    
    def get_indexed_repositories(self) -> List[Dict[str, Any]]:
        """
        Get list of repositories that have been indexed.
        
        Returns:
            List of dicts with repo info (name, path, last_indexed, file_count)
        """
        if not self.metadata_path.exists():
            return []
        
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding='utf-8'))
            return metadata.get('repositories', [])
        except Exception:
            return []
    
    def record_index_completion(self, repo_path: str, file_count: int, repo_name: str = None):
        """
        Record successful index completion.
        
        Args:
            repo_path: Path to indexed repository
            file_count: Number of files indexed
            repo_name: Optional repository name
        """
        # Update manifest
        manifest = {
            "count": file_count,
            "last_updated": datetime.now().isoformat()
        }
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        
        # Update metadata
        repo_path_resolved = Path(repo_path).resolve()
        repo_name = repo_name or repo_path_resolved.name
        
        metadata = {}
        if self.metadata_path.exists():
            try:
                metadata = json.loads(self.metadata_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        
        if 'repositories' not in metadata:
            metadata['repositories'] = []
        
        # Update or add repository entry
        repo_entry = {
            "name": repo_name,
            "path": str(repo_path_resolved),
            "last_indexed": datetime.now().isoformat(),
            "file_count": file_count
        }
        
        # Remove old entry if exists
        metadata['repositories'] = [r for r in metadata['repositories'] if r['path'] != str(repo_path_resolved)]
        metadata['repositories'].append(repo_entry)
        
        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    
    def get_file_hash_manifest(self, repo_path: str) -> Dict[str, str]:
        """
        Get hash manifest of all indexed files for incremental updates.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Dict mapping file paths to their content hashes
        """
        hash_manifest_path = self.index_path / "file_hashes.json"
        
        if not hash_manifest_path.exists():
            return {}
        
        try:
            manifest = json.loads(hash_manifest_path.read_text(encoding='utf-8'))
            return manifest.get(str(Path(repo_path).resolve()), {})
        except Exception:
            return {}
    
    def update_file_hash_manifest(self, repo_path: str, file_hashes: Dict[str, str]):
        """
        Update hash manifest for incremental updates.
        
        Args:
            repo_path: Path to repository
            file_hashes: Dict mapping file paths to content hashes
        """
        hash_manifest_path = self.index_path / "file_hashes.json"
        
        manifest = {}
        if hash_manifest_path.exists():
            try:
                manifest = json.loads(hash_manifest_path.read_text(encoding='utf-8'))
            except Exception:
                pass
        
        manifest[str(Path(repo_path).resolve())] = file_hashes
        
        self.index_path.mkdir(parents=True, exist_ok=True)
        hash_manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    
    def detect_changed_files(self, repo_path: str, current_files: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Detect which files have changed since last indexing.
        
        Args:
            repo_path: Path to repository
            current_files: Dict mapping current file paths to their content hashes
            
        Returns:
            Dict with:
            - added: List of new files
            - modified: List of changed files
            - deleted: List of removed files
        """
        old_hashes = self.get_file_hash_manifest(repo_path)
        
        added = [f for f in current_files if f not in old_hashes]
        modified = [f for f in current_files if f in old_hashes and current_files[f] != old_hashes[f]]
        deleted = [f for f in old_hashes if f not in current_files]
        
        return {
            "added": added,
            "modified": modified,
            "deleted": deleted
        }
    
    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Compute SHA-256 hash of file content.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file hash
        """
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""


# Global refresh manager instance
_refresh_manager = None

def get_refresh_manager() -> RAGRefreshManager:
    """Get or create global refresh manager"""
    global _refresh_manager
    if _refresh_manager is None:
        _refresh_manager = RAGRefreshManager()
    return _refresh_manager

