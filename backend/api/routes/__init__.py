"""
API Routes Package

FastAPI route handlers for the sentiment dashboard API.
"""

from api.routes.sentiment import router as sentiment_router
from api.routes.opportunities import router as opportunities_router

__all__ = ["sentiment_router", "opportunities_router"]
