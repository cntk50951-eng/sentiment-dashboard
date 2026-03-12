"""
Logging Configuration

Structured logging with JSON output for production environments.
"""

import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    Uses structlog for structured JSON logging in production,
    and colored console output in development.
    """
    
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    if settings.LOG_FORMAT == "json":
        # Production: JSON format
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Colored console output
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, settings.LOG_LEVEL.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.stdlib.BoundLogger: Structured logger
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logger to classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger instance."""
        return get_logger(self.__class__.__name__)
