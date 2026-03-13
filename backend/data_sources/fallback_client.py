"""
Fallback Data Client

Provides fallback data when primary sources fail.
Used for resilience and graceful degradation.
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import random


class FallbackClient:
    """
    Fallback client for providing default data when APIs fail.
    
    Features:
    - Cached data from previous successful calls
    - Default/placeholder data
    - Graceful degradation
    """
    
    # Default crypto data (fallback)
    DEFAULT_CRYPTO_DATA = [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "current_price": 67000, "market_cap": 1300000000000, "price_change_percentage_24h": 2.5},
        {"id": "ethereum", "symbol": "ETH", "name": "Ethereum", "current_price": 3500, "market_cap": 420000000000, "price_change_percentage_24h": 3.2},
        {"id": "solana", "symbol": "SOL", "name": "Solana", "current_price": 145, "market_cap": 65000000000, "price_change_percentage_24h": 5.1},
        {"id": "binancecoin", "symbol": "BNB", "name": "BNB", "current_price": 580, "market_cap": 87000000000, "price_change_percentage_24h": 1.8},
        {"id": "ripple", "symbol": "XRP", "name": "XRP", "current_price": 0.52, "market_cap": 28000000000, "price_change_percentage_24h": -1.2}
    ]
    
    # Default news topics (fallback)
    DEFAULT_NEWS = [
        {
            "id": "fallback_1",
            "title": "Market Sentiment Remains Cautiously Optimistic",
            "description": "Investors weigh economic indicators",
            "source": "Market Watch",
            "topics": ["Finance"],
            "related_tickers": [],
            "relevance_score": 0.5,
            "data_source": "fallback"
        },
        {
            "id": "fallback_2",
            "title": "Tech Sector Shows Resilience Amid Volatility",
            "description": "Technology stocks continue to attract interest",
            "source": "Reuters",
            "topics": ["Tech", "AI"],
            "related_tickers": ["NVDA", "MSFT", "GOOGL"],
            "relevance_score": 0.6,
            "data_source": "fallback"
        },
        {
            "id": "fallback_3",
            "title": "Cryptocurrency Market Observations",
            "description": "Digital assets see varied movement",
            "source": "CoinDesk",
            "topics": ["Crypto"],
            "related_tickers": ["BTC", "ETH"],
            "relevance_score": 0.5,
            "data_source": "fallback"
        }
    ]
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600  # 1 hour for fallback cache
        self._request_count = 0
        self._fallback_count = 0
    
    async def get_crypto_data(
        self,
        limit: int = 10,
        cached_data: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Get crypto data with fallback.
        
        Args:
            limit: Number of results
            cached_data: Previously cached data from primary source
            
        Returns:
            List of crypto data
        """
        self._request_count += 1
        
        # Use cached data if available and fresh
        if cached_data:
            self._cache["crypto"] = (cached_data, datetime.now())
            return cached_data[:limit]
        
        # Check fallback cache
        if "crypto" in self._cache:
            data, timestamp = self._cache["crypto"]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                self._fallback_count += 1
                return data[:limit]
        
        # Return default data with slight variation
        self._fallback_count += 1
        return self._add_variation(self.DEFAULT_CRYPTO_DATA[:limit])
    
    async def get_news(
        self,
        limit: int = 10,
        cached_data: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Get news data with fallback.
        
        Args:
            limit: Number of results
            cached_data: Previously cached data
            
        Returns:
            List of news articles
        """
        self._request_count += 1
        
        if cached_data:
            self._cache["news"] = (cached_data, datetime.now())
            return cached_data[:limit]
        
        if "news" in self._cache:
            data, timestamp = self._cache["news"]
            if datetime.now().timestamp() - timestamp < self._cache_ttl:
                self._fallback_count += 1
                return data[:limit]
        
        self._fallback_count += 1
        return self._add_variation(self.DEFAULT_NEWS[:limit])
    
    def _add_variation(self, data: List[Dict]) -> List[Dict]:
        """Add slight variation to fallback data."""
        import time
        random.seed(int(time.time() / 300))  # Change every 5 minutes
        
        varied = []
        for item in data:
            varied_item = item.copy()
            varied_item["timestamp"] = datetime.now().isoformat()
            varied_item["is_fallback"] = True
            varied.append(varied_item)
        
        random.seed()
        return varied
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fallback client statistics."""
        return {
            "total_requests": self._request_count,
            "fallback_uses": self._fallback_count,
            "fallback_rate": self._fallback_count / max(self._request_count, 1),
            "cached_endpoints": list(self._cache.keys())
        }


class DataAggregator:
    """
    Aggregates data from multiple sources with fallback support.
    
    Features:
    - Parallel fetching from multiple sources
    - Fallback to secondary sources on failure
    - Data deduplication
    - Priority-based selection
    """
    
    def __init__(self):
        self.fallback = FallbackClient()
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 60  # 1 minute
    
    async def get_all_sentiment_data(
        self,
        news_client,
        reddit_client,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get sentiment data from all sources.
        
        Args:
            news_client: NewsAPI client
            reddit_client: Reddit client
            limit: Number of results per source
            
        Returns:
            Aggregated data with metadata
        """
        results = {
            "news": {"data": [], "status": "pending", "error": None},
            "reddit": {"data": [], "status": "pending", "error": None},
            "aggregated": {"topics": [], "status": "pending"}
        }
        
        # Fetch from news
        try:
            news_data = await news_client.get_hot_topics(limit=limit)
            results["news"]["data"] = news_data
            results["news"]["status"] = "success"
        except Exception as e:
            results["news"]["error"] = str(e)
            results["news"]["status"] = "failed"
        
        # Fetch from reddit
        try:
            reddit_data = await reddit_client.get_hot_posts(limit=limit)
            results["reddit"]["data"] = reddit_data
            results["reddit"]["status"] = "success"
        except Exception as e:
            results["reddit"]["error"] = str(e)
            results["reddit"]["status"] = "failed"
        
        # Aggregate
        all_topics = []
        
        if results["news"]["status"] == "success":
            all_topics.extend(results["news"]["data"])
        
        if results["reddit"]["status"] == "success":
            all_topics.extend(results["reddit"]["data"])
        
        # If both failed, use fallback
        if not all_topics:
            all_topics = await self.fallback.get_news(limit=limit)
            results["aggregated"]["status"] = "fallback"
        else:
            results["aggregated"]["status"] = "success"
        
        # Deduplicate
        seen_ids = set()
        unique_topics = []
        for topic in all_topics:
            topic_id = topic.get("id", "")
            if topic_id and topic_id not in seen_ids:
                seen_ids.add(topic_id)
                unique_topics.append(topic)
        
        results["aggregated"]["topics"] = unique_topics[:limit]
        results["aggregated"]["total_sources"] = sum(
            1 for s in [results["news"]["status"], results["reddit"]["status"]]
            if s == "success"
        )
        
        return results
    
    async def get_crypto_with_fallback(
        self,
        primary_client,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get crypto data with fallback support.
        
        Args:
            primary_client: Primary CoinGecko client
            limit: Number of results
            
        Returns:
            Crypto data with metadata
        """
        result = {
            "data": [],
            "status": "pending",
            "source": "primary",
            "error": None
        }
        
        try:
            data = await primary_client.get_top_cryptos(limit=limit)
            result["data"] = data
            result["status"] = "success"
            result["source"] = "primary"
        except Exception as e:
            result["error"] = str(e)
            result["status"] = "failed"
            
            # Use fallback
            fallback_data = await self.fallback.get_crypto_data(limit=limit)
            result["data"] = fallback_data
            result["status"] = "fallback"
            result["source"] = "fallback"
        
        return result
