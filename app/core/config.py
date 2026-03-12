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
    app_name: str = "Sentiment Dashboard"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Security
    secret_key: str = ""
    access_token_expire_minutes: int = 30
    
    # API Keys - Required
    news_api_key: str = ""
    minimax_api_key: str = ""
    
    # API Keys - Optional
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_username: Optional[str] = None
    reddit_password: Optional[str] = None
    
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    
    twitter_bearer_token: Optional[str] = None
    
    # Cache
    cache_ttl: int = 300
    redis_url: Optional[str] = None
    
    # Rate Limiting
    rate_limit_requests: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


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
