"""
Performance Metrics Collection

Collects and exposes performance metrics for monitoring and optimization.
"""

import time
import asyncio
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
from functools import wraps
import statistics


@dataclass
class MetricSnapshot:
    """Snapshot of metric data."""
    count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    p95_time: float = 0.0
    p99_time: float = 0.0
    errors: int = 0
    success_rate: float = 100.0


class MetricsCollector:
    """
    Collects performance metrics for API calls and operations.
    
    Tracks:
    - Call counts
    - Response times
    - Error rates
    - Percentile latencies
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._metrics: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
    
    async def record(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        error_type: Optional[str] = None
    ):
        """
        Record a metric.
        
        Args:
            operation: Operation name
            duration: Execution time in seconds
            success: Whether operation succeeded
            error_type: Type of error if failed
        """
        async with self._lock:
            if operation not in self._metrics:
                self._metrics[operation] = {
                    "count": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "times": deque(maxlen=self.max_history),
                    "errors": deque(maxlen=100),
                    "last_updated": time.time()
                }
            
            metric = self._metrics[operation]
            metric["count"] += 1
            metric["times"].append(duration)
            metric["last_updated"] = time.time()
            
            if success:
                metric["success_count"] += 1
            else:
                metric["error_count"] += 1
                metric["errors"].append({
                    "type": error_type or "unknown",
                    "timestamp": time.time()
                })
    
    async def get_snapshot(self, operation: str) -> MetricSnapshot:
        """
        Get metric snapshot for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            MetricSnapshot with statistics
        """
        async with self._lock:
            if operation not in self._metrics:
                return MetricSnapshot()
            
            metric = self._metrics[operation]
            times = list(metric["times"])
            
            if not times:
                return MetricSnapshot(count=metric["count"])
            
            total = sum(times)
            count = len(times)
            
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            
            return MetricSnapshot(
                count=metric["count"],
                total_time=total,
                avg_time=total / count,
                min_time=min(times),
                max_time=max(times),
                p95_time=sorted_times[min(p95_idx, len(sorted_times) - 1)],
                p99_time=sorted_times[min(p99_idx, len(sorted_times) - 1)],
                errors=metric["error_count"],
                success_rate=(metric["success_count"] / metric["count"] * 100) 
                    if metric["count"] > 0 else 100.0
            )
    
    async def get_all_snapshots(self) -> Dict[str, MetricSnapshot]:
        """Get snapshots for all operations."""
        async with self._lock:
            result = {}
            for operation in self._metrics:
                result[operation] = await self.get_snapshot(operation)
            return result
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        async with self._lock:
            total_calls = sum(m["count"] for m in self._metrics.values())
            total_errors = sum(m["error_count"] for m in self._metrics.values())
            
            return {
                "total_operations": len(self._metrics),
                "total_calls": total_calls,
                "total_errors": total_errors,
                "overall_success_rate": (
                    (total_calls - total_errors) / total_calls * 100
                ) if total_calls > 0 else 100.0,
                "operations": list(self._metrics.keys())
            }
    
    async def reset(self, operation: Optional[str] = None):
        """Reset metrics for an operation or all operations."""
        async with self._lock:
            if operation:
                if operation in self._metrics:
                    del self._metrics[operation]
            else:
                self._metrics.clear()


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def track_performance(operation_name: Optional[str] = None):
    """
    Decorator to track function performance.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        
    Example:
        @track_performance("fetch_news")
        async def get_news():
            return await api.fetch()
    """
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__
        collector = get_metrics_collector()
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                await collector.record(name, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start
                await collector.record(name, duration, success=False, error_type=type(e).__name__)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                asyncio.create_task(collector.record(name, duration, success=True))
                return result
            except Exception as e:
                duration = time.time() - start
                asyncio.create_task(collector.record(name, duration, success=False, error_type=type(e).__name__))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class Timer:
    """Context manager for timing code blocks."""
    
    def __init__(self, operation: str, collector: Optional[MetricsCollector] = None):
        self.operation = operation
        self.collector = collector or get_metrics_collector()
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        success = exc_type is None
        await self.collector.record(
            self.operation,
            self.duration,
            success=success,
            error_type=exc_type.__name__ if exc_type else None
        )
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        success = exc_type is None
        asyncio.create_task(self.collector.record(
            self.operation,
            self.duration,
            success=success,
            error_type=exc_type.__name__ if exc_type else None
        ))
