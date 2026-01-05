"""API router aggregation.

This module combines all v1 API routes into a single router.
"""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .chat import router as chat_router
from .health import router as health_router
from .metrics import router as metrics_router

# Create the main v1 API router
api_router = APIRouter(prefix="/v1")

# Include all sub-routers
api_router.include_router(analyze_router)
api_router.include_router(chat_router)
api_router.include_router(metrics_router)
api_router.include_router(health_router)
