"""Pydantic schemas for metrics responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class RequestMetrics(BaseModel):
    """Metrics for a single request."""

    request_id: str
    complexity_score: int
    initial_model: str
    final_model: str
    was_escalated: bool
    quality_score: int | None
    latency_ms: float
    tokens_used: int
    estimated_cost: float


class ComplexityDistribution(BaseModel):
    """Distribution of requests by complexity level."""

    low: int = Field(default=0, description="Requests with complexity < 30")
    medium: int = Field(default=0, description="Requests with complexity 30-70")
    high: int = Field(default=0, description="Requests with complexity > 70")


class DashboardMetrics(BaseModel):
    """Aggregated metrics for dashboard display."""

    period: str = Field(description="Time period for these metrics")

    # Counts
    total_requests: int = Field(default=0)
    requests_by_model: dict[str, int] = Field(default_factory=dict)

    # Routing effectiveness
    escalation_count: int = Field(default=0, description="Number of escalated requests")
    escalation_rate: float = Field(
        default=0.0, description="Percentage of requests that were escalated"
    )
    avg_complexity_score: float = Field(default=0.0)
    complexity_distribution: ComplexityDistribution = Field(
        default_factory=ComplexityDistribution
    )

    # Quality
    avg_quality_score: float = Field(default=0.0)
    quality_issues_count: int = Field(
        default=0, description="Requests with quality below threshold"
    )

    # Performance
    avg_latency_ms: float = Field(default=0.0)
    p95_latency_ms: float = Field(default=0.0)

    # Cost
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    cost_savings: float = Field(
        default=0.0, description="Estimated savings vs using pro for everything"
    )

    # Token usage
    total_tokens: int = Field(default=0)
    tokens_by_model: dict[str, int] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "period": "last_hour",
                "total_requests": 150,
                "requests_by_model": {
                    "gemini-2.0-flash": 120,
                    "gemini-2.0-flash-thinking-exp": 30,
                },
                "escalation_rate": 12.5,
                "avg_complexity_score": 42.3,
                "complexity_distribution": {"low": 80, "medium": 50, "high": 20},
                "avg_quality_score": 78.5,
                "quality_issues_count": 15,
                "avg_latency_ms": 450.2,
                "p95_latency_ms": 1200.5,
                "total_cost": 0.25,
                "cost_savings": 1.75,
                "total_tokens": 45000,
                "tokens_by_model": {
                    "gemini-2.0-flash": 35000,
                    "gemini-2.0-flash-thinking-exp": 10000,
                },
            }
        }


class HealthStatus(BaseModel):
    """Health check response."""

    status: str = Field(description="Overall health status")
    database: str = Field(description="Database connection status")
    llm_api: str = Field(description="LLM API availability status")
    version: str = Field(description="Application version")
    uptime_seconds: float = Field(description="Time since application start")
    last_request_at: datetime | None = Field(
        default=None, description="Timestamp of last processed request"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "database": "connected",
                "llm_api": "available",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "last_request_at": "2024-01-15T10:30:00Z",
            }
        }
