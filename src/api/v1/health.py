"""Health check API endpoints.

This module provides health check endpoints for monitoring
and container orchestration (Kubernetes, Docker).
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from src.dependencies import DbSessionDep, SettingsDep
from src.metrics.schemas import HealthStatus

router = APIRouter(tags=["health"])

# Track startup time for uptime calculation
_startup_time = time.time()


@router.get("/health", response_model=HealthStatus)
async def health_check(
    settings: SettingsDep,
    db: DbSessionDep,
) -> HealthStatus:
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connectivity
    - LLM API availability (placeholder - would need actual check)
    - Application version and uptime
    """
    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # LLM API check would require making a test request
    # For now, assume available if API key is configured
    llm_status = "available" if settings.gemini_api_key else "not_configured"

    # Determine overall status
    if db_status == "connected" and llm_status == "available":
        status = "healthy"
    elif db_status == "connected" or llm_status == "available":
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthStatus(
        status=status,
        database=db_status,
        llm_api=llm_status,
        version=settings.app_version,
        uptime_seconds=time.time() - _startup_time,
        last_request_at=datetime.now(timezone.utc),  # Would track actual last request
    )


@router.get("/ready")
async def readiness_check(
    db: DbSessionDep,
) -> dict:
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to receive traffic.
    Checks database connectivity before declaring ready.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False, "reason": "database_unavailable"}


@router.get("/live")
async def liveness_check() -> dict:
    """
    Kubernetes liveness probe.

    Returns 200 if the application is alive.
    This is a simple check - if we can respond, we're alive.
    """
    return {"alive": True}


@router.get("/info")
async def app_info(
    settings: SettingsDep,
) -> dict:
    """
    Get application information.

    Returns version, configuration summary, and runtime info.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "fast_model": settings.fast_model,
        "complex_model": settings.complex_model,
        "complexity_thresholds": {
            "low": settings.complexity_threshold_low,
            "high": settings.complexity_threshold_high,
        },
        "quality_threshold": settings.quality_threshold,
        "max_escalation_depth": settings.max_escalation_depth,
        "uptime_seconds": time.time() - _startup_time,
    }
