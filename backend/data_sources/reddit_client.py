"""
Reddit JSON API Client
無需認證，公開訪問，增強版
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

import aiohttp

from data_sources.base_client import DataSourceClient, DataSourceError
from utils.decorators import cache, timing
from utils.metrics import track_performance


class RedditClient(DataSourceClient):
    """
    Enhanced Reddit client with circuit breaker and caching.
    
    Features:
    - Circuit breaker protection
    - Connection pooling
    - Intelligent caching
    - Rate limiting
    - Subreddit rotation
    """
    
    # Topic keywords for classification
    TOPIC_KEYWORDS = {
        "AI": ["ai", "artificial intelligence", "chatgpt", "machine learning", "llm", "openai"],
        "Crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain", "defi", "nft", "web3", "altcoin"],
        "Energy": ["oil", "energy", "gas", "petroleum", "renewable", "solar", "wind", "opec", "crude"],
        "Tech": ["tech", "technology", "software", "cloud", "saas", "semiconductor", "chip", "ai"],
        "Finance": ["fed", "interest rate", "inflation", "economy", "recession", "gdp", "fomc", "cpi", "ppi"],
        "Meme": ["meme", "yolo", "moon", "rocket", "tendies", "diamond hands", "paper hands"],
        "Earnings": ["earnings", "revenue", "profit", "quarterly", "guidance", "beat", "miss"],
        "EV": ["tesla", "ev", "electric vehicle", "battery", "rivian", "lucid", "nio"],
        "Semiconductor": ["chip", "semiconductor", "nvidia", "intel", "amd", "tsmc"]
    }
    
    # Default subreddits to monitor
    DEFAULT_SUBREDDITS = [
        "wallstreetbets",
        "investing",
        "stocks",
        "StockMarket",
        "CryptoCurrency",
        "Bitcoin",
        "ethereum",
        "wallstreetbetsOGs",
        "SecurityAnalysis"
    ]
    
    def __init__(self, subreddits: Optional[List[str]] = None):
        super().__init__(
            name="reddit",
            base_url="https://www.reddit.com",
            api_key=None,  # Reddit JSON API doesn't require auth
            circuit_breaker_config={
                "failure_threshold": 5,
                "recovery_timeout": 60.0
            }
        )
        
        self.subreddits = subreddits or self.DEFAULT_SUBREDDITS
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        self._rate_limit_delay = 1.0  # Seconds between requests
        self._last_request_time = 0
    
    @track_performance("reddit_hot_posts")
    @cache(ttl=120.0)  # 2 minutes cache
    async def get_hot_posts(
        self,
        limit: int = 10,
        subreddits: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取多個 subreddit 的熱門帖子。
        
        Args:
            limit: Total posts to return
            subreddits: Specific subreddits to query (uses default if None)
            
        Returns:
            List of hot posts sorted by engagement
        """
        target_subreddits = subreddits or self.subreddits
        all_posts = []
        errors = []
        
        # Calculate limit per subreddit
        per_subreddit = max(limit // len(target_subreddits), 5)
        
        for subreddit in target_subreddits:
            try:
                posts = await self._fetch_subreddit_posts(subreddit, per_subreddit)
                all_posts.extend(posts)
                
                # Rate limiting between requests
                await asyncio.sleep(self._rate_limit_delay)
                
            except Exception as e:
                errors.append(f"r/{subreddit}: {str(e)}")
                continue
        
        if not all_posts and errors:
            raise DataSourceError(
                f"Failed to fetch from all subreddits: {'; '.join(errors[:3])}",
                "reddit"
            )
        
        # Sort by engagement (score + comments)
        all_posts.sort(
            key=lambda x: x.get("engagement_score", 0),
            reverse=True
        )
        
        return all_posts[:limit]
    
    async def _fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from a specific subreddit.
        
        Args:
            subreddit: Subreddit name
            limit: Number of posts to fetch
            
        Returns:
            List of processed posts
        """
        url = f"{self.base_url}/r/{subreddit}/hot.json"
        params = {"limit": min(limit, 100)}
        
        try:
            async with self._pool.request(
                "GET",
                url,
                params=params,
                headers=self.headers
            ) as response:
                
                if response.status == 429:
                    raise DataSourceError(
                        "Rate limited by Reddit",
                        "reddit",
                        429
                    )
                elif response.status == 404:
                    raise DataSourceError(
                        f"Subreddit r/{subreddit} not found",
                        "reddit",
                        404
                    )
                elif response.status != 200:
                    raise DataSourceError(
                        f"Reddit returned status {response.status}",
                        "reddit",
                        response.status
                    )
                
                data = await response.json()
                posts = data.get("data", {}).get("children", [])
                
                return self._process_posts(posts, subreddit)
                
        except aiohttp.ClientError as e:
            raise DataSourceError(f"Network error: {str(e)}", "reddit")
    
    def _process_posts(
        self,
        posts: List[Dict],
        subreddit: str
    ) -> List[Dict[str, Any]]:
        """
        Process Reddit posts into standardized format.
        
        Args:
            posts: Raw Reddit posts
            subreddit: Source subreddit
            
        Returns:
            Processed posts
        """
        processed = []
        
        for post in posts:
            post_data = post.get("data", {})
            
            # Skip stickied/pinned posts
            if post_data.get("stickied", False):
                continue
            
            title = post_data.get("title", "")
            score = post_data.get("score", 0)
            comments = post_data.get("num_comments", 0)
            
            # Calculate engagement score
            engagement = score + (comments * 2)  # Comments weighted higher
            
            # Extract metadata
            topics = self._extract_topics(title, self.TOPIC_KEYWORDS)
            tickers = self._extract_tickers(title)
            sentiment = self._estimate_sentiment(title)
            
            created_utc = post_data.get("created_utc", 0)
            
            processed.append({
                "id": f"reddit_{post_data.get('id', '')}",
                "title": title,
                "score": score,
                "comments": comments,
                "engagement_score": engagement,
                "upvote_ratio": post_data.get("upvote_ratio", 0.5),
                "subreddit": subreddit,
                "author": post_data.get("author"),
                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                "created_at": datetime.fromtimestamp(created_utc).isoformat() if created_utc else None,
                "topics": topics,
                "related_tickers": tickers,
                "sentiment": sentiment,
                "data_source": "reddit",
                "collected_at": datetime.now().isoformat()
            })
        
        return processed
    
    def _estimate_sentiment(self, title: str) -> float:
        """
        Estimate sentiment from post title.
        
        Args:
            title: Post title
            
        Returns:
            Sentiment score (-1 to 1)
        """
        title_lower = title.lower()
        
        # Positive indicators
        positive = [
            "bull", "bullish", "buy", "moon", "rocket", "gain", "profit",
            "up", "rise", "surge", "jump", "rally", "boom", "growth",
            "strong", "beat", "breakout", " ATH", "all time high"
        ]
        
        # Negative indicators
        negative = [
            "bear", "bearish", "sell", "crash", "dump", "loss", "down",
            "fall", "drop", "decline", "bearish", "weak", "miss",
            "panic", "fear", "bear market", "correction"
        ]
        
        pos_count = sum(1 for p in positive if p in title_lower)
        neg_count = sum(1 for n in negative if n in title_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Reddit API health.
        
        Returns:
            Health status dictionary
        """
        try:
            start = datetime.now()
            await self._fetch_subreddit_posts("wallstreetbets", 1)
            latency = (datetime.now() - start).total_seconds()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "subreddits_monitored": len(self.subreddits)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "subreddits_monitored": len(self.subreddits)
            }