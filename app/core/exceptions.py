"""
Custom Exceptions

Application-specific exceptions with proper error codes and messages.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFoundError(AppException):
    """Resource not found exception."""
    
    def __init__(self, message: str, resource_type: str = "Resource"):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details={"resource_type": resource_type}
        )


class ExternalAPIError(AppException):
    """External API call error."""
    
    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: int = 502
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="EXTERNAL_API_ERROR",
            details={"api_name": api_name}
        )


class RateLimitError(AppException):
    """Rate limit exceeded exception."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )


class AuthenticationError(AppException):
    """Authentication failed exception."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(AppException):
    """Authorization failed exception."""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )
