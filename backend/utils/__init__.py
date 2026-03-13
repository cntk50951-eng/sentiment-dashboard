"""
Utilities Package

Shared utilities for the sentiment dashboard backend.
"""

from utils.decorators import retry, rate_limit, cache, timing, log_calls
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, circuit_breaker
from utils.connection_pool import ConnectionPool, get_connection_pool
from utils.metrics import MetricsCollector, track_performance, Timer
from utils.validators import (
    validate_ticker,
    validate_date_range,
    sanitize_input,
    validate_category,
    validate_limit
)

__all__ = [
    # Decorators
    "retry",
    "rate_limit",
    "cache",
    "timing",
    "log_calls",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "circuit_breaker",
    # Connection Pool
    "ConnectionPool",
    "get_connection_pool",
    # Metrics
    "MetricsCollector",
    "track_performance",
    "Timer",
    # Validators
    "validate_ticker",
    "validate_date_range",
    "sanitize_input",
    "validate_category",
    "validate_limit",
]
