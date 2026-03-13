"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily disabling calls to failing services.
"""

import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Any
from functools import wraps


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Prevents cascading failures by:
    - Tracking failure counts
    - Opening circuit after threshold
    - Periodically testing recovery (half-open)
    - Closing when service recovers
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self._last_failure_time and \
               time.time() - self._last_failure_time >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            current_state = self.state
            
            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpen(f"Circuit '{self.name}' is OPEN")
            
            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen(
                        f"Circuit '{self.name}' is HALF_OPEN (max calls reached)"
                    )
                self._half_open_calls += 1
        
        # Execute the call
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    # Service recovered, close circuit
                    self._reset()
            else:
                self._failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failed during recovery test, reopen circuit
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._success_count = 0
            elif self._failure_count >= self.failure_threshold:
                # Threshold reached, open circuit
                self._state = CircuitState.OPEN
    
    def _reset(self):
        """Reset circuit to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time
        }


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global circuit breakers registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """
    Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        **kwargs: Configuration options
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
    return _circuit_breakers[name]


def circuit_breaker(name: str, **kwargs):
    """
    Decorator to apply circuit breaker to a function.
    
    Args:
        name: Circuit breaker name
        **kwargs: Circuit breaker configuration
        
    Example:
        @circuit_breaker("news_api", failure_threshold=3)
        async def fetch_news():
            return await api.get_news()
    """
    def decorator(func):
        breaker = get_circuit_breaker(name, **kwargs)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator
