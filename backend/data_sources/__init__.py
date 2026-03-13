"""
Data Sources Package

Provides unified access to multiple financial and social data sources
with built-in caching, retry logic, and circuit breaker protection.
"""

from data_sources.news_api import NewsAPIClient
from data_sources.reddit_client import RedditClient
from data_sources.coingecko import CoinGeckoClient
from data_sources.twitter_client import TwitterClient
from data_sources.base_client import DataSourceClient, DataSourceError

__all__ = [
    "NewsAPIClient",
    "RedditClient",
    "CoinGeckoClient",
    "TwitterClient",
    "DataSourceClient",
    "DataSourceError",
]
