"""
NewsAPI Client
獲取全球新聞熱點
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from data_sources.base_client import DataSourceClient
from utils.decorators import cache, timing
from utils.metrics import track_performance
from core.exceptions import DataSourceError


class NewsAPIClient(DataSourceClient):
    """
    NewsAPI client with enhanced reliability and caching.
    
    Features:
    - Circuit breaker protection
    - Connection pooling
    - Intelligent caching
    - Comprehensive error handling
    """
    
    # Topic keywords for classification
    TOPIC_KEYWORDS = {
        "AI": ["ai", "artificial intelligence", "chatgpt", "machine learning", "llm", "openai", "anthropic", "claude", "gemini"],
        "Crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain", "defi", "nft", "web3", "altcoin", "solana", "cardano"],
        "Energy": ["oil", "energy", "gas", "petroleum", "renewable", "solar", "wind", "opec", "crude", "natural gas"],
        "Tech": ["tech", "technology", "software", "cloud", "saas", "semiconductor", "chip", "ai", "cybersecurity"],
        "Finance": ["fed", "interest rate", "inflation", "economy", "recession", "gdp", "fomc", "cpi", "ppi", "treasury"],
        "China": ["china", "chinese", "beijing", "shanghai", "hong kong", "taiwan", "yuan", "renminbi"],
        "EV": ["tesla", "ev", "electric vehicle", "battery", "charging", "rivian", "lucid", "nio", "byd"],
        "Semiconductor": ["chip", "semiconductor", "nvidia", "intel", "amd", "tsmc", "qualcomm", "broadcom"],
        "Healthcare": ["pharma", "biotech", "fda", "vaccine", "healthcare", "medical", "drug", "clinical trial"],
        "Real Estate": ["reit", "housing", "mortgage", "property", "real estate", "home prices", "commercial real estate"],
        "E-commerce": ["amazon", "shopify", "e-commerce", "online retail", "delivery"],
        "Gaming": ["gaming", "video game", "esports", "playstation", "xbox", "nintendo"]
    }
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="newsapi",
            base_url="https://newsapi.org/v2",
            api_key=api_key or os.getenv("NEWS_API_KEY", ""),
            circuit_breaker_config={
                "failure_threshold": 5,
                "recovery_timeout": 60.0
            }
        )
    
    @track_performance("newsapi_hot_topics")
    @cache(ttl=180.0)  # 3 minutes cache
    async def get_hot_topics(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        獲取熱點新聞話題。
        
        Args:
            category: News category (business, technology, etc.)
            limit: Maximum number of articles
            
        Returns:
            List of processed news articles
        """
        params = {
            "language": "en",
            "pageSize": min(limit, 100),  # API max is 100
        }
        
        if category:
            params["category"] = category
        
        # Use top-headlines if no query, otherwise use everything
        endpoint = "/top-headlines"
        
        try:
            data = await self.fetch_with_protection(
                endpoint,
                params=params,
                max_retries=3
            )
            
            if data.get("status") != "ok":
                error_msg = data.get("message", "Unknown error")
                raise DataSourceError(f"API error: {error_msg}", "newsapi")
            
            articles = data.get("articles", [])
            return self._process_articles(articles)
            
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"Failed to fetch news: {str(e)}", "newsapi")
    
    @track_performance("newsapi_search")
    @cache(ttl=60.0)  # 1 minute cache for searches
    async def search_news(
        self,
        query: str,
        limit: int = 10,
        sort_by: str = "relevancy"
    ) -> List[Dict[str, Any]]:
        """
        搜索特定主題的新聞。
        
        Args:
            query: Search query
            limit: Maximum results
            sort_by: Sort order (relevancy, popularity, publishedAt)
            
        Returns:
            List of matching articles
        """
        params = {
            "q": query,
            "sortBy": sort_by,
            "language": "en",
            "pageSize": min(limit, 100),
        }
        
        try:
            data = await self.fetch_with_protection(
                "/everything",
                params=params,
                max_retries=3
            )
            
            if data.get("status") != "ok":
                error_msg = data.get("message", "Unknown error")
                raise DataSourceError(f"API error: {error_msg}", "newsapi")
            
            articles = data.get("articles", [])
            return self._process_articles(articles)
            
        except DataSourceError:
            raise
        except Exception as e:
            raise DataSourceError(f"Search failed: {str(e)}", "newsapi")
    
    def _process_articles(self, articles: List[Dict]) -> List[Dict[str, Any]]:
        """
        處理新聞文章，提取投資相關信息。
        
        Args:
            articles: Raw articles from API
            
        Returns:
            Processed articles with extracted metadata
        """
        processed = []
        
        for article in articles:
            title = article.get("title", "") or ""
            description = article.get("description", "") or ""
            content = f"{title} {description}".lower()
            
            # Skip articles with removed content
            if "[removed]" in title.lower():
                continue
            
            # Extract investment themes
            topics = self._extract_topics(content, self.TOPIC_KEYWORDS)
            tickers = self._extract_tickers(title)
            
            # Calculate relevance score
            relevance = self._calculate_relevance(title, description, topics, tickers)
            
            processed.append({
                "id": f"news_{hash(title + str(article.get('publishedAt', '')))}",
                "title": title,
                "description": description,
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": article.get("url"),
                "published_at": article.get("publishedAt"),
                "topics": topics,
                "related_tickers": tickers,
                "relevance_score": relevance,
                "data_source": "newsapi",
                "collected_at": datetime.now().isoformat()
            })
        
        # Sort by relevance
        processed.sort(key=lambda x: x["relevance_score"], reverse=True)
        return processed
    
    def _calculate_relevance(
        self,
        title: str,
        description: str,
        topics: List[str],
        tickers: List[str]
    ) -> float:
        """
        Calculate article relevance score for investors.
        
        Args:
            title: Article title
            description: Article description
            topics: Extracted topics
            tickers: Related tickers
            
        Returns:
            Relevance score (0-1)
        """
        score = 0.0
        
        # Financial keywords boost
        financial_keywords = [
            "earnings", "revenue", "profit", "loss", "quarterly",
            "guidance", "outlook", "forecast", "beat", "miss",
            "upgrade", "downgrade", "target", "price", "buy", "sell",
            "merger", "acquisition", "ipo", "dividend", "stock split",
            "bullish", "bearish", "outperform", "underperform"
        ]
        
        text_lower = f"{title} {description}".lower()
        
        # Base score from financial keywords
        for keyword in financial_keywords:
            if keyword in text_lower:
                score += 0.05
        
        # Topic relevance
        score += len(topics) * 0.1
        
        # Ticker mention bonus
        score += len(tickers) * 0.15
        
        # Cap at 1.0
        return min(score, 1.0)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check NewsAPI health status.
        
        Returns:
            Health status dictionary
        """
        try:
            # Try a simple request
            start = datetime.now()
            await self.fetch_with_protection(
                "/top-headlines",
                params={"language": "en", "pageSize": 1},
                max_retries=1
            )
            latency = (datetime.now() - start).total_seconds()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency * 1000, 2),
                "api_key_configured": bool(self.api_key)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.api_key)
            }