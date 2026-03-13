"""
Data Aggregator Service

Aggregates data from multiple sources with caching, retry logic,
and error handling for reliable data fetching.
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json
import logging

from data_sources.news_api import NewsAPIClient
from data_sources.reddit_client import RedditClient
from data_sources.coingecko import CoinGeckoClient
from data_sources.twitter_client import TwitterClient
from data_sources.fallback_client import FallbackDataClient
from core.exceptions import DataSourceError

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    data: any
    timestamp: datetime
    ttl_seconds: int = 300  # Default 5 minutes
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now() - self.timestamp > timedelta(seconds=self.ttl_seconds)


@dataclass
class DataSourceStatus:
    """Track data source health status."""
    name: str
    is_healthy: bool = True
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0


class DataAggregator:
    """
    Aggregates data from multiple financial and social data sources.
    
    Features:
    - Intelligent caching with TTL
    - Parallel data fetching
    - Fallback mechanisms
    - Error resilience
    - Rate limiting coordination
    - Health monitoring
    """
    
    def __init__(self):
        self.news_client = NewsAPIClient()
        self.reddit_client = RedditClient()
        self.crypto_client = CoinGeckoClient()
        self.twitter_client = TwitterClient()
        self.fallback_client = FallbackDataClient()
        
        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        
        # Cache TTL configuration (in seconds)
        self._cache_config = {
            "hot_topics": 180,        # 3 minutes
            "crypto_prices": 60,      # 1 minute
            "sentiment": 300,         # 5 minutes
            "trending": 120,          # 2 minutes
            "search": 60,             # 1 minute
        }
        
        # Data source health tracking
        self._source_status: Dict[str, DataSourceStatus] = {
            "newsapi": DataSourceStatus("newsapi"),
            "reddit": DataSourceStatus("reddit"),
            "coingecko": DataSourceStatus("coingecko"),
            "twitter": DataSourceStatus("twitter"),
            "fallback": DataSourceStatus("fallback")
        }
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key from method and parameters."""
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        return f"{method}:{hashlib.md5(params_str.encode()).hexdigest()}"
    
    def _get_from_cache(self, key: str) -> Optional[any]:
        """Get data from cache if available and not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                logger.debug(f"Cache hit for key: {key[:16]}...")
                return entry.data
            else:
                logger.debug(f"Cache expired for key: {key[:16]}...")
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: any, ttl: int = 300):
        """Store data in cache with TTL."""
        self._cache[key] = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            ttl_seconds=ttl
        )
        logger.debug(f"Cached data with key: {key[:16]}...")
    
    def _update_source_status(self, source: str, success: bool, error: Optional[str] = None):
        """Update data source health status."""
        status = self._source_status[source]
        if success:
            status.is_healthy = True
            status.last_success = datetime.now()
            status.success_count += 1
            status.failure_count = max(0, status.failure_count - 1)
        else:
            status.failure_count += 1
            status.last_error = error
            if status.failure_count >= 3:  # Mark unhealthy after 3 consecutive failures
                status.is_healthy = False
                logger.warning(f"Data source {source} marked as unhealthy")
    
    def get_source_health(self) -> Dict[str, Dict]:
        """Get health status of all data sources."""
        return {
            name: {
                "is_healthy": status.is_healthy,
                "last_error": status.last_error,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "failure_count": status.failure_count,
                "success_count": status.success_count
            }
            for name, status in self._source_status.items()
        }
    
    async def get_hot_topics(
        self, 
        category: Optional[str] = None, 
        limit: int = 20,
        use_fallback: bool = True
    ) -> Dict[str, any]:
        """
        獲取熱點話題，聚合多個數據源。
        
        Args:
            category: Optional category filter
            limit: Maximum number of topics to return
            use_fallback: Whether to use fallback data if all sources fail
            
        Returns:
            Dictionary with topics and metadata
        """
        cache_key = self._get_cache_key("hot_topics", category=category, limit=limit)
        cached = self._get_from_cache(cache_key)
        if cached:
            return {**cached, "from_cache": True}
        
        all_topics = []
        errors = []
        sources_used = []
        
        # Try NewsAPI
        try:
            news_topics = await self._fetch_news_topics(category, limit // 2 + 5)
            all_topics.extend(news_topics)
            self._update_source_status("newsapi", True)
            sources_used.append("newsapi")
            logger.info(f"Fetched {len(news_topics)} topics from NewsAPI")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"NewsAPI fetch error: {error_msg}")
            errors.append(f"NewsAPI: {error_msg}")
            self._update_source_status("newsapi", False, error_msg)
        
        # Try Reddit
        try:
            reddit_topics = await self._fetch_reddit_topics(limit // 2 + 5)
            all_topics.extend(reddit_topics)
            self._update_source_status("reddit", True)
            sources_used.append("reddit")
            logger.info(f"Fetched {len(reddit_topics)} topics from Reddit")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reddit fetch error: {error_msg}")
            errors.append(f"Reddit: {error_msg}")
            self._update_source_status("reddit", False, error_msg)
        
        # Use fallback if no data and fallback enabled
        if not all_topics and use_fallback:
            logger.warning("All primary sources failed, using fallback data")
            try:
                fallback_topics = await self.fallback_client.get_hot_topics(limit)
                all_topics.extend(fallback_topics)
                self._update_source_status("fallback", True)
                sources_used.append("fallback")
                logger.info(f"Generated {len(fallback_topics)} fallback topics")
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
                errors.append(f"Fallback: {str(e)}")
        
        # Sort by engagement/mentions
        all_topics.sort(key=lambda x: x.get("mentions