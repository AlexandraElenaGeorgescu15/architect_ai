"""
RAG Context Caching System
Supports in-memory and Redis backends
"""

import hashlib
import pickle
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

class CacheBackend:
    """Base class for cache backends"""
    
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError
    
    def set(self, key: str, value: str, ttl: int = 3600):
        raise NotImplementedError
    
    def delete(self, key: str):
        raise NotImplementedError
    
    def clear(self):
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """In-memory cache implementation"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            entry = self.cache[key]
            # Check if expired
            if datetime.now() < entry['expires_at']:
                return entry['value']
            else:
                # Expired, remove it
                del self.cache[key]
        return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
            'created_at': datetime.now()
        }
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = len(self.cache)
        expired = sum(1 for entry in self.cache.values() 
                     if datetime.now() >= entry['expires_at'])
        return {
            'total_entries': total,
            'active_entries': total - expired,
            'expired_entries': expired
        }


class RedisCache(CacheBackend):
    """Redis cache implementation"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.available = True
            # Test connection
            self.redis_client.ping()
            print("[OK] Connected to Redis cache")
        except Exception as e:
            print(f"[WARN] Redis not available: {e}. Falling back to memory cache.")
            self.available = False
            self.fallback = MemoryCache()
    
    def get(self, key: str) -> Optional[str]:
        if not self.available:
            return self.fallback.get(key)
        
        try:
            value = self.redis_client.get(f"rag:{key}")
            return value
        except Exception as e:
            print(f"[WARN] Redis get error: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = 3600):
        if not self.available:
            return self.fallback.set(key, value, ttl)
        
        try:
            self.redis_client.setex(f"rag:{key}", ttl, value)
        except Exception as e:
            print(f"[WARN] Redis set error: {e}")
    
    def delete(self, key: str):
        if not self.available:
            return self.fallback.delete(key)
        
        try:
            self.redis_client.delete(f"rag:{key}")
        except Exception as e:
            print(f"[WARN] Redis delete error: {e}")
    
    def clear(self, pattern: str = "*"):
        if not self.available:
            return self.fallback.clear()
        
        try:
            for key in self.redis_client.scan_iter(f"rag:{pattern}"):
                self.redis_client.delete(key)
        except Exception as e:
            print(f"[WARN] Redis clear error: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.available:
            return self.fallback.stats()
        
        try:
            info = self.redis_client.info('stats')
            return {
                'total_keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0)
            }
        except Exception:
            return {}


class RAGCache:
    """High-level RAG caching interface"""
    
    def __init__(self, backend: str = "memory", redis_url: str = None):
        if backend == "redis" and redis_url:
            self.backend = RedisCache(redis_url)
        else:
            self.backend = MemoryCache()
        
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, query: str, context_type: str = "default") -> str:
        """Create cache key from query"""
        content = f"{context_type}:{query}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_context(self, query: str, context_type: str = "default") -> Optional[str]:
        """Get cached RAG context"""
        key = self._make_key(query, context_type)
        value = self.backend.get(key)
        
        if value:
            self.hits += 1
            print(f"[CACHE HIT] Retrieved cached context for query")
            return value
        else:
            self.misses += 1
            return None
    
    def set_context(self, query: str, context: str, context_type: str = "default", ttl: int = 3600):
        """Cache RAG context"""
        key = self._make_key(query, context_type)
        self.backend.set(key, context, ttl)
    
    def invalidate(self, query: str = None, context_type: str = None):
        """Invalidate cache"""
        if query:
            key = self._make_key(query, context_type or "default")
            self.backend.delete(key)
        else:
            self.backend.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        backend_stats = self.backend.stats()
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'backend': backend_stats
        }


# Global cache instance
_cache_instance = None

def get_cache(backend: str = "memory", redis_url: str = None) -> RAGCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RAGCache(backend, redis_url)
    return _cache_instance

