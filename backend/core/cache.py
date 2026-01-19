"""
Centralized caching system for backend services.
Provides Redis-backed caching with in-memory fallback.
"""

import sys
from pathlib import Path
from typing import Any, Optional, Dict, Callable
import json
import hashlib
import logging
from functools import wraps
from datetime import timedelta

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache only.")


class CacheManager:
    """
    Centralized cache manager with Redis backend and in-memory fallback.
    
    Features:
    - Redis-backed distributed caching
    - In-memory fallback when Redis unavailable
    - TTL support
    - Key prefixing
    - Cache invalidation
    """
    
    def __init__(self):
        """Initialize cache manager."""
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        if REDIS_AVAILABLE and settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
                self.redis_client = None
        
        self.key_prefix = "architect_ai:"
    
    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        full_key = self._make_key(key)
        
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(full_key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory
        if full_key in self.memory_cache:
            entry = self.memory_cache[full_key]
            # Check TTL
            if entry.get("expires_at") and entry["expires_at"] > self._now():
                return entry["value"]
            else:
                # Expired, remove it
                del self.memory_cache[full_key]
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        
        Returns:
            True if successful
        """
        full_key = self._make_key(key)
        ttl = ttl or 3600  # Default 1 hour
        
        # Try Redis first
        if self.redis_client:
            try:
                serialized = json.dumps(value)
                self.redis_client.setex(full_key, ttl, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Fallback to memory
        expires_at = self._now() + ttl if ttl else None
        self.memory_cache[full_key] = {
            "value": value,
            "expires_at": expires_at
        }
        
        # Clean up expired entries periodically
        if len(self.memory_cache) > 10000:
            self._cleanup_memory_cache()
        
        return True
    
    async def set_async(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Async wrapper for set - allows calling from async contexts.
        The underlying cache operation is synchronous but this allows
        consistent async/await patterns in the codebase.
        """
        return self.set(key, value, ttl)
    
    async def get_async(self, key: str) -> Optional[Any]:
        """
        Async wrapper for get - allows calling from async contexts.
        """
        return self.get(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if successful
        """
        full_key = self._make_key(key)
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.delete(full_key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        # Remove from memory
        if full_key in self.memory_cache:
            del self.memory_cache[full_key]
        
        return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
        
        Returns:
            Number of keys deleted
        """
        count = 0
        full_pattern = self._make_key(pattern)
        
        # Try Redis first
        if self.redis_client:
            try:
                keys = self.redis_client.keys(full_pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis pattern delete error: {e}")
        
        # Remove from memory
        memory_keys = [k for k in self.memory_cache.keys() if self._match_pattern(k, full_pattern)]
        for key in memory_keys:
            del self.memory_cache[key]
            count += 1
        
        return count
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for memory cache."""
        if "*" in pattern:
            pattern = pattern.replace("*", ".*")
            import re
            return bool(re.match(pattern, key))
        return key == pattern
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        now = self._now()
        expired = [
            k for k, v in self.memory_cache.items()
            if v.get("expires_at") and v["expires_at"] <= now
        ]
        for key in expired:
            del self.memory_cache[key]
    
    def _now(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        stats = {
            "backend": "redis" if self.redis_client else "memory",
            "memory_entries": len(self.memory_cache)
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info("memory")
                stats["redis_memory_used"] = info.get("used_memory_human", "unknown")
                stats["redis_keys"] = self.redis_client.dbsize()
            except Exception as e:
                logger.warning(f"Redis stats error: {e}")
        
        return stats


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    # Create deterministic key from arguments
    key_parts = []
    
    # Add positional args
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif isinstance(arg, (dict, list)):
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add keyword args
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        elif isinstance(v, (dict, list)):
            key_parts.append(f"{k}:{json.dumps(v, sort_keys=True)}")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    # Hash the key for consistent length
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_func: Optional function to generate cache key
    
    Example:
        @cached(ttl=1800, key_prefix="context:")
        async def build_context(meeting_notes: str):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)
            
            if key_prefix:
                cache_key_str = f"{key_prefix}{cache_key_str}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key_str, result, ttl=ttl)
            logger.debug(f"Cache set: {cache_key_str}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                cache_key_str = cache_key(*args, **kwargs)
            
            if key_prefix:
                cache_key_str = f"{key_prefix}{cache_key_str}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_value
            
            # Call function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key_str, result, ttl=ttl)
            logger.debug(f"Cache set: {cache_key_str}")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator



