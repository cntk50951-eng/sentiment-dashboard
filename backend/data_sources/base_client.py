"""
Base Client for Data Sources

Provides common functionality for all data source clients including:
- Circuit breaker pattern
- Connection pooling
- Metrics collection
- Retry logic
- Error handling
"""

import asyncio
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime

from utils.decorators import retry, cache
from utils.circuit_breaker import circuit_breaker, CircuitBreakerOpen
from utils.metrics import track_performance, Timer
from utils.connection_pool import get_connection_pool
from core.exceptions import DataSourceError, RateLimitError, AuthenticationError


class DataSourceClient(ABC):
    """
    Abstract base class for data source clients.
    
    Provides:
    - Circuit breaker protection
    - Connection pooling
    - Metrics tracking
    - Standardized error handling
    """
    
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        circuit_breaker_config: Optional[Dict] = None
    ):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._pool = get_connection_pool()
        
        # Circuit breaker configuration
        cb_config = circuit_breaker_config or {
            "failure_threshold": 5,
            "recovery_timeout": 60.0,
            "half_open_max_calls": 3
        }
        self._circuit_breaker = circuit_breaker(name, **cb_config)
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with full protection.
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            params: Query parameters
            headers: Request headers
            json_data: JSON body
            timeout: Request timeout
            
        Returns:
            JSON response
            
        Raises:
            DataSourceError: On API errors
        """
        url = f"{self.base_url}{endpoint}"
        request_headers = headers or {}
        
        # Add API key if available
        if self.api_key and "Authorization" not in request_headers:
            request_headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with Timer(f"{self.name}_request"):
                async with self._pool.request(
                    method,
                    url,
                    params=params,
                    headers=request_headers,
                    json=json_data
                ) as response:
                    
                    # Handle specific status codes
                    if response.status == 429:
                        raise RateLimitError(
                            "Rate limit exceeded",
                            self.name,
                            429
                        )
                    elif response.status == 401:
                        raise AuthenticationError(
                            "Authentication failed",
                            self.name
                        )
                    elif response.status == 403:
                        raise AuthenticationError(
                            "Access forbidden",
                            self.name
                        )
                    elif response.status >= 500:
                        raise DataSourceError(
                            f"Server error: {response.status}",
                            self.name,
                            response.status
                        )
                    elif response.status >= 400:
                        raise DataSourceError(
                            f"Client error: {response.status}",
                            self.name,
                            response.status
                        )
                    
                    # Parse response
                    try:
                        data = await response.json()
                        return data
                    except Exception as e:
                        text = await response.text()
                        raise DataSourceError(
                            f"Invalid JSON response: {str(e)}",
                            self.name,
                            response.status
                        )
                        
        except asyncio.TimeoutError:
            raise DataSourceError(
                f"Request timeout after {timeout}s",
                self.name
            )
        except CircuitBreakerOpen:
            raise DataSourceError(
                "Circuit breaker is open - service temporarily unavailable",
                self.name
            )
        except Exception as e:
            if isinstance(e, DataSourceError):
                raise
            raise DataSourceError(
                f"Request failed: {str(e)}",
                self.name
            )
    
    @track_performance()
    async def fetch_with_protection(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Fetch data with circuit breaker and retry protection.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            headers: Request headers
            max_retries: Maximum retry attempts
            
        Returns:
            JSON response
        """
        @retry(max_attempts=max_retries, delay=1.0, backoff=2.0)
        @self._circuit_breaker
        async def _fetch():
            return await self._make_request(
                endpoint,
                method=method,
                params=params,
                headers=headers
            )
        
        return await _fetch()
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check data source health.
        
        Returns:
            Health status dictionary
        """
        pass
    
    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock tickers from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of ticker symbols
        """
        import re
        
        # $XXX format
        tickers = re.findall(r'\$([A-Z]{1,5})', text)
        
        # Common company names
        company_map = {
            "tesla": "TSLA", "apple": "AAPL", "amazon": "AMZN",
            "microsoft": "MSFT", "google": "GOOGL", "nvidia": "NVDA",
            "meta": "META", "netflix": "NFLX", "amd": "AMD",
            "intel": "INTC", "coinbase": "COIN", "bitcoin": "BTC",
            "ethereum": "ETH", "binance": "BNB", "cardano": "ADA",
            "solana": "SOL", "polygon": "MATIC", "ripple": "XRP",
            "dogecoin": "DOGE", "polkadot": "DOT", "avalanche": "AVAX"
        }
        
        text_lower = text.lower()
        for company, ticker in company_map.items():
            if company in text_lower and ticker not in tickers:
                tickers.append(ticker)
        
        return list(set(tickers))
    
    def _extract_topics(self, text: str, topic_keywords: Dict[str, List[str]]) -> List[str]:
        """
        Extract topics from text based on keywords.
        
        Args:
            text: Text to analyze
            topic_keywords: Dictionary of topic -> keywords
            
        Returns:
            List of matched topics
        """
        text_lower = text.lower()
        found_topics = []
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_topics.append(topic)
        
        return found_topics
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score (-1 to 1) from text.
        
        Uses keyword-based analysis for quick sentiment scoring.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score between -1 and 1
        """
        text_lower = text.lower()
        
        # Positive indicators
        positive = [
            "bull", "bullish", "buy", "moon", "rocket", "gain", "profit",
            "up", "rise", "surge", "jump", "rally", "boom", "growth",
            "strong", "beat", "breakout", "support", "long", "calls",
            " ATH", "all time high", " ATH ", "pump"
        ]
        
        # Negative indicators
        negative = [
            "bear", "bearish", "sell", "crash", "dump", "loss", "down",
            "fall", "drop", "decline", "weak", "miss", "fear", "panic",
            "resistance", "short", "puts", "bear market", "correction"
        ]
        
        pos_count = sum(1 for p in positive if p in text_lower)
        neg_count = sum(1 for n in negative if n in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def _get_sentiment_label(self, score: float) -> str:
        """
        Get sentiment label from score.
        
        Args:
            score: Sentiment score (-1 to 1)
            
        Returns:
            Sentiment label
        """
        if score > 0.3:
            return "Bullish"
        elif score < -0.3:
            return "Bearish"
        else:
            return "Neutral"