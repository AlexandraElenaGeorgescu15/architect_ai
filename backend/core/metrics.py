"""
Metrics collection system for monitoring and observability.
Provides counters, histograms, gauges, and timers for performance tracking.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import time
import threading
import logging
from functools import wraps
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralized metrics collection system.
    
    Features:
    - Counters (increments/decrements)
    - Histograms (value distributions)
    - Gauges (current values)
    - Timers (duration tracking)
    - Automatic aggregation and reporting
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._timer_start: Dict[str, float] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Aggregation window (default: 1 minute)
        self.aggregation_window = 60
        self._last_aggregation = time.time()
        
        # Keep last N samples for histograms/timers
        self.max_samples = 1000
        
        logger.info("Metrics Collector initialized")
    
    def increment(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Amount to increment (default: 1)
            tags: Optional tags for filtering
        """
        key = self._make_key(metric_name, tags)
        with self._lock:
            self._counters[key] += value
    
    def decrement(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Decrement a counter metric.
        
        Args:
            metric_name: Name of the metric
            value: Amount to decrement (default: 1)
            tags: Optional tags for filtering
        """
        key = self._make_key(metric_name, tags)
        with self._lock:
            self._counters[key] -= value
    
    def record(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record a value in a histogram.
        
        Args:
            metric_name: Name of the metric
            value: Value to record
            tags: Optional tags for filtering
        """
        key = self._make_key(metric_name, tags)
        with self._lock:
            self._histograms[key].append(value)
            # Limit samples
            if len(self._histograms[key]) > self.max_samples:
                self._histograms[key] = self._histograms[key][-self.max_samples:]
    
    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric (current value).
        
        Args:
            metric_name: Name of the metric
            value: Current value
            tags: Optional tags for filtering
        """
        key = self._make_key(metric_name, tags)
        with self._lock:
            self._gauges[key] = value
    
    def start_timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """
        Start a timer.
        
        Args:
            metric_name: Name of the metric
            tags: Optional tags for filtering
        
        Returns:
            Timer ID for stopping the timer
        """
        timer_id = f"{metric_name}_{time.time()}_{id(self)}"
        key = self._make_key(metric_name, tags)
        with self._lock:
            self._timer_start[timer_id] = (key, time.time())
        return timer_id
    
    def stop_timer(self, timer_id: str):
        """
        Stop a timer and record the duration.
        
        Args:
            timer_id: Timer ID from start_timer
        """
        with self._lock:
            if timer_id in self._timer_start:
                key, start_time = self._timer_start.pop(timer_id)
                duration = time.time() - start_time
                self._timers[key].append(duration)
                # Limit samples
                if len(self._timers[key]) > self.max_samples:
                    self._timers[key] = self._timers[key][-self.max_samples:]
    
    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        Context manager for timing code blocks.
        
        Example:
            with metrics.timer("generation_time"):
                # code to time
                pass
        """
        return TimerContext(self, metric_name, tags)
    
    def _make_key(self, metric_name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create metric key with tags."""
        if not tags:
            return metric_name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregated statistics for all metrics.
        
        Returns:
            Dictionary with metric statistics
        """
        with self._lock:
            stats = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "timers": {}
            }
            
            # Calculate histogram statistics
            for key, values in self._histograms.items():
                if values:
                    stats["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99)
                    }
            
            # Calculate timer statistics
            for key, values in self._timers.items():
                if values:
                    stats["timers"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99),
                        "total": sum(values)
                    }
            
            return stats
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def reset(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self._timers.clear()
            self._timer_start.clear()
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Prometheus-formatted metrics string
        """
        lines = []
        stats = self.get_stats()
        
        # Export counters
        for key, value in stats["counters"].items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {value}")
        
        # Export gauges
        for key, value in stats["gauges"].items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {value}")
        
        # Export histogram summaries
        for key, stats_dict in stats["histograms"].items():
            lines.append(f"# TYPE {key} histogram")
            lines.append(f"{key}_count {stats_dict['count']}")
            lines.append(f"{key}_sum {stats_dict['mean'] * stats_dict['count']}")
            lines.append(f"{key}_mean {stats_dict['mean']}")
            lines.append(f"{key}_min {stats_dict['min']}")
            lines.append(f"{key}_max {stats_dict['max']}")
            lines.append(f"{key}_p50 {stats_dict['p50']}")
            lines.append(f"{key}_p95 {stats_dict['p95']}")
            lines.append(f"{key}_p99 {stats_dict['p99']}")
        
        # Export timer summaries
        for key, stats_dict in stats["timers"].items():
            lines.append(f"# TYPE {key} histogram")
            lines.append(f"{key}_count {stats_dict['count']}")
            lines.append(f"{key}_sum {stats_dict['total']}")
            lines.append(f"{key}_mean {stats_dict['mean']}")
            lines.append(f"{key}_min {stats_dict['min']}")
            lines.append(f"{key}_max {stats_dict['max']}")
            lines.append(f"{key}_p50 {stats_dict['p50']}")
            lines.append(f"{key}_p95 {stats_dict['p95']}")
            lines.append(f"{key}_p99 {stats_dict['p99']}")
        
        return "\n".join(lines)


class TimerContext:
    """Context manager for timing code blocks."""
    
    def __init__(self, collector: MetricsCollector, metric_name: str, tags: Optional[Dict[str, str]]):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags
        self.timer_id = None
    
    def __enter__(self):
        self.timer_id = self.collector.start_timer(self.metric_name, self.tags)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timer_id:
            self.collector.stop_timer(self.timer_id)


def timed(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """
    Decorator for timing function execution.
    
    Example:
        @timed("generation_time", tags={"artifact_type": "erd"})
        async def generate_artifact(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            with collector.timer(metric_name, tags):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            with collector.timer(metric_name, tags):
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

