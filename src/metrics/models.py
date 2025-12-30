"""SQLAlchemy ORM models for metrics storage."""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ModelTier(str, enum.Enum):
    """Model tier classification for database storage."""

    FAST = "fast"
    COMPLEX = "complex"


class RequestLog(Base):
    """
    Log of every request processed by the router.

    This is the main metrics table for analytics, debugging,
    and cost tracking. Each row represents one complete request
    processing cycle, including any escalation attempts.
    """

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Request details
    prompt_preview: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="First 500 chars of prompt"
    )
    prompt_length: Mapped[int] = mapped_column(Integer, nullable=False)

    # Complexity analysis
    complexity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected_signals: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="List of detected signal types"
    )

    # Routing decision
    initial_model: Mapped[str] = mapped_column(String(100), nullable=False)
    initial_tier: Mapped[ModelTier] = mapped_column(SQLEnum(ModelTier), nullable=False)
    final_model: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality & escalation
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    was_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_depth: Mapped[int] = mapped_column(Integer, default=0)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Performance
    latency_ms: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Initial response latency"
    )
    total_latency_ms: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Total latency including escalations"
    )

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost (USD)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Response summary
    response_preview: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="First 500 chars of response"
    )
    finish_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Error tracking
    error_occurred: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_request_logs_created_at", "created_at"),
        Index("idx_request_logs_complexity", "complexity_score"),
        Index("idx_request_logs_model", "final_model"),
        Index("idx_request_logs_escalated", "was_escalated"),
    )


class AggregatedMetrics(Base):
    """
    Pre-computed aggregated metrics for dashboard performance.

    These are computed periodically (hourly/daily) to avoid
    expensive queries on the main request_logs table.
    """

    __tablename__ = "aggregated_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="hour, day, or week"
    )

    # Request counts
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    fast_model_requests: Mapped[int] = mapped_column(Integer, default=0)
    complex_model_requests: Mapped[int] = mapped_column(Integer, default=0)

    # Escalation metrics
    escalation_count: Mapped[int] = mapped_column(Integer, default=0)
    escalation_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Quality metrics
    avg_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_below_threshold: Mapped[int] = mapped_column(Integer, default=0)

    # Performance
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p50_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Token usage
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Cost
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    cost_savings_estimate: Mapped[float] = mapped_column(
        Float, default=0.0, comment="Estimated savings vs using complex for all"
    )

    # Complexity distribution
    complexity_distribution: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="{low: x, medium: y, high: z}"
    )

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agg_metrics_period", "period_start", "period_type"),
    )
