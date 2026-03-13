"""
Decorators

Utility decorators for retry logic, rate limiting, and caching.
"""

import asyncio
import functools
import time
from typing import Callable, Any, Optional
from functools import wraps


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @retry(max_attempts=3, delay=1.0)
        async def fetch_data():
            return await api.get_data()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            return None  # Should not reach here
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None  # Should not reach here
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def rate_limit(calls: int, period: float):
    """
    Rate limit decorator.
    
    Args:
        calls: Maximum number of calls allowed in the period
        period: Time period in seconds
        
    Example:
        @rate_limit(calls=10, period=60.0)
        async def api_call():
            return await fetch_data()
    """
    def decorator(func: Callable) -> Callable:
        # Store state on the function
        if not hasattr(func, '_rate_limit_state'):
            func._rate_limit_state = {
                'calls': [],
                'lock': asyncio.Lock() if asyncio.iscoroutinefunction(func) else None
            }
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            state = func._rate_limit_state
            
            async with state['lock']:
                now = time.time()
                # Remove old calls outside the period
                state['calls'] = [c for c in state['calls'] if now - c < period]
                
                # Check if we've exceeded the rate limit
                if len(state['calls']) >= calls:
                    sleep_time = state['calls'][0] + period - now
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                    state['calls'] = state['calls'][1:]
                
                state['calls'].append(now)
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            state = func._rate_limit_state
            
            now = time.time()
            # Remove old calls outside the period
            state['calls'] = [c for c in state['calls'] if now - c < period]
            
            # Check if we've exceeded the rate limit
            if len(state['calls']) >= calls:
                sleep_time = state['calls'][0] + period - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                state['calls'] = state['calls'][1:]
            
            state['calls'].append(now)
            
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def cache(ttl: float = 300.0, key_func: Optional[Callable] = None):
    """
    Simple in-memory cache decorator.
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from arguments
        
    Example:
        @cache(ttl=60.0)
        async def get_data(user_id: int):
            return await fetch_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        cache_store = {}
        
        def make_key(*args, **kwargs):
            if key_func:
                return key_func(*args, **kwargs)
            return str(args) + str(sorted(kwargs.items()))
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            key = make_key(*args, **kwargs)
            
            if key in cache_store:
                result, timestamp = cache_store[key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = await func(*args, **kwargs)
            cache_store[key] = (result, time.time())
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            key = make_key(*args, **kwargs)
            
            if key in cache_store:
                result, timestamp = cache_store[key]
                if time.time() - timestamp < ttl:
                    return result
            
            result = func(*args, **kwargs)
            cache_store[key] = (result, time.time())
            return result
        
        # Add cache management methods
        def clear_cache():
            cache_store.clear()
        
        def get_cache_info():
            return {
                'size': len(cache_store),
                'ttl': ttl
            }
        
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.clear_cache = clear_cache
        wrapper.get_cache_info = get_cache_info
        
        return wrapper
    
    return decorator


def timing(func: Callable) -> Callable:
    """
    Timing decorator to measure function execution time.
    
    Example:
        @timing
        async def slow_function():
            await asyncio.sleep(1)
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def log_calls(logger=None):
    """
    Log function calls with arguments.
    
    Args:
        logger: Optional logger instance. If None, uses print.
        
    Example:
        @log_calls()
        def process_data(data):
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            log_msg = f"Calling {func.__name__} with args={args}, kwargs={kwargs}"
            if logger:
                logger.info(log_msg)
            else:
                print(log_msg)
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                if logger:
                    logger.error(f"{func.__name__} failed: {e}")
                else:
                    print(f"{func.__name__} failed: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            log_msg = f"Calling {func.__name__} with args={args}, kwargs={kwargs}"
            if logger:
                logger.info(log_msg)
            else:
                print(log_msg)
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if logger:
                    logger.error(f"{func.__name__} failed: {e}")
                else:
                    print(f"{func.__name__} failed: {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
