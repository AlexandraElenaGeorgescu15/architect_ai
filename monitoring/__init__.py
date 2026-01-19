"""
Monitoring module - provides metrics decorators and utilities.
Wraps backend.core.metrics for easy access.
"""

import sys
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any
import time
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Try to import the actual metrics system
try:
    from backend.core.metrics import get_collector
    _metrics_collector = get_collector()
    METRICS_AVAILABLE = True
except ImportError:
    _metrics_collector = None
    METRICS_AVAILABLE = False
    logger.warning("Metrics collector not available, using no-op stubs")


def get_metrics():
    """Get the metrics collector instance."""
    return _metrics_collector


def timer(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to time function execution.
    
    Args:
        metric_name: Name of the timer metric
        tags: Optional tags for filtering
    
    Usage:
        @timer("my_function_duration")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if _metrics_collector:
                    _metrics_collector.timer_record(metric_name, duration)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if _metrics_collector:
                    _metrics_collector.timer_record(metric_name, duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


def counter(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to count function calls.
    
    Args:
        metric_name: Name of the counter metric
        tags: Optional tags for filtering
    
    Usage:
        @counter("my_function_calls")
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if _metrics_collector:
                _metrics_collector.increment(metric_name, tags=tags)
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if _metrics_collector:
                _metrics_collector.increment(metric_name, tags=tags)
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


def histogram(metric_name: str, value_extractor=None, tags: Optional[Dict[str, str]] = None):
    """
    Decorator to record values in a histogram.
    
    Args:
        metric_name: Name of the histogram metric
        value_extractor: Optional function to extract value from result
        tags: Optional tags for filtering
    
    Usage:
        @histogram("response_size", value_extractor=lambda r: len(r))
        def get_data():
            return "data"
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if _metrics_collector:
                value = value_extractor(result) if value_extractor else result
                if isinstance(value, (int, float)):
                    _metrics_collector.histogram(metric_name, value, tags=tags)
            return result
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if _metrics_collector:
                value = value_extractor(result) if value_extractor else result
                if isinstance(value, (int, float)):
                    _metrics_collector.histogram(metric_name, value, tags=tags)
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


__all__ = ['get_metrics', 'timer', 'counter', 'histogram', 'METRICS_AVAILABLE']
