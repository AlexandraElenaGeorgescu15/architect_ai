"""
Monitoring and Metrics System
Tracks performance, usage, and system health
"""

import time
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import defaultdict

@dataclass
class MetricEvent:
    """Single metric event"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """Collect and aggregate metrics"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self.gauges = {}
        self.events = []
        self.start_time = time.time()
    
    def counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        self.events.append(MetricEvent(name, value, labels=labels or {}))
    
    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram value"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        self.events.append(MetricEvent(name, value, labels=labels or {}))
    
    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        self.events.append(MetricEvent(name, value, labels=labels or {}))
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        stats = {
            'uptime_seconds': time.time() - self.start_time,
            'total_events': len(self.events),
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {}
        }
        
        # Aggregate histograms
        for key, values in self.histograms.items():
            if values:
                stats['histograms'][key] = {
                    'count': len(values),
                    'sum': sum(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'p50': self._percentile(values, 50),
                    'p95': self._percentile(values, 95),
                    'p99': self._percentile(values, 99)
                }
        
        return stats
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def export_json(self, filepath: str = None):
        """Export metrics to JSON"""
        stats = self.get_stats()
        stats['exported_at'] = datetime.now().isoformat()
        
        if filepath:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(stats, f, indent=2)
        
        return stats
    
    def reset(self):
        """Reset all metrics"""
        self.counters.clear()
        self.histograms.clear()
        self.gauges.clear()
        self.events.clear()
        self.start_time = time.time()


class Timer:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, labels: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.labels = labels or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.collector.histogram(self.name, duration, self.labels)
        
        # Also count success/failure
        status = 'success' if exc_type is None else 'error'
        labels_with_status = {**self.labels, 'status': status}
        self.collector.counter(f"{self.name}_total", 1, labels_with_status)


# Global metrics collector
_metrics_instance = None

def get_metrics() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


# Convenience functions
def counter(name: str, value: int = 1, **labels):
    """Increment counter"""
    get_metrics().counter(name, value, labels)

def histogram(name: str, value: float, **labels):
    """Record histogram value"""
    get_metrics().histogram(name, value, labels)

def gauge(name: str, value: float, **labels):
    """Set gauge value"""
    get_metrics().gauge(name, value, labels)

def timer(name: str, **labels):
    """Create timer context manager"""
    return Timer(get_metrics(), name, labels)

