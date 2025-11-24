"""
Lazy loading utilities for performance optimization.
Provides decorators and utilities for lazy initialization of expensive resources.
"""

import sys
from pathlib import Path
from typing import Any, Optional, Callable, TypeVar, Generic
from functools import wraps
import threading
import logging

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LazyProperty(Generic[T]):
    """
    Lazy property that initializes on first access.
    Thread-safe and supports cleanup.
    """
    
    def __init__(self, factory: Callable[[], T], cleanup: Optional[Callable[[T], None]] = None):
        """
        Initialize lazy property.
        
        Args:
            factory: Factory function to create the value
            cleanup: Optional cleanup function when value is reset
        """
        self._factory = factory
        self._cleanup = cleanup
        self._value: Optional[T] = None
        self._lock = threading.Lock()
        self._initialized = False
    
    def __get__(self, instance: Any, owner: Any) -> T:
        """Get value, initializing if necessary."""
        if self._value is None or not self._initialized:
            with self._lock:
                if self._value is None or not self._initialized:
                    logger.debug(f"Lazy initializing {self._factory.__name__}")
                    self._value = self._factory()
                    self._initialized = True
        return self._value
    
    def reset(self):
        """Reset the value (will be re-initialized on next access)."""
        with self._lock:
            if self._value is not None and self._cleanup:
                try:
                    self._cleanup(self._value)
                except Exception as e:
                    logger.warning(f"Error during lazy property cleanup: {e}")
            self._value = None
            self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if value has been initialized."""
        return self._initialized


def lazy_property(factory: Callable[[], T], cleanup: Optional[Callable[[T], None]] = None) -> LazyProperty[T]:
    """
    Create a lazy property.
    
    Example:
        class MyService:
            expensive_resource = lazy_property(
                lambda: ExpensiveResource(),
                cleanup=lambda r: r.cleanup()
            )
    """
    return LazyProperty(factory, cleanup)


def lazy_init(func: Callable) -> Callable:
    """
    Decorator for lazy initialization of function results.
    Caches result after first call.
    
    Example:
        @lazy_init
        def get_expensive_service():
            return ExpensiveService()
    """
    _cache: dict = {}
    _lock = threading.Lock()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = (args, tuple(sorted(kwargs.items())))
        
        if cache_key not in _cache:
            with _lock:
                if cache_key not in _cache:
                    logger.debug(f"Lazy initializing {func.__name__}")
                    _cache[cache_key] = func(*args, **kwargs)
        
        return _cache[cache_key]
    
    return wrapper


class LazyLoader:
    """
    Utility class for lazy loading modules and resources.
    """
    
    def __init__(self):
        """Initialize lazy loader."""
        self._loaded: dict = {}
        self._lock = threading.Lock()
    
    def load(self, name: str, factory: Callable[[], Any]) -> Any:
        """
        Load a resource lazily.
        
        Args:
            name: Resource name
            factory: Factory function
        
        Returns:
            Loaded resource
        """
        if name not in self._loaded:
            with self._lock:
                if name not in self._loaded:
                    logger.debug(f"Lazy loading {name}")
                    self._loaded[name] = factory()
        return self._loaded[name]
    
    def unload(self, name: str):
        """Unload a resource."""
        with self._lock:
            if name in self._loaded:
                del self._loaded[name]
                logger.debug(f"Unloaded {name}")
    
    def is_loaded(self, name: str) -> bool:
        """Check if resource is loaded."""
        return name in self._loaded


# Global lazy loader instance
_lazy_loader: Optional[LazyLoader] = None


def get_lazy_loader() -> LazyLoader:
    """Get or create global lazy loader instance."""
    global _lazy_loader
    if _lazy_loader is None:
        _lazy_loader = LazyLoader()
    return _lazy_loader

