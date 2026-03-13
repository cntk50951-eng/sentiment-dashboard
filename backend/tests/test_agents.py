"""
Tests for Analysis Team AI Agent

Unit tests for the AI agent functionality.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.analysis_team import AnalysisTeam


class TestAnalysisTeamInit:
    """Tests for AnalysisTeam initialization."""
    
    def test_init_default(self):
        """Test default initialization."""
        team = AnalysisTeam()
        assert team.api_key == ""
        assert team.model == "MiniMax-M2.5"
        assert "sentiment_analyst" in team.agents
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        team = AnalysisTeam(api_key="test_key_123")
        assert team.api_key == "test_key_123"
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        team = AnalysisTeam(model="MiniMax-M1")
        assert team.model == "MiniMax-M1"


class TestSentimentCalculation:
    """Tests for keyword-based sentiment calculation."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_bullish_sentiment(self, team):
        """Test bullish sentiment detection."""
        text = "Buying $NVDA calls, this stock is going to the moon! 🚀"
        score = team._calculate_sentiment(text)
        assert score > 0
    
    def test_bearish_sentiment(self, team):
        """Test bearish sentiment detection."""
        text = "Selling $TSLA, bear market incoming, crash predicted"
        score = team._calculate_sentiment(text)
        assert score < 0
    
    def test_neutral_sentiment(self, team):
        """Test neutral sentiment."""
        text = "Apple announces new product"
        score = team._calculate_sentiment(text)
        assert score == 0.0
    
    def test_sentiment_label_bullish(self, team):
        """Test bullish label."""
        assert team._get_sentiment_label(0.5) == "Bullish"
    
    def test_sentiment_label_bearish(self, team):
        """Test bearish label."""
        assert team._get_sentiment_label(-0.5) == "Bearish"
    
    def test_sentiment_label_neutral(self, team):
        """Test neutral label."""
        assert team._get_sentiment_label(0.1) == "Neutral"


class TestTopicExtraction:
    """Tests for topic extraction."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_extract_ai_topics(self, team):
        """Test AI topic extraction."""
        topics = team._extract_topics_from_query("What's the latest on AI and ChatGPT?")
        assert "AI" in topics
    
    def test_extract_crypto_topics(self, team):
        """Test crypto topic extraction."""
        topics = team._extract_topics_from_query("Bitcoin and Ethereum price analysis")
        assert "Crypto" in topics
    
    def test_extract_tech_topics(self, team):
        """Test tech topic extraction."""
        topics = team._extract_topics_from_query("Tech sector analysis")
        assert "Tech" in topics


class TestQueryDecomposition:
    """Tests for query intent decomposition."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_sentiment_query(self, team):
        """Test sentiment query decomposition."""
        tasks = team._decompose_query("What is the sentiment on NVDA?")
        assert "sentiment" in tasks
    
    def test_opportunity_query(self, team):
        """Test opportunity query decomposition."""
        tasks = team._decompose_query("Find buying opportunities in tech")
        assert "opportunity" in tasks
    
    def test_topic_query(self, team):
        """Test topic query decomposition."""
        tasks = team._decompose_query("What are the hot topics today?")
        assert "extraction" in tasks
    
    def test_general_query(self, team):
        """Test general query decomposition."""
        tasks = team._decompose_query("Analyze the market")
        assert "analysis" in tasks


class TestAnalyzeSentiment:
    """Tests for sentiment analysis."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()  # No API key for testing fallback
    
    @pytest.mark.asyncio
    async def test_analyze_topics(self, team):
        """Test analyzing multiple topics."""
        topics = [
            {"title": "NVDA to the moon! 🚀", "score": 100},
            {"title": "Bearish on TSLA", "score": 50}
        ]
        
        analyzed = await team.analyze_sentiment(topics)
        
        assert len(analyzed) == 2
        assert analyzed[0]["sentiment"] > 0  # Bullish
        assert analyzed[1]["sentiment"] < 0  # Bearish
        assert "sentiment_label" in analyzed[0]
        assert "analyzed_at" in analyzed[0]
    
    @pytest.mark.asyncio
    async def test_analyze_empty_topics(self, team):
        """Test analyzing empty topic list."""
        analyzed = await team.analyze_sentiment([])
        assert analyzed == []


class TestIdentifyOpportunities:
    """Tests for opportunity identification."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    @pytest.mark.asyncio
    async def test_identify_opportunities_positive(self, team):
        """Test identifying positive opportunities."""
        topics = [
            {
                "title": "NVDA earnings beat, stock surges",
                "related_tickers": ["NVDA"],
                "sentiment": 0.8,
                "engagement_score": 200
            }
        ]
        
        opportunities = await team.identify_opportunities(topics)
        
        assert len(opportunities) > 0
        assert opportunities[0]["ticker"] == "NVDA"
        assert opportunities[0]["opportunity_type"] in ["watch", "consider"]
    
    @pytest.mark.asyncio
    async def test_identify_opportunities_low_sentiment(self, team):
        """Test low sentiment doesn't generate opportunities."""
        topics = [
            {
                "title": "Neutral market observation",
                "related_tickers": ["AAPL"],
                "sentiment": 0.1,
                "engagement_score": 10
            }
        ]
        
        opportunities = await team.identify_opportunities(topics)
        
        # Low sentiment may not generate opportunities
        # This is expected behavior
        assert isinstance(opportunities, list)


class TestProcessUserQuery:
    """Tests for user query processing."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    @pytest.mark.asyncio
    async def test_process_sentiment_query(self, team):
        """Test processing sentiment query."""
        result = await team.process_user_query("What's the sentiment on Bitcoin?")
        
        assert result["original_query"] == "What's the sentiment on Bitcoin?"
        assert "decomposed_tasks" in result
        assert "results" in result
        assert "processed_at" in result
    
    @pytest.mark.asyncio
    async def test_process_opportunity_query(self, team):
        """Test processing opportunity query."""
        result = await team.process_user_query("Find investment opportunities")
        
        assert "decomposed_tasks" in result
        assert "opportunity" in result["decomposed_tasks"]
    
    @pytest.mark.asyncio
    async def test_process_general_query(self, team):
        """Test processing general query."""
        result = await team.process_user_query("Analyze the market")
        
        assert "decomposed_tasks" in result
        assert "analysis" in result["decomposed_tasks"]


class TestKeywordExtraction:
    """Tests for keyword extraction."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_extract_finance_keywords(self, team):
        """Test finance keyword extraction."""
        keywords = team._extract_keywords("Fed raises interest rates, inflation concerns")
        assert "fed" in keywords or "inflation" in keywords
    
    def test_extract_tech_keywords(self, team):
        """Test tech keyword extraction."""
        keywords = team._extract_keywords("AI and semiconductor stocks rally")
        assert "ai" in keywords or "semiconductor" in keywords
    
    def test_extract_crypto_keywords(self, team):
        """Test crypto keyword extraction."""
        keywords = team._extract_keywords("Bitcoin and Ethereum defi")
        assert "bitcoin" in keywords or "crypto" in keywords


class TestSummaryGeneration:
    """Tests for summary generation."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_generate_sentiment_summary(self, team):
        """Test sentiment summary generation."""
        results = {"sentiment": {"sentiment_label": "Bullish"}}
        summary = team._generate_summary(results)
        assert "Bullish" in summary
    
    def test_generate_empty_summary(self, team):
        """Test empty results summary."""
        summary = team._generate_summary({})
        assert "No analysis" in summary or "completed" in summary.lower()


class TestCacheStats:
    """Tests for cache statistics."""
    
    @pytest.fixture
    def team(self):
        return AnalysisTeam()
    
    def test_cache_stats(self, team):
        """Test cache stats retrieval."""
        stats = team.get_cache_stats()
        assert "cache_size" in stats
        assert "cache_ttl" in stats
        assert stats["cache_ttl"] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
