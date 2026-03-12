"""
Application Configuration

Centralized configuration management using Pydantic Settings.
All environment variables are validated and typed.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = Field(default="Sentiment Dashboard", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="production", description="Environment (dev/staging/prod)")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], description="Allowed CORS origins")
    
    # Security
    SECRET_KEY: str = Field(default="", description="Secret key for JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Token expiration time")
    
    # API Keys - Required
    NEWS_API_KEY: str = Field(..., description="NewsAPI key (required)")
    MINIMAX_API_KEY: str = Field(..., description="Minimax AI API key (required)")
    
    # API Keys - Optional
    REDDIT_CLIENT_ID: Optional[str] = Field(default=None, description="Reddit API client ID")
    REDDIT_CLIENT_SECRET: Optional[str] = Field(default=None, description="Reddit API client secret")
    REDDIT_USERNAME: Optional[str] = Field(default=None, description="Reddit username")
    REDDIT_PASSWORD: Optional[str] = Field(default=None, description="Reddit password")
    
    ALPACA_API_KEY: Optional[str] = Field(default=None, description="Alpaca API key")
    ALPACA_SECRET_KEY: Optional[str] = Field(default=None, description="Alpaca secret key")
    
    TWITTER_BEARER_TOKEN: Optional[str] = Field(default=None, description="Twitter Bearer token")
    
    # Cache
    CACHE_TTL: int = Field(default=300, description="Cache TTL in seconds")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis connection URL")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=60, description="Rate limit requests per minute")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton
    """
    return Settings()


# Global settings instance
settings = get_settings()
