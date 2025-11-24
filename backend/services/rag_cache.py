"""
RAG Cache Service - Refactored from components/rag_cache.py
Intelligent caching for RAG retrieval results.
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import json
import logging
import os

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)


class RAGCache:
    """
    Smart caching for RAG context retrieval.
    
    Caches results based on:
    - Meeting notes hash
    - Repository modification time
    
    This ensures cache invalidation when code changes.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, repo_dir: Optional[Path] = None):
        """
        Initialize RAG cache.
        
        Args:
            cache_dir: Directory to store cache files (defaults to outputs/.cache)
            repo_dir: Repository root directory to monitor (defaults to current directory)
        """
        self.cache_dir = cache_dir or Path("outputs/.cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.repo_dir = repo_dir or Path(".")
        self._memory_cache: Dict[str, Any] = {}
    
    def _get_repo_modification_time(self) -> float:
        """
        Get most recent modification time of repository files.
        
        Returns:
            Unix timestamp of most recent file modification
        """
        try:
            max_mtime = 0.0
            
            # Check common code directories
            code_dirs = ["src", "lib", "app", "components", "services", "api"]
            
            for code_dir in code_dirs:
                dir_path = self.repo_dir / code_dir
                if dir_path.exists():
                    for file_path in dir_path.rglob("*"):
                        if file_path.is_file():
                            try:
                                mtime = file_path.stat().st_mtime
                                max_mtime = max(max_mtime, mtime)
                            except (OSError, PermissionError):
                                continue
            
            # Also check root level files
            for file_path in self.repo_dir.glob("*.py"):
                if file_path.is_file():
                    try:
                        mtime = file_path.stat().st_mtime
                        max_mtime = max(max_mtime, mtime)
                    except (OSError, PermissionError):
                        continue
            
            return max_mtime
            
        except Exception as e:
            logger.warning(f"Error getting repo modification time: {e}")
            return 0.0
    
    def _get_hash(self, meeting_notes: str, repo_mtime: float) -> str:
        """
        Generate cache key hash from meeting notes and repo modification time.
        
        Args:
            meeting_notes: Meeting notes content
            repo_mtime: Repository modification time
        
        Returns:
            SHA1 hash string
        """
        combined = f"{meeting_notes}::{repo_mtime}"
        return hashlib.sha1(combined.encode('utf-8')).hexdigest()
    
    def get_context(self, meeting_notes: str) -> Optional[str]:
        """
        Get cached RAG context.
        
        Args:
            meeting_notes: Meeting notes content
        
        Returns:
            Cached context string or None if not found
        """
        repo_mtime = self._get_repo_modification_time()
        cache_key = self._get_hash(meeting_notes, repo_mtime)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            logger.debug("RAG cache hit (memory)")
            return self._memory_cache[cache_key]
        
        # Check disk cache
        cache_file = self.cache_dir / f"rag_{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verify repo_mtime matches (safety check)
                if data.get("repo_mtime") == repo_mtime:
                    context = data.get("context", "")
                    # Store in memory cache
                    self._memory_cache[cache_key] = context
                    logger.debug("RAG cache hit (disk)")
                    return context
                else:
                    # Repo changed, invalidate this cache entry
                    cache_file.unlink()
                    logger.debug("RAG cache invalidated (repo changed)")
                    
            except Exception as e:
                logger.warning(f"Error reading cache file: {e}")
        
        logger.debug("RAG cache miss")
        return None
    
    def set_context(self, meeting_notes: str, context: str):
        """
        Cache RAG context.
        
        Args:
            meeting_notes: Meeting notes content
            context: RAG context to cache
        """
        repo_mtime = self._get_repo_modification_time()
        cache_key = self._get_hash(meeting_notes, repo_mtime)
        
        # Store in memory cache
        self._memory_cache[cache_key] = context
        
        # Store in disk cache
        cache_file = self.cache_dir / f"rag_{cache_key}.json"
        try:
            data = {
                "meeting_notes": meeting_notes[:100],  # Store first 100 chars for debugging
                "context": context,
                "repo_mtime": repo_mtime,
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"RAG context cached: {cache_key}")
            
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")
    
    def invalidate(self, meeting_notes: Optional[str] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            meeting_notes: Specific notes to invalidate, or None for all
        
        Returns:
            Number of entries invalidated
        """
        if meeting_notes:
            # Invalidate specific entry
            repo_mtime = self._get_repo_modification_time()
            cache_key = self._get_hash(meeting_notes, repo_mtime)
            
            # Clear from memory
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            # Clear from disk
            cache_file = self.cache_dir / f"rag_{cache_key}.json"
            if cache_file.exists():
                cache_file.unlink()
            
            return 1
        else:
            # Invalidate all entries
            count = 0
            
            # Clear memory cache
            count += len(self._memory_cache)
            self._memory_cache.clear()
            
            # Clear disk cache
            for cache_file in self.cache_dir.glob("rag_*.json"):
                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    logger.warning(f"Error deleting cache file {cache_file}: {e}")
            
            logger.info(f"Invalidated {count} cache entries")
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        disk_count = len(list(self.cache_dir.glob("rag_*.json")))
        
        return {
            "memory_entries": len(self._memory_cache),
            "disk_entries": disk_count,
            "cache_dir": str(self.cache_dir)
        }


# Global cache instance
_cache: Optional[RAGCache] = None


def get_cache() -> RAGCache:
    """Get or create global RAG cache instance."""
    global _cache
    if _cache is None:
        _cache = RAGCache()
    return _cache


def get_rag_cache() -> RAGCache:
    """Alias for get_cache() for backward compatibility."""
    return get_cache()



