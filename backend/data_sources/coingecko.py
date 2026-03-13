"""
CoinGecko API Client
獲取加密貨幣實時數據
"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp


class CoinGeckoClient:
    """
    CoinGecko API Client with caching and retry logic.
    
    Provides real-time cryptocurrency data including prices,
    market cap, volume, and price changes.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.coingecko.com/api/v3"
        self.pro_url = "https://pro-api.coingecko.com/api/v3"
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds cache
        self._last_request_time = 0
        self._min_request_interval = 1.2  # Rate limiting: max 50 calls/min for free tier
        
    async def _make_request(self, endpoint: str, params: Dict = None, use_pro: bool = False) -> Dict:
        """
        Make API request with rate limiting and retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_pro: Whether to use pro API endpoint
            
        Returns:
            API response as dictionary
        """
        import time
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        
        base = self.pro_url if (use_pro and self.api_key) else self.base_url
        url = f"{base}{endpoint}"
        
        headers = {}
        if self.api_key and use_pro:
            headers["X-CG-PRO-API-KEY"] = self.api_key
        
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
                            # Rate limited - wait longer
                            wait_time = retry_delay * (2 ** attempt)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (2 ** attempt))
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (2 ** attempt))
        
        return {}
    
    async def get_top_cryptos(self, limit: int = 20, currency: str = "usd") -> List[Dict]:
        """
        獲取市值最高的加密貨幣列表。
        
        Args:
            limit: Number of cryptocurrencies to return
            currency: Currency for price data (usd, eur, etc.)
            
        Returns:
            List of cryptocurrency data dictionaries
        """
        cache_key = f"top_cryptos_{limit}_{currency}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now().timestamp() - cached_time < self._cache_ttl:
                return cached_data
        
        try:
            params = {
                "vs_currency": currency,
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": False,
                "price_change_percentage": "24h,7d"
            }
            
            data = await self._make_request("/coins/markets", params)
            
            processed = []
            for coin in data:
                processed.append({
                    "id": coin.get("id"),
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name"),
                    "current_price": coin.get("current_price"),
                    "market_cap": coin.get("market_cap"),
                    "market_cap_rank": coin.get("market_cap_rank"),
                    "total_volume": coin.get("total_volume"),
                    "price_change_24h": coin.get("price_change_24h"),
                    "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                    "price_change_percentage_7d_in_currency": coin.get("price_change_percentage_7d_in_currency"),
                    "sparkline_in_7d": coin.get("sparkline_in_7d"),
                    "last_updated": coin.get("last_updated"),
                    "data_source": "coingecko"
                })
            
            # Update cache
            self._cache[cache_key] = (processed, datetime.now().timestamp())
            return processed
            
        except Exception as e:
            print(f"CoinGecko Error: {e}")
            # Return cached data if available, even if expired
            if cache_key in self._cache:
                return self._cache[cache_key][0]
            return []
    
    async def get_coin_details(self, coin_id: str) -> Dict:
        """
        獲取特定加密貨幣的詳細信息。
        
        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin', 'ethereum')
            
        Returns:
            Detailed cryptocurrency information
        """
        cache_key = f"coin_details_{coin_id}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now().timestamp() - cached_time < self._cache_ttl:
                return cached_data
        
        try:
            params = {
                "localization": False,
                "tickers": True,
                "market_data": True,
                "community_data": True,
                "developer_data": True,
                "sparkline": True
            }
            
            data = await self._make_request(f"/coins/{coin_id}", params)
            
            processed = {
                "id": data.get("id"),
                "symbol": data.get("symbol", "").upper(),
                "name": data.get("name"),
                "description": data.get("description", {}).get("en", ""),
                "homepage": data.get("links", {}).get("homepage", [""])[0],
                "market_data": {
                    "current_price": data.get("market_data", {}).get("current_price", {}).get("usd"),
                    "market_cap": data.get("market_data", {}).get("market_cap", {}).get("usd"),
                    "total_volume": data.get("market_data", {}).get("total_volume", {}).get("usd"),
                    "high_24h": data.get("market_data", {}).get("high_24h", {}).get("usd"),
                    "low_24h": data.get("market_data", {}).get("low_24h", {}).get("usd"),
                    "price_change_24h": data.get("market_data", {}).get("price_change_24h"),
                    "price_change_percentage_24h": data.get("market_data", {}).get("price_change_percentage_24h"),
                    "price_change_percentage_7d": data.get("market_data", {}).get("price_change_percentage_7d"),
                    "ath": data.get("market_data", {}).get("ath", {}).get("usd"),
                    "atl": data.get("market_data", {}).get("atl", {}).get("usd")
                },
                "community_data": {
                    "twitter_followers": data.get("community_data", {}).get("twitter_followers"),
                    "reddit_subscribers": data.get("community_data", {}).get("reddit_subscribers")
                },
                "last_updated": data.get("market_data", {}).get("last_updated"),
                "data_source": "coingecko"
            }
            
            # Update cache
            self._cache[cache_key] = (processed, datetime.now().timestamp())
            return processed
            
        except Exception as e:
            print(f"CoinGecko Error: {str(e)}")
            if cache_key in self._cache:
                return self._cache[cache_key][0]
            return {}
    
    async def health_check(self) -> Dict:
        """
        Check CoinGecko API health.
        
        Returns:
            Health status dictionary
        """
        try:
            start = datetime.now()
            data = await self.get_top_cryptos(limit=1)
            latency = (datetime.now() - start).total_seconds()
            
            return {
                "status": "healthy" if data else "degraded",
                "latency_ms": round(latency * 1000, 2),
                "api_key_configured": bool(self.api_key)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_key_configured": bool(self.api_key)
            }