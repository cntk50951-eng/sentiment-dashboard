"""
Pytest Configuration

Shared fixtures and configuration for tests.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_response():
    """Create a mock aiohttp response."""
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"data": []})
    response.text = AsyncMock(return_value="{}")
    return response


@pytest.fixture
def sample_news_article():
    """Sample news article for testing."""
    return {
        "title": "Tesla Stock Surges on Strong Earnings",
        "description": "Tesla reported better than expected quarterly results.",
        "source": {"name": "Test News"},
        "url": "https://test.com/article",
        "publishedAt": "2026-03-13T10:00:00Z"
    }


@pytest.fixture
def sample_reddit_post():
    """Sample Reddit post for testing."""
    return {
        "data": {
            "id": "test123",
            "title": "Buying $AAPL calls for next week",
            "score": 150,
            "num_comments": 45,
            "upvote_ratio": 0.85,
            "author": "testuser",
            "permalink": "/r/wallstreetbets/comments/test123",
            "created_utc": 1710312000,
            "stickied": False
        }
    }
