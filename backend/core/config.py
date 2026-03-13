"""
Application Configuration

Centralized configuration management with environment variable support.
"""

import os
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class APIConfig:
    """API configuration settings."""
    
    # NewsAPI
    news_api_key: str = field(default_factory=lambda: os.getenv("NEWS_API_KEY", ""))
    
    # Minimax AI
    minimax_api_key: str = field(default_factory=lambda: os.getenv("MINIMAX_API_KEY", ""))
    
    # Twitter/X
    twitter_bearer_token: str = field(default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""))
    
    # Reddit (optional)
    reddit_client_id: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", ""))
    reddit_username: str = field(default_factory=lambda: os.getenv("REDDIT_USERNAME", ""))
    reddit_password: str = field(default_factory=lambda: os.getenv("REDDIT_PASSWORD", ""))
    
    # CoinGecko (optional - can use free tier)
    coingecko_api_key: str = field(default_factory=lambda: os.getenv("COINGECKO_API_KEY", ""))


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    
    hot_topics_ttl: int = 180  # 3 minutes
    crypto_prices_ttl: int = 60  # 1 minute
    sentiment_ttl: int = 300  # 5 minutes
    trending_ttl: int = 120  # 2 minutes
    search_ttl: int = 60  # 1 minute
    news_ttl: int = 180  # 3 minutes
    reddit_ttl: int = 120  # 2 minutes
    max_cache_size: int = 1000  # Maximum cached items


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration settings."""
    
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration settings."""
    
    pool_size: int = 100
    keepalive_timeout: float = 30.0
    ttl_dns_cache: int = 300
    limit_per_host: int = 20
    request_timeout: float = 30.0
    connect_timeout: float = 10.0


@dataclass
class RateLimitConfig:
    """Rate limiting configuration settings."""
    
    # NewsAPI: 100 requests/day on free tier
    newsapi_calls: int = 100
    newsapi_period: float = 86400.0  # 24 hours
    
    # Reddit: Be nice to their servers
    reddit_calls: int = 30
    reddit_period: float = 60.0  # 1 minute
    
    # CoinGecko: 50 calls/min on free tier
    coingecko_calls: int = 50
    coingecko_period: float = 60.0  # 1 minute
    
    # Twitter: 500 requests/month on free tier
    twitter_calls: int = 500
    twitter_period: float = 2592000.0  # 30 days


@dataclass
class AppConfig:
    """Application configuration."""
    
    # Server settings
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000"
    ).split(","))
    
    # API configurations
    api: APIConfig = field(default_factory=APIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or os.getenv("ENVIRONMENT", "production").lower() == "development"


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """Reload configuration from environment variables."""
    global _config
    _config = AppConfig()
    return _config
