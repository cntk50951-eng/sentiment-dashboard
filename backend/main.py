"""
Sentiment Dashboard Backend API
FastAPI + Real-time Data Integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from datetime import datetime

from data_sources.news_api import NewsAPIClient
from data_sources.reddit_client import RedditClient
from data_sources.coingecko import CoinGeckoClient
from agents.analysis_team import AnalysisTeam

app = FastAPI(
    title="Sentiment Dashboard API",
    description="AI-Powered Investment Intelligence",
    version="1.0.0"
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

# AI Agent Team
analysis_team = AnalysisTeam()

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
    overall_sentiment: float  # -1 to 1
    bullish_percentage: float
    bearish_percentage: float
    neutral_percentage: float
    trending_keywords: List[str]

class InvestmentOpportunity(BaseModel):
    ticker: str
    opportunity_type: str  # 'buy', 'watch', 'avoid'
    confidence: float
    reasoning: str
    risk_level: str
    time_horizon: str

@app.get("/")
async def root():
    return {"message": "Sentiment Dashboard API", "status": "running"}

@app.get("/api/hot-topics")
async def get_hot_topics(
    category: Optional[str] = None,
    limit: int = 20
):
    """
    獲取當前熱點話題
    """
    try:
        # 並行獲取多個數據源
        news_task = asyncio.create_task(news_client.get_hot_topics(category, limit))
        reddit_task = asyncio.create_task(reddit_client.get_hot_posts(limit))
        
        news_data = await news_task
        reddit_data = await reddit_task
        
        # 合併並分析
        all_topics = news_data + reddit_data
        
        # AI 情緒分析
        analyzed_topics = await analysis_team.analyze_sentiment(all_topics)
        
        return {
            "topics": analyzed_topics,
            "total": len(analyzed_topics),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sentiment/{topic}")
async def get_topic_sentiment(topic: str):
    """
    獲取特定話題的詳細情緒分析
    """
    try:
        sentiment = await analysis_team.analyze_topic_sentiment(topic)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/opportunities")
async def get_investment_opportunities(
    risk_level: Optional[str] = "medium",
    time_horizon: Optional[str] = "short"
):
    """
    獲取 AI 識別的投資機會
    """
    try:
        # 獲取熱點話題
        hot_topics = await get_hot_topics(limit=50)
        
        # AI 分析投資機會
        opportunities = await analysis_team.identify_opportunities(
            hot_topics["topics"],
            risk_level=risk_level,
            time_horizon=time_horizon
        )
        
        return {
            "opportunities": opportunities,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent/analyze")
async def agent_analyze(query: str):
    """
    AI Agent 團隊分析用戶查詢
    """
    try:
        result = await analysis_team.process_user_query(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market/crypto")
async def get_crypto_data():
    """
    獲取加密貨幣實時數據
    """
    try:
        data = await crypto_client.get_top_cryptos()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
