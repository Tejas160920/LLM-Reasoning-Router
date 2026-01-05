"""Metrics API endpoint.

This module provides endpoints for querying aggregated metrics
and monitoring the router's performance.
"""

from typing import Literal

from fastapi import APIRouter, Query

from src.dependencies import MetricsServiceDep
from src.metrics.schemas import DashboardMetrics, RequestMetrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=DashboardMetrics)
async def get_metrics(
    metrics_service: MetricsServiceDep,
    period: Literal["last_hour", "last_day", "last_week"] = Query(
        default="last_hour",
        description="Time period for metrics aggregation",
    ),
) -> DashboardMetrics:
    """
    Get aggregated metrics for the dashboard.

    Returns comprehensive metrics including:
    - Request counts by model
    - Escalation rates
    - Quality scores
    - Latency percentiles
    - Cost tracking
    - Complexity distribution

    Use this endpoint for monitoring dashboards and analytics.
    """
    return await metrics_service.get_metrics(period)


@router.get("/request/{request_id}", response_model=RequestMetrics | None)
async def get_request_metrics(
    request_id: str,
    metrics_service: MetricsServiceDep,
) -> RequestMetrics | None:
    """
    Get metrics for a specific request.

    Returns detailed metrics for a single request including
    routing decision, quality score, latency, and cost.

    Useful for debugging specific requests.
    """
    return await metrics_service.get_request_metrics(request_id)


@router.get("/summary")
async def get_metrics_summary(
    metrics_service: MetricsServiceDep,
) -> dict:
    """
    Get a quick summary of key metrics.

    Returns a simplified view of the most important metrics
    for quick status checks.
    """
    metrics = await metrics_service.get_metrics("last_hour")

    return {
        "total_requests_last_hour": metrics.total_requests,
        "escalation_rate": f"{metrics.escalation_rate:.1f}%",
        "avg_quality_score": f"{metrics.avg_quality_score:.1f}",
        "avg_latency_ms": f"{metrics.avg_latency_ms:.0f}",
        "total_cost_usd": f"${metrics.total_cost:.4f}",
        "fast_model_usage": f"{metrics.requests_by_model.get('gemini-2.0-flash', 0)}",
        "complex_model_usage": f"{metrics.requests_by_model.get('gemini-2.0-flash-thinking-exp', 0)}",
    }
