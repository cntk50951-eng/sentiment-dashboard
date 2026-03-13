"""
Custom Exceptions for Sentiment Dashboard

Provides standardized error handling across the application.
"""

from typing import Optional, Any


class SentimentDashboardError(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# ============== Data Source Errors ==============

class DataSourceError(SentimentDashboardError):
    """Exception raised for data source failures."""
    
    def __init__(
        self,
        message: str,
        source: str,
        status_code: Optional[int] = None,
        details: Optional[Any] = None
    ):
        self.source = source
        self.status_code = status_code
        super().__init__(message, details)


class RateLimitError(DataSourceError):
    """Exception raised when API rate limit is exceeded."""
    
    def __init__(self, message: str, source: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message, source, status_code=429)


class AuthenticationError(DataSourceError):
    """Exception raised for authentication failures."""
    
    def __init__(self, message: str, source: str):
        super().__init__(message, source, status_code=401)


class CircuitBreakerError(DataSourceError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, source: str):
        super().__init__(message, source, status_code=503)


# ============== AI Agent Errors ==============

class AIAnalysisError(SentimentDashboardError):
    """Exception raised for AI analysis failures."""
    
    def __init__(self, message: str, model: Optional[str] = None, details: Optional[Any] = None):
        self.model = model
        super().__init__(message, details)


# ============== Validation Errors ==============

class ValidationError(SentimentDashboardError):
    """Exception raised for validation failures."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Any] = None):
        self.field = field
        super().__init__(message, details)


class CacheError(SentimentDashboardError):
    """Exception raised for cache-related errors."""
    
    def __init__(self, message: str, key: Optional[str] = None):
        self.key = key
        super().__init__(message)


class CircuitBreakerOpenError(SentimentDashboardError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, retry_after: Optional[float] = None):
        self.service_name = service_name
        self.retry_after = retry_after
        msg = f"Circuit breaker is open for {service_name}"
        if retry_after:
            msg += f". Retry after {retry_after:.1f} seconds"
        super().__init__(msg)


# ============== Error Handlers ==============

def format_error_response(error: Exception) -> dict:
    """
    Format exception into API error response.
    
    Args:
        error: Exception to format
        
    Returns:
        Error response dictionary
    """
    if isinstance(error, DataSourceError):
        return {
            "error": error.__class__.__name__,
            "message": error.message,
            "source": error.source,
            "status_code": error.status_code,
            "details": error.details
        }
    elif isinstance(error, AIAnalysisError):
        return {
            "error": error.__class__.__name__,
            "message": error.message,
            "model": error.model,
            "details": error.details
        }
    elif isinstance(error, ValidationError):
        return {
            "error": error.__class__.__name__,
            "message": error.message,
            "field": error.field,
            "details": error.details
        }
    else:
        return {
            "error": error.__class__.__name__,
            "message": str(error),
            "details": None
        }
