"""
HTTP Connection Pool Management

Provides efficient connection pooling for HTTP requests with:
- Persistent connections
- Connection reuse
- Timeout management
- SSL session reuse
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager


class ConnectionPool:
    """
    Managed HTTP connection pool for efficient API calls.
    
    Features:
    - Connection reuse across requests
    - Configurable pool size
    - Keep-alive support
    - Automatic cleanup
    """
    
    def __init__(
        self,
        pool_size: int = 100,
        keepalive_timeout: float = 30.0,
        ttl_dns_cache: int = 300,
        use_dns_cache: bool = True
    ):
        self.pool_size = pool_size
        self.keepalive_timeout = keepalive_timeout
        self.ttl_dns_cache = ttl_dns_cache
        self.use_dns_cache = use_dns_cache
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._lock = asyncio.Lock()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pool."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    self._connector = aiohttp.TCPConnector(
                        limit=self.pool_size,
                        limit_per_host=20,
                        keepalive_timeout=self.keepalive_timeout,
                        ttl_dns_cache=self.ttl_dns_cache,
                        use_dns_cache=self.use_dns_cache,
                        enable_cleanup_closed=True,
                        force_close=False,
                    )
                    
                    timeout = aiohttp.ClientTimeout(
                        total=30,
                        connect=10,
                        sock_read=20
                    )
                    
                    self._session = aiohttp.ClientSession(
                        connector=self._connector,
                        timeout=timeout,
                        raise_for_status=False
                    )
        
        return self._session
    
    @asynccontextmanager
    async def request(
        self,
        method: str,
        url: str,
        **kwargs
    ):
        """
        Make HTTP request using pooled connection.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional aiohttp request arguments
            
        Yields:
            aiohttp.ClientResponse
        """
        session = await self._get_session()
        async with session.request(method, url, **kwargs) as response:
            yield response
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make GET request."""
        session = await self._get_session()
        return await session.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make POST request."""
        session = await self._get_session()
        return await session.post(url, **kwargs)
    
    async def close(self):
        """Close connection pool and cleanup resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()
        self._session = None
        self._connector = None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if self._connector:
            return {
                "limit": self._connector.limit,
                "limit_per_host": self._connector.limit_per_host,
                "size": self._connector.size,
                "num_connections": len(self._connector._conns),
                "num_acquired": len(self._connector._acquired),
            }
        return {"status": "not_initialized"}


# Global connection pool instance
_global_pool: Optional[ConnectionPool] = None


def get_connection_pool(
    pool_size: int = 100,
    keepalive_timeout: float = 30.0
) -> ConnectionPool:
    """
    Get global connection pool instance.
    
    Args:
        pool_size: Maximum connections in pool
        keepalive_timeout: Keep-alive timeout in seconds
        
    Returns:
        ConnectionPool instance
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = ConnectionPool(
            pool_size=pool_size,
            keepalive_timeout=keepalive_timeout
        )
    return _global_pool


async def close_global_pool():
    """Close global connection pool."""
    global _global_pool
    if _global_pool:
        await _global_pool.close()
        _global_pool = None
