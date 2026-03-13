"""
Tests for Data Sources

Unit tests for all data source clients.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_sources.news_api import NewsAPIClient
from data_sources.reddit_client import RedditClient
from data_sources.coingecko import CoinGeckoClient
from data_sources.twitter_client import TwitterClient


class TestNewsAPIClient:
    """Tests for NewsAPI client."""
    
    @pytest.fixture
    def client(self):
        return NewsAPIClient(api_key="test_key")
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.api_key == "test_key"
        assert client.base_url == "https://newsapi.org/v2"
    
    def test_extract_tickers(self, client):
        """Test ticker extraction from text."""
        title = "Apple $AAPL and Tesla $TSLA are rising"
        tickers = client._extract_tickers(title)
        assert "AAPL" in tickers
        assert "TSLA" in tickers
    
    def test_extract_topics(self, client):
        """Test topic extraction."""
        content = "Bitcoin and AI technology are trending"
        topics = client._extract_topics(content, client.TOPIC_KEYWORDS)
        assert "Crypto" in topics
        assert "AI" in topics
    
    def test_process_articles(self, client):
        """Test article processing."""
        articles = [
            {
                "title": "Tesla Stock Rises",
                "description": "EV maker sees gains",
                "source": {"name": "Test Source"},
                "url": "https://test.com",
                "publishedAt": "2026-03-13T00:00:00Z"
            }
        ]
        
        processed = client._process_articles(articles)
        assert len(processed) == 1
        assert processed[0]["related_tickers"] == ["TSLA"]
        assert "Tech" in processed[0]["topics"] or "EV" in processed[0]["topics"]


class TestRedditClient:
    """Tests for Reddit client."""
    
    @pytest.fixture
    def client(self):
        return RedditClient()
    
    def test_init(self, client):
        """Test client initialization."""
        assert "wallstreetbets" in client.subreddits
        assert "investing" in client.subreddits
    
    def test_extract_tickers(self, client):
        """Test ticker extraction."""
        title = "Buying $NVDA calls, what about $AMD?"
        tickers = client._extract_tickers(title)
        assert "NVDA" in tickers
        assert "AMD" in tickers
    
    def test_extract_topics(self, client):
        """Test topic extraction."""
        title = "Fed raises interest rates, inflation concerns"
        topics = client._extract_topics(title, client.TOPIC_KEYWORDS)
        assert "Finance" in topics


class TestCoinGeckoClient:
    """Tests for CoinGecko client."""
    
    @pytest.fixture
    def client(self):
        return CoinGeckoClient()
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.base_url == "https://api.coingecko.com/api/v3"
        assert client._cache_ttl == 60
    
    @pytest.mark.asyncio
    async def test_get_top_cryptos_empty(self, client):
        """Test getting top cryptos with no API key."""
        # Mock the _make_request to return empty data
        client._make_request = AsyncMock(return_value=[])
        
        result = await client.get_top_cryptos(limit=5)
        assert result == []


class TestTwitterClient:
    """Tests for Twitter client."""
    
    @pytest.fixture
    def client(self):
        return TwitterClient(bearer_token="test_token")
    
    def test_init(self, client):
        """Test client initialization."""
        assert client.bearer_token == "test_token"
        assert client._cache_ttl == 120
    
    @pytest.mark.asyncio
    async def test_search_tweets_no_token(self):
        """Test search without token returns empty."""
        client = TwitterClient(bearer_token="")
        result = await client.search_tweets("test", max_results=10)
        assert result == []


class TestValidators:
    """Tests for validation utilities."""
    
    def test_validate_ticker_valid(self):
        """Test valid ticker validation."""
        from utils.validators import validate_ticker
        
        is_valid, error = validate_ticker("AAPL")
        assert is_valid
        assert error is None
    
    def test_validate_ticker_invalid(self):
        """Test invalid ticker validation."""
        from utils.validators import validate_ticker
        
        is_valid, error = validate_ticker("TOOLONGTICKER")
        assert not is_valid
        assert "1-5 characters" in error
    
    def test_validate_limit(self):
        """Test limit validation."""
        from utils.validators import validate_limit
        
        is_valid, error = validate_limit(50, min_val=1, max_val=100)
        assert is_valid
        
        is_valid, error = validate_limit(150, min_val=1, max_val=100)
        assert not is_valid


class TestDecorators:
    """Tests for decorator utilities."""
    
    @pytest.mark.asyncio
    async def test_retry_success(self):
        """Test retry decorator with successful function."""
        from utils.decorators import retry
        
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_failure(self):
        """Test retry decorator with failing function."""
        from utils.decorators import retry
        
        call_count = 0
        
        @retry(max_attempts=3, delay=0.1)
        async def fail_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            await fail_func()
        
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
