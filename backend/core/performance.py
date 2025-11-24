"""
Performance monitoring and optimization utilities.
"""

import sys
from pathlib import Path
import time
import logging
from functools import wraps
from typing import Callable, Any, Dict, Optional
from contextlib import contextmanager

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


@contextmanager
def timer(operation_name: str):
    """
    Context manager for timing operations.
    
    Example:
        with timer("context_build"):
            result = build_context(...)
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.info(f"{operation_name} took {elapsed:.3f}s")


def timed(operation_name: Optional[str] = None):
    """
    Decorator for timing function execution.
    
    Example:
        @timed("build_context")
        async def build_context(...):
            ...
    """
    def decorator(func: Callable):
        name = operation_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start
                logger.info(f"{name} took {elapsed:.3f}s")
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start
                logger.info(f"{name} took {elapsed:.3f}s")
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class PerformanceMonitor:
    """
    Performance monitoring for tracking operation metrics.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, list] = {}
    
    def record(self, operation: str, duration: float):
        """
        Record operation duration.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
        
        # Keep only last 1000 measurements
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """
        Get statistics for an operation.
        
        Args:
            operation: Operation name
        
        Returns:
            Dictionary with min, max, avg, p50, p95, p99
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = sorted(self.metrics[operation])
        n = len(durations)
        
        return {
            "count": n,
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / n,
            "p50": durations[int(n * 0.5)],
            "p95": durations[int(n * 0.95)],
            "p99": durations[int(n * 0.99)]
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to their stats
        """
        return {
            op: self.get_stats(op)
            for op in self.metrics.keys()
        }


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

