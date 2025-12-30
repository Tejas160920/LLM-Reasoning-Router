"""Initial database schema

Revision ID: 0001
Revises:
Create Date: 2024-01-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ModelTier enum type
    modeltier_enum = postgresql.ENUM("fast", "complex", name="modeltier", create_type=False)
    modeltier_enum.create(op.get_bind(), checkfirst=True)

    # Create request_logs table
    op.create_table(
        "request_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("prompt_preview", sa.String(length=500), nullable=False),
        sa.Column("prompt_length", sa.Integer(), nullable=False),
        sa.Column("complexity_score", sa.Integer(), nullable=False),
        sa.Column("complexity_confidence", sa.Float(), nullable=False),
        sa.Column("detected_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("initial_model", sa.String(length=100), nullable=False),
        sa.Column(
            "initial_tier",
            sa.Enum("fast", "complex", name="modeltier"),
            nullable=False,
        ),
        sa.Column("final_model", sa.String(length=100), nullable=False),
        sa.Column("routing_reasoning", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=True),
        sa.Column("was_escalated", sa.Boolean(), nullable=True),
        sa.Column("escalation_depth", sa.Integer(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("total_latency_ms", sa.Float(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("response_preview", sa.String(length=500), nullable=True),
        sa.Column("finish_reason", sa.String(length=50), nullable=True),
        sa.Column("error_occurred", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_request_logs")),
        sa.UniqueConstraint("request_id", name=op.f("uq_request_logs_request_id")),
    )
    op.create_index("idx_request_logs_complexity", "request_logs", ["complexity_score"], unique=False)
    op.create_index("idx_request_logs_created_at", "request_logs", ["created_at"], unique=False)
    op.create_index("idx_request_logs_escalated", "request_logs", ["was_escalated"], unique=False)
    op.create_index("idx_request_logs_model", "request_logs", ["final_model"], unique=False)
    op.create_index(op.f("ix_request_logs_request_id"), "request_logs", ["request_id"], unique=False)

    # Create aggregated_metrics table
    op.create_table(
        "aggregated_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=True),
        sa.Column("fast_model_requests", sa.Integer(), nullable=True),
        sa.Column("complex_model_requests", sa.Integer(), nullable=True),
        sa.Column("escalation_count", sa.Integer(), nullable=True),
        sa.Column("escalation_rate", sa.Float(), nullable=True),
        sa.Column("avg_quality_score", sa.Float(), nullable=True),
        sa.Column("quality_below_threshold", sa.Integer(), nullable=True),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("p50_latency_ms", sa.Float(), nullable=True),
        sa.Column("p95_latency_ms", sa.Float(), nullable=True),
        sa.Column("p99_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("total_completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("cost_savings_estimate", sa.Float(), nullable=True),
        sa.Column("complexity_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aggregated_metrics")),
    )
    op.create_index("idx_agg_metrics_period", "aggregated_metrics", ["period_start", "period_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_agg_metrics_period", table_name="aggregated_metrics")
    op.drop_table("aggregated_metrics")
    op.drop_index(op.f("ix_request_logs_request_id"), table_name="request_logs")
    op.drop_index("idx_request_logs_model", table_name="request_logs")
    op.drop_index("idx_request_logs_escalated", table_name="request_logs")
    op.drop_index("idx_request_logs_created_at", table_name="request_logs")
    op.drop_index("idx_request_logs_complexity", table_name="request_logs")
    op.drop_table("request_logs")
    sa.Enum("fast", "complex", name="modeltier").drop(op.get_bind(), checkfirst=True)
