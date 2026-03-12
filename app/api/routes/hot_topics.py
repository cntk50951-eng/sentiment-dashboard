"""
Hot Topics API Routes

Endpoints for retrieving and analyzing hot investment topics
from various data sources.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.core.logging import get_logger
from app.services.data_aggregator import DataAggregator

logger = get_logger(__name__)
router = APIRouter(prefix="/hot-topics")


class HotTopicResponse(BaseModel):
    """Hot topic response model."""
    
    id: str = Field(..., description="Topic unique identifier")
    title: str = Field(..., description="Topic title")
    source: str = Field(..., description="Data source (newsapi/reddit)")
    category: str = Field(..., description="Topic category")
    sentiment: float = Field(..., description="Sentiment score (-1 to 1)", ge=-1, le=1)
    mentions: int = Field(..., description="Number of mentions", ge=0)
    related_tickers: List[str] = Field(default=[], description="Related stock tickers")
    timestamp: str = Field(..., description="Topic timestamp (ISO format)")
    url: Optional[str] = Field(None, description="Source URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "topic_123",
                "title": "Nvidia AI Investment",
                "source": "reddit",
                "category": "AI",
                "sentiment": 0.75,
                "mentions": 1250,
                "related_tickers": ["NVDA", "AMD"],
                "timestamp": "2026-03-12T23:00:00Z",
                "url": "https://reddit.com/r/..."
            }
        }


class HotTopicsListResponse(BaseModel):
    """List of hot topics response."""
    
    topics: List[HotTopicResponse] = Field(..., description="List of hot topics")
    total: int = Field(..., description="Total number of topics")
    timestamp: str = Field(..., description="Response timestamp")


# Service dependency
def get_data_aggregator() -> DataAggregator:
    """Get data aggregator service instance."""
    return DataAggregator()


@router.get(
    "",
    response_model=HotTopicsListResponse,
    summary="Get hot investment topics",
    description="Retrieve current hot investment topics from multiple data sources",
    responses={
        200: {"description": "Successfully retrieved hot topics"},
        502: {"description": "External API error"},
        500: {"description": "Internal server error"},
    }
)
async def get_hot_topics(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100, description="Number of topics to return"),
    aggregator: DataAggregator = Depends(get_data_aggregator)
) -> HotTopicsListResponse:
    """
    Get current hot investment topics.
    
    Retrieves and analyzes hot topics from NewsAPI and Reddit,
    including sentiment analysis and related stock tickers.
    
    Args:
        category: Optional category filter
        limit: Maximum number of topics to return
        aggregator: Data aggregator service
        
    Returns:
        HotTopicsListResponse: List of hot topics with metadata
    """
    logger.info(
        "fetching_hot_topics",
        category=category,
        limit=limit,
    )
    
    try:
        topics = await aggregator.get_hot_topics(
            category=category,
            limit=limit
        )
        
        logger.info(
            "hot_topics_fetched",
            count=len(topics),
        )
        
        return HotTopicsListResponse(
            topics=topics,
            total=len(topics),
            timestamp=__import__('datetime').datetime.utcnow().isoformat() + "Z"
        )
        
    except ExternalAPIError as e:
        logger.error(
            "external_api_error",
            error=str(e),
            api_name=e.details.get("api_name", "unknown")
        )
        raise
    except Exception as e:
        logger.exception("unexpected_error_fetching_topics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch hot topics"
        )


@router.get(
    "/categories",
    summary="Get available categories",
    description="Get list of available topic categories"
)
async def get_categories() -> dict:
    """Get available topic categories."""
    return {
        "categories": [
            {"id": "all", "name": "All Topics"},
            {"id": "stocks", "name": "Stocks"},
            {"id": "crypto", "name": "Cryptocurrency"},
            {"id": "tech", "name": "Technology"},
            {"id": "ai", "name": "AI & Machine Learning"},
            {"id": "energy", "name": "Energy"},
            {"id": "finance", "name": "Finance"},
        ]
    }
