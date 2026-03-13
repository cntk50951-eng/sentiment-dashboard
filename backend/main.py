"""
Sentiment Dashboard Backend API
FastAPI + Real-time Data Integration
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from data_sources.news_api import NewsAPIClient
from data_sources.reddit_client import RedditClient
from data_sources.coingecko import CoinGeckoClient
from data_sources.fallback_client import FallbackClient, DataAggregator
from agents.analysis_team import AnalysisTeam
from core.exceptions import DataSourceError

app = FastAPI(
    title="Sentiment Dashboard API",
    description="AI-Powered Investment Intelligence",
    version="1.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Clients
news_client = NewsAPIClient()
reddit_client = RedditClient()
crypto_client = CoinGeckoClient()
fallback_client = FallbackClient()
data_aggregator = DataAggregator()

# AI Agent Team
analysis_team = AnalysisTeam()


# ============== Models ==============

class HotTopic(BaseModel):
    id: str
    title: str
    source: str
    category: str
    sentiment: float
    mentions: int
    related_tickers: List[str]
    timestamp: datetime
    potential_opportunity: Optional[str]


class SentimentAnalysis(BaseModel):
    topic: str
    overall_sentiment: float
    bullish_percentage: float
    bearish_percentage: float
    neutral_percentage: float
    trending_keywords: List[str]


class InvestmentOpportunity(BaseModel):
    ticker: str
    opportunity_type: str
    confidence: float
    reasoning: str
    risk_level: str
    time_horizon: str


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Dict[str, Any]]


class AgentQuery(BaseModel):
    query: str


# ============== Root Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Sentiment Dashboard API",
        "version": "1.1.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "hot_topics": "/api/hot-topics",
            "sentiment": "/api/sentiment/{topic}",
            "opportunities": "/api/opportunities",
            "agent": "/api/agent/analyze",
            "crypto": "/api/market/crypto",
            "aggregated": "/api/aggregated"
        }
    }


@app.get("/api/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check for all services.
    """
    services = {}
    overall_status = "healthy"
    
    # Check NewsAPI
    try:
        news_health = await news_client.health_check()
        services["newsapi"] = news_health
    except Exception as e:
        services["newsapi"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
    
    # Check Reddit
    try:
        reddit_health = await reddit_client.health_check()
        services["reddit"] = reddit_health
    except Exception as e:
        services["reddit"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
    
    # Check CoinGecko
    try:
        crypto_data = await crypto_client.get_top_cryptos(limit=1)
        services["coingecko"] = {
            "status": "healthy" if crypto_data else "degraded",
            "data_available": bool(crypto_data)
        }
    except Exception as e:
        services["coingecko"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "degraded"
    
    # Check AI Agent
    services["ai_agent"] = {
        "status": "healthy",
        "api_configured": bool(os.getenv("MINIMAX_API_KEY")),
        "cache_stats": analysis_team.get_cache_stats()
    }
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": services
    }


# ============== Hot Topics Endpoints ==============

@app.get("/api/hot-topics")
async def get_hot_topics(
    category: Optional[str] = Query(None, description="News category filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of topics to return"),
    source: Optional[str] = Query(None, description="Filter by source: news, reddit, or all")
):
    """
    Get current hot topics from multiple sources.
    
    - **category**: Optional news category (business, technology, etc.)
    - **limit**: Number of topics to return (1-100)
    - **source**: Filter by data source (news, reddit, all)
    """
    try:
        results = []
        
        # Fetch from requested sources
        if source in (None, "all", "news"):
            try:
                news_data = await news_client.get_hot_topics(category=category, limit=limit)
                results.extend(news_data)
            except Exception as e:
                # Use fallback on failure
                fallback_data = await fallback_client.get_news(limit=limit)
                results.extend(fallback_data)
        
        if source in (None, "all", "reddit"):
            try:
                reddit_data = await reddit_client.get_hot_posts(limit=limit)
                results.extend(reddit_data)
            except Exception:
                pass  # Reddit failure is non-fatal
        
        # If both failed, get fallback
        if not results:
            results = await fallback_client.get_news(limit=limit)
        
        # AI sentiment analysis
        analyzed_topics = await analysis_team.analyze_sentiment(results)
        
        return {
            "topics": analyzed_topics[:limit],
            "total": len(analyzed_topics),
            "timestamp": datetime.now().isoformat(),
            "sources_used": source or "all"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch hot topics: {str(e)}")


@app.get("/api/aggregated")
async def get_aggregated_data(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get aggregated sentiment data from all sources with fallback support.
    """
    try:
        result = await data_aggregator.get_all_sentiment_data(
            news_client,
            reddit_client,
            limit=limit
        )
        
        # Analyze sentiment
        analyzed = await analysis_team.analyze_sentiment(
            result["aggregated"]["topics"]
        )
        
        result["aggregated"]["topics"] = analyzed
        result["timestamp"] = datetime.now().isoformat()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


# ============== Sentiment Endpoints ==============

@app.get("/api/sentiment/{topic}")
async def get_topic_sentiment(topic: str):
    """
    Get detailed sentiment analysis for a specific topic.
    
    - **topic**: The topic to analyze
    """
    try:
        # Decode topic from URL
        import urllib.parse
        decoded_topic = urllib.parse.unquote(topic)
        
        sentiment = await analysis_team.analyze_topic_sentiment(decoded_topic)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@app.post("/api/sentiment/batch")
async def batch_sentiment_analysis(topics: List[str]):
    """
    Batch sentiment analysis for multiple topics.
    
    - **topics**: List of topics to analyze
    """
    try:
        results = []
        for topic in topics:
            sentiment = await analysis_team.analyze_topic_sentiment(topic)
            results.append(sentiment)
        
        return {
            "results": results,
            "total": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


# ============== Opportunity Endpoints ==============

@app.get("/api/opportunities")
async def get_investment_opportunities(
    risk_level: str = Query("medium", regex="^(low|medium|high)$", description="Risk level preference"),
    time_horizon: str = Query("short", regex="^(short|medium|long)$", description="Investment time horizon"),
    limit: int = Query(10, ge=1, le=50, description="Number of opportunities to return")
):
    """
    Get AI-identified investment opportunities.
    
    - **risk_level**: Risk preference (low, medium, high)
    - **time_horizon**: Investment horizon (short, medium, long)
    - **limit**: Maximum number of opportunities
    """
    try:
        # Get hot topics as context
        hot_topics_result = await get_hot_topics(limit=50)
        hot_topics = hot_topics_result["topics"]
        
        # AI identifies opportunities
        opportunities = await analysis_team.identify_opportunities(
            hot_topics,
            risk_level=risk_level,
            time_horizon=time_horizon
        )
        
        return {
            "opportunities": opportunities[:limit],
            "total": len(opportunities),
            "filters": {
                "risk_level": risk_level,
                "time_horizon": time_horizon
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to identify opportunities: {str(e)}")


# ============== AI Agent Endpoints ==============

@app.post("/api/agent/analyze")
async def agent_analyze(query: AgentQuery):
    """
    AI Agent team analyzes user query with task decomposition.
    
    - **query**: User query in natural language
    """
    try:
        result = await analysis_team.process_user_query(query.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {str(e)}")


@app.get("/api/agent/cache-stats")
async def get_agent_cache_stats():
    """Get AI agent cache statistics."""
    return analysis_team.get_cache_stats()


# ============== Market Data Endpoints ==============

@app.get("/api/market/crypto")
async def get_crypto_data(
    limit: int = Query(20, ge=1, le=100),
    currency: str = Query("usd", description="Currency for prices")
):
    """
    Get real-time cryptocurrency market data.
    
    - **limit**: Number of cryptocurrencies to return
    - **currency**: Fiat currency for prices
    """
    try:
        # Try primary source first
        data = await crypto_client.get_top_cryptos(limit=limit, currency=currency)
        
        if not data:
            # Use fallback
            fallback_result = await data_aggregator.get_crypto_with_fallback(
                crypto_client,
                limit=limit
            )
            data = fallback_result["data"]
        
        return {
            "data": data,
            "count": len(data),
            "currency": currency,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch crypto data: {str(e)}")


@app.get("/api/market/crypto/{coin_id}")
async def get_crypto_details(coin_id: str):
    """
    Get detailed information for a specific cryptocurrency.
    
    - **coin_id**: CoinGecko coin ID (e.g., bitcoin, ethereum)
    """
    try:
        details = await crypto_client.get_coin_details(coin_id)
        return {
            "data": details,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch coin details: {str(e)}")


# ============== Fallback Stats ==============

@app.get("/api/fallback/stats")
async def get_fallback_stats():
    """Get fallback client usage statistics."""
    return fallback_client.get_stats()


# ============== Main ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
