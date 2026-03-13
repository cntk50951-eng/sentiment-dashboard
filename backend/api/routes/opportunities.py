"""
Investment Opportunities API Routes

Endpoints for discovering and analyzing investment opportunities.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.data_aggregator import DataAggregator
from agents.analysis_team import AnalysisTeam

router = APIRouter(prefix="/opportunities")


class OpportunityResponse(BaseModel):
    """Investment opportunity response."""
    
    ticker: str = Field(..., description="Stock/crypto ticker")
    opportunity_type: str = Field(
        ...,
        description="Type: buy, watch, avoid, research"
    )
    confidence: float = Field(
        ...,
        description="Confidence score (0-100)",
        ge=0,
        le=100
    )
    reasoning: str = Field(..., description="AI reasoning for the opportunity")
    risk_level: str = Field(
        ...,
        description="Risk level: low, medium, high"
    )
    time_horizon: str = Field(
        ...,
        description="Time horizon: short, medium, long"
    )
    sentiment_score: float = Field(..., description="Current sentiment score")
    mention_momentum: float = Field(..., description="Mention growth rate")
    related_topics: List[str] = Field(default=[], description="Related topics")
    identified_at: str = Field(..., description="Identification timestamp")


class OpportunitiesListResponse(BaseModel):
    """List of opportunities response."""
    
    opportunities: List[OpportunityResponse]
    total: int
    filters_applied: dict
    generated_at: str


class OpportunityFilterRequest(BaseModel):
    """Request to filter opportunities."""
    
    risk_level: Optional[str] = Field(None, description="Filter by risk level")
    time_horizon: Optional[str] = Field(None, description="Filter by time horizon")
    min_confidence: float = Field(50.0, description="Minimum confidence score")
    category: Optional[str] = Field(None, description="Filter by category")


# Initialize services
aggregator = DataAggregator()
analysis_team = AnalysisTeam()


@router.get(
    "",
    response_model=OpportunitiesListResponse,
    summary="Get investment opportunities",
    description="Get AI-identified investment opportunities"
)
async def get_opportunities(
    risk_level: Optional[str] = Query(None, description="Filter by risk: low/medium/high"),
    time_horizon: Optional[str] = Query(None, description="Filter by horizon: short/medium/long"),
    min_confidence: float = Query(50.0, ge=0, le=100, description="Minimum confidence"),
    limit: int = Query(10, ge=1, le=50, description="Number of opportunities")
) -> OpportunitiesListResponse:
    """
    Get AI-identified investment opportunities.
    
    Analyzes hot topics and sentiment data to identify
    potential investment opportunities with risk assessment.
    """
    from datetime import datetime
    
    try:
        # Get hot topics
        topics = await aggregator.get_hot_topics(limit=50)
        
        # Use analysis team to identify opportunities
        opportunities_data = await analysis_team.identify_opportunities(
            topics,
            risk_level=risk_level or "medium",
            time_horizon=time_horizon or "short"
        )
        
        # Convert to response model
        opportunities = []
        for opp in opportunities_data:
            # Apply filters
            if min_confidence and opp.get("confidence", 0) < min_confidence:
                continue
            
            if risk_level and opp.get("risk_level") != risk_level:
                continue
            
            if time_horizon and opp.get("time_horizon") != time_horizon:
                continue
            
            opportunities.append(OpportunityResponse(
                ticker=opp.get("ticker", "UNKNOWN"),
                opportunity_type=opp.get("opportunity_type", "watch"),
                confidence=opp.get("confidence", 50.0),
                reasoning=opp.get("reasoning", ""),
                risk_level=opp.get("risk_level", "medium"),
                time_horizon=opp.get("time_horizon", "short"),
                sentiment_score=opp.get("sentiment_score", 0.0),
                mention_momentum=opp.get("mention_momentum", 0.0),
                related_topics=opp.get("related_topics", []),
                identified_at=opp.get("identified_at", datetime.utcnow().isoformat())
            ))
        
        # Sort by confidence
        opportunities.sort(key=lambda x: x.confidence, reverse=True)
        
        return OpportunitiesListResponse(
            opportunities=opportunities[:limit],
            total=len(opportunities),
            filters_applied={
                "risk_level": risk_level,
                "time_horizon": time_horizon,
                "min_confidence": min_confidence
            },
            generated_at=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get opportunities: {str(e)}"
        )


@router.get(
    "/trending",
    summary="Get trending opportunities",
    description="Get opportunities with highest momentum"
)
async def get_trending_opportunities(
    limit: int = Query(5, ge=1, le=20)
) -> List[OpportunityResponse]:
    """
    Get trending opportunities with highest momentum.
    
    Returns opportunities sorted by mention momentum
    and recent sentiment changes.
    """
    from datetime import datetime
    
    try:
        topics = await aggregator.get_hot_topics(limit=50)
        
        # Identify opportunities
        opportunities_data = await analysis_team.identify_opportunities(
            topics,
            risk_level="medium",
            time_horizon="short"
        )
        
        # Sort by mention momentum
        opportunities_data.sort(
            key=lambda x: x.get("mention_momentum", 0),
            reverse=True
        )
        
        return [
            OpportunityResponse(
                ticker=opp.get("ticker", "UNKNOWN"),
                opportunity_type=opp.get("opportunity_type", "watch"),
                confidence=opp.get("confidence", 50.0),
                reasoning=opp.get("reasoning", ""),
                risk_level=opp.get("risk_level", "medium"),
                time_horizon=opp.get("time_horizon", "short"),
                sentiment_score=opp.get("sentiment_score", 0.0),
                mention_momentum=opp.get("mention_momentum", 0.0),
                related_topics=opp.get("related_topics", []),
                identified_at=opp.get("identified_at", datetime.utcnow().isoformat())
            )
            for opp in opportunities_data[:limit]
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending opportunities: {str(e)}"
        )


@router.get(
    "/{ticker}",
    response_model=OpportunityResponse,
    summary="Get opportunity for specific ticker",
    description="Get detailed opportunity analysis for a specific ticker"
)
async def get_ticker_opportunity(ticker: str) -> OpportunityResponse:
    """
    Get detailed opportunity analysis for a specific ticker.
    
    Provides comprehensive analysis including sentiment,
    momentum, and risk assessment.
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
        # Get topics for this ticker
        topics = await aggregator.get_hot_topics(limit=50)
        ticker_topics = [
            t for t in topics
            if ticker in [t.upper() for t in t.get("related_tickers", [])]
        ]
        
        if not ticker_topics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for ticker {ticker}"
            )
        
        # Analyze
        opportunities = await analysis_team.identify_opportunities(
            ticker_topics,
            risk_level="medium",
            time_horizon="short"
        )
        
        if not opportunities:
            # Create neutral opportunity
            return OpportunityResponse(
                ticker=ticker,
                opportunity_type="research",
                confidence=50.0,
                reasoning=f"Limited data available for {ticker}. Consider researching further.",
                risk_level="medium",
                time_horizon="medium",
                sentiment_score=0.0,
                mention_momentum=0.0,
                related_topics=[],
                identified_at=datetime.utcnow().isoformat() + "Z"
            )
        
        opp = opportunities[0]
        return OpportunityResponse(
            ticker=opp.get("ticker", ticker),
            opportunity_type=opp.get("opportunity_type", "watch"),
            confidence=opp.get("confidence", 50.0),
            reasoning=opp.get("reasoning", ""),
            risk_level=opp.get("risk_level", "medium"),
            time_horizon=opp.get("time_horizon", "short"),
            sentiment_score=opp.get("sentiment_score", 0.0),
            mention_momentum=opp.get("mention_momentum", 0.0),
            related_topics=opp.get("related_topics", []),
            identified_at=opp.get("identified_at", datetime.utcnow().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze opportunity: {str(e)}"
        )


@router.post(
    "/analyze",
    summary="Analyze custom opportunity",
    description="Analyze a custom ticker or topic for opportunities"
)
async def analyze_custom_opportunity(
    query: str,
    risk_level: str = Query("medium"),
    time_horizon: str = Query("short")
) -> OpportunityResponse:
    """
    Analyze a custom query for investment opportunities.
    
    Allows analysis of any ticker or topic not in the
    pre-computed opportunities list.
    """
    from datetime import datetime
    
    try:
        # Search for topics related to query
        # This would typically involve searching news/social
        # For now, return a research recommendation
        
        return OpportunityResponse(
            ticker=query.upper(),
            opportunity_type="research",
            confidence=50.0,
            reasoning=f"Custom analysis for {query}. Further research recommended.",
            risk_level=risk_level,
            time_horizon=time_horizon,
            sentiment_score=0.0,
            mention_momentum=0.0,
            related_topics=[],
            identified_at=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
