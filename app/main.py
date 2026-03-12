"""
FastAPI Application Entry Point

Production-grade FastAPI application with proper error handling,
logging, and middleware configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import hot_topics, sentiment, opportunities, agent
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger

# Configure logging on module load
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Investment Intelligence Platform",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    _add_middleware(app)
    
    # Add exception handlers
    _add_exception_handlers(app)
    
    # Include routers
    _include_routers(app)
    
    return app


def _add_middleware(app: FastAPI) -> None:
    """Configure middleware stack."""
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)


def _add_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers."""
    
    @app.exception_handler(AppException)
    async def handle_app_exception(
        request: Request,
        exc: AppException
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        logger.error(
            "application_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )
    
    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions."""
        logger.exception(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )


def _include_routers(app: FastAPI) -> None:
    """Include API routers."""
    
    # API version prefix
    api_prefix = "/api/v1"
    
    app.include_router(hot_topics.router, prefix=api_prefix, tags=["Hot Topics"])
    app.include_router(sentiment.router, prefix=api_prefix, tags=["Sentiment Analysis"])
    app.include_router(opportunities.router, prefix=api_prefix, tags=["Opportunities"])
    app.include_router(agent.router, prefix=api_prefix, tags=["AI Agent"])
    
    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """Root endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else None,
        }


# Create application instance
app = create_application()
