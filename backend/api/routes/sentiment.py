"""
Sentiment Analysis API Routes

Endpoints for sentiment analysis of stocks, crypto, and topics.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.data_aggregator import DataAggregator

router = APIRouter(prefix="/sentiment")


class SentimentRequest(BaseModel):
    """Sentiment analysis request."""
    
    text: str = Field(..., description="Text to analyze")
    context: Optional[str] = Field(None, description="Additional context")


class SentimentResponse(BaseModel):
    """Sentiment analysis response."""
    
    text: str = Field(..., description="Analyzed text")
    sentiment_score: float = Field(
        ..., 
        description="Sentiment score (-1 to 1)",
        ge=-1,
        le=1
    )
    sentiment_label: str = Field(..., description="Sentiment label (Bullish/Bearish/Neutral)")
    confidence: float = Field(
        ...,
        description="Confidence level (0 to 1)",
        ge=0,
        le=1
    )
    keywords: List[str] = Field(default=[], description="Key sentiment keywords")


class TickerSentimentRequest(BaseModel):
    """Ticker sentiment analysis request."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    include_social: bool = Field(True, description="Include social media data")
    include_news: bool = Field(True, description="Include news data")


class TickerSentimentResponse(BaseModel):
    """Ticker sentiment analysis response."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    overall_sentiment: float = Field(..., description="Overall sentiment score")
    sentiment_label: str = Field(..., description="Overall sentiment label")
    
    # Breakdown
    social_sentiment: Optional[float] = Field(None, description="Social media sentiment")
    news_sentiment: Optional[float] = Field(None, description="News sentiment")
    
    # Metrics
    mention_count: int = Field(..., description="Total mentions")
    bullish_percentage: float = Field(..., description="Percentage of bullish mentions")
    bearish_percentage: float = Field(..., description="Percentage of bearish mentions")
    neutral_percentage: float = Field(..., description="Percentage of neutral mentions")
    
    # Trends
    trending_keywords: List[str] = Field(default=[], description="Trending keywords")
    top_sources: List[str] = Field(default=[], description="Top data sources")
    
    timestamp: str = Field(..., description="Analysis timestamp")


# Initialize aggregator
aggregator = DataAggregator()


@router.post(
    "/analyze",
    response_model=SentimentResponse,
    summary="Analyze text sentiment",
    description="Analyze sentiment of provided text"
)
async def analyze_sentiment(request: SentimentRequest) -> SentimentResponse:
    """
    Analyze sentiment of provided text.
    
    Uses keyword-based sentiment analysis to determine
    bullish/bearish/neutral sentiment.
    """
    try:
        # Use aggregator's sentiment calculation
        score = aggregator._calculate_sentiment(request.text)
        label = aggregator._get_sentiment_label(score)
        
        # Extract keywords
        keywords = _extract_sentiment_keywords(request.text)
        
        # Calculate confidence based on text length and keyword density
        confidence = min(len(request.text) / 100, 1.0)
        
        return SentimentResponse(
            text=request.text,
            sentiment_score=score,
            sentiment_label=label,
            confidence=confidence,
            keywords=keywords
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sentiment analysis failed: {str(e)}"
        )


@router.get(
    "/ticker/{ticker}",
    response_model=TickerSentimentResponse,
    summary="Get ticker sentiment",
    description="Get comprehensive sentiment analysis for a stock ticker"
)
async def get_ticker_sentiment(
    ticker: str,
    include_social: bool = Query(True),
    include_news: bool = Query(True)
) -> TickerSentimentResponse:
    """
    Get comprehensive sentiment analysis for a stock ticker.
    
    Aggregates data from multiple sources including social media
    and news to provide overall sentiment metrics.
    """
    from datetime import datetime
    from utils.validators import validate_ticker
    
    # Validate ticker
    is_valid, error = validate_ticker(ticker)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    ticker = ticker.lstrip('$').upper()
    
    try:
        # Get hot topics and filter by ticker
        topics = await aggregator.get_hot_topics(limit=50)
        
        # Filter topics mentioning this ticker
        ticker_topics = [
            t for t in topics 
            if ticker in [t.upper() for t in t.get("related_tickers", [])]
        ]
        
        if not ticker_topics:
            # Return neutral sentiment if no data
            return TickerSentimentResponse(
                ticker=ticker,
                overall_sentiment=0.0,
                sentiment_label="Neutral",
                mention_count=0,
                bullish_percentage=33.3,
                bearish_percentage=33.3,
                neutral_percentage=33.4,
                trending_keywords=[],
                top_sources=[],
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        
        # Calculate aggregated metrics
        sentiments = [t.get("sentiment", 0) for t in ticker_topics]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        # Count sentiment distribution
        bullish = sum(1 for s in sentiments if s > 0.3)
        bearish = sum(1 for s in sentiments if s < -0.3)
        neutral = len(sentiments) - bullish - bearish
        
        total = len(sentiments)
        
        # Extract trending keywords
        all_keywords = []
        for topic in ticker_topics:
            all_keywords.extend(topic.get("topics", []))
        
        trending = list(set(all_keywords))[:10]
        
        # Get top sources
        sources = list(set(t.get("source", "") for t in ticker_topics))[:5]
        
        return TickerSentimentResponse(
            ticker=ticker,
            overall_sentiment=round(avg_sentiment, 2),
            sentiment_label=aggregator._get_sentiment_label(avg_sentiment),
            mention_count=len(ticker_topics),
            bullish_percentage=round(bullish / total * 100, 1),
            bearish_percentage=round(bearish / total * 100, 1),
            neutral_percentage=round(neutral / total * 100, 1),
            trending_keywords=trending,
            top_sources=sources,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze ticker sentiment: {str(e)}"
        )


@router.get(
    "/market-overview",
    summary="Get market sentiment overview",
    description="Get overall market sentiment across all tracked assets"
)
async def get_market_overview() -> dict:
    """
    Get overall market sentiment overview.
    
    Returns aggregated sentiment metrics across all
    tracked stocks and cryptocurrencies.
    """
    from datetime import datetime
    
    try:
        topics = await aggregator.get_hot_topics(limit=100)
        
        if not topics:
            return {
                "overall_sentiment": 0,
                "sentiment_label": "Neutral",
                "total_topics": 0,
                "bullish_ratio": 0.33,
                "bearish_ratio": 0.33,
                "neutral_ratio": 0.34,
                "top_categories": [],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        sentiments = [t.get("sentiment", 0) for t in topics]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        bullish = sum(1 for s in sentiments if s > 0.3)
        bearish = sum(1 for s in sentiments if s < -0.3)
        neutral = len(sentiments) - bullish - bearish
        total = len(sentiments)
        
        # Category breakdown
        categories = {}
        for topic in topics:
            cat = topic.get("category", "Other")
            categories[cat] = categories.get(cat, 0) + 1
        
        top_categories = sorted(
            [{"name": k, "count": v} for k, v in categories.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]
        
        return {
            "overall_sentiment": round(avg_sentiment, 2),
            "sentiment_label": aggregator._get_sentiment_label(avg_sentiment),
            "total_topics": total,
            "bullish_ratio": round(bullish / total, 2),
            "bearish_ratio": round(bearish / total, 2),
            "neutral_ratio": round(neutral / total, 2),
            "top_categories": top_categories,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market overview: {str(e)}"
        )


def _extract_sentiment_keywords(text: str) -> List[str]:
    """Extract sentiment-related keywords from text."""
    text_lower = text.lower()
    
    positive_keywords = [
        "bull", "buy", "moon", "rocket", "gain", "profit", "up", "rise",
        "surge", "jump", "rally", "boom", "growth", "strong", "beat",
        "breakout", "support", "long", "calls"
    ]
    
    negative_keywords = [
        "bear", "sell", "crash", "dump", "loss", "down", "fall", "drop",
        "decline", "bearish", "weak", "miss", "fear", "panic",
        "resistance", "short", "puts"
    ]
    
    found = []
    for word in positive_keywords + negative_keywords:
        if word in text_lower:
            found.append(word)
    
    return found[:10]  # Limit to top 10
