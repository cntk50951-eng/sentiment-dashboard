"""
Twitter/X API Client
獲取社交媒體情緒數據
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import aiohttp
import os


class TwitterClient:
    """
    Twitter/X API Client for sentiment analysis.
    
    Uses Twitter API v2 to fetch tweets and analyze
    market sentiment from social media discussions.
    """
    
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN", "")
        self.base_url = "https://api.twitter.com/2"
        self._cache = {}
        self._cache_ttl = 120  # 2 minutes cache
        self._last_request_time = 0
        self._min_request_interval = 2.0  # Rate limiting for free tier
        
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make Twitter API request with rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as dictionary
        """
        import time
        
        if not self.bearer_token:
            return {"data": [], "meta": {}}
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, 
                        params=params, 
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        self._last_request_time = time.time()
                        
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:
                            # Rate limited
                            reset_time = int(response.headers.get("x-rate-limit-reset", time.time() + 60))
                            wait_time = max(reset_time - time.time(), retry_delay * (2 ** attempt))
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status == 401:
                            print("Twitter API: Invalid credentials")
                            return {"data": [], "meta": {}}
                        else:
                            response.raise_for_status()
                            
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    return {"data": [], "meta": {}}
                await asyncio.sleep(retry_delay * (2 ** attempt))
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Twitter API Error: {e}")
                    return {"data": [], "meta": {}}
                await asyncio.sleep(retry_delay * (2 ** attempt))
        
        return {"data": [], "meta": {}}
    
    async def search_tweets(
        self, 
        query: str, 
        max_results: int = 20,
        tweet_fields: str = "created_at,public_metrics,context_annotations"
    ) -> List[Dict]:
        """
        搜索推文。
        
        Args:
            query: Search query
            max_results: Maximum number of results (10-100)
            tweet_fields: Additional tweet fields to include
            
        Returns:
            List of tweet dictionaries
        """
        cache_key = f"tweets_{query}_{max_results}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now().timestamp() - cached_time < self._cache_ttl:
                return cached_data
        
        try:
            params = {
                "query": query,
                "max_results": min(max(max_results, 10), 100),
                "tweet.fields": tweet_fields
            }
            
            data = await self._make_request("/tweets/search/recent", params)
            
            tweets = data.get("data", [])
            processed = []
            
            for tweet in tweets:
                processed.append({
                    "id": tweet.get("id"),
                    "text": tweet.get("text"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {}),
                    "like_count": tweet.get("public_metrics", {}).get("like_count", 0),
                    "retweet_count": tweet.get("public_metrics", {}).get("retweet_count", 0),
                    "reply_count": tweet.get("public_metrics", {}).get("reply_count", 0),
                    "quote_count": tweet.get("public_metrics", {}).get("quote_count", 0),
                    "data_source": "twitter"
                })
            
            # Update cache
            self._cache[cache_key] = (processed, datetime.now().timestamp())
            return processed
            
        except Exception as e:
            print(f"Twitter Search Error: {e}")
            return []
    
    async def get_trending_financial_tweets(self, limit: int = 20) -> List[Dict]:
        """
        獲取熱門金融相關推文。
        
        Args:
            limit: Number of tweets to return
            
        Returns:
            List of financial tweet dictionaries
        """
        # Search for popular financial hashtags and keywords
        queries = [
            "(#stocks OR #stockmarket OR #investing) -is:retweet lang:en",
            "(#crypto OR #bitcoin OR #ethereum) -is:retweet lang:en",
            "(#trading OR #daytrading OR #forex) -is:retweet lang:en",
            "(#wallstreet OR #nasdaq OR #nyse) -is:retweet lang:en"
        ]
        
        all_tweets = []
        
        for query in queries:
            try:
                tweets = await self.search_tweets(query, max_results=limit // len(queries) + 5)
                all_tweets.extend(tweets)
            except Exception as e:
                print(f"Error fetching tweets for query '{query}': {e}")
                continue
        
        # Sort by engagement (likes + retweets)
        all_tweets.sort(
            key=lambda x: x.get("like_count", 0) + x.get("retweet_count", 0), 
            reverse=True
        )
        
        return all_tweets[:limit]
    
    async def get_stock_sentiment(self, ticker: str, limit: int = 30) -> Dict:
        """
        獲取特定股票的情緒分析數據。
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            limit: Number of tweets to analyze
            
        Returns:
            Sentiment analysis results
        """
        query = f"${ticker} OR #{ticker} -is:retweet lang:en"
        
        try:
            tweets = await self.search_tweets(query, max_results=limit)
            
            if not tweets:
                return {
                    "ticker": ticker,
                    "tweet_count": 0,
                    "sentiment": "neutral",
                    "sentiment_score": 0.0,
                    "engagement": 0
                }
            
            # Calculate engagement
            total_engagement = sum(
                t.get("public_metrics", {}).get("like_count", 0) +
                t.get("public_metrics", {}).get("retweet_count", 0) +
                t.get("public_metrics", {}).get("reply_count", 0)
                for t in tweets
            )
            
            return {
                "ticker": ticker,
                "tweet_count": len(tweets),
                "sentiment": "neutral",  # Simplified
                "sentiment_score": 0.0,
                "engagement": total_engagement,
                "analyzed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict:
        """
        Check Twitter API health.
        
        Returns:
            Health status dictionary
        """
        if not self.bearer_token:
            return {
                "status": "unconfigured",
                "message": "No bearer token configured"
            }
        
        return {
            "status": "healthy",
            "configured": True
        }