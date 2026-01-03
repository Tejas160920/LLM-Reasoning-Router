"""Pydantic schemas for routing decisions."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    """Model tier classification."""

    FAST = "fast"  # Fast/cheap model (e.g., gemini-2.0-flash)
    COMPLEX = "complex"  # Complex/reasoning model (e.g., gemini-2.0-flash-thinking-exp)


class RoutingDecision(BaseModel):
    """Result of a routing decision."""

    selected_model: str = Field(
        description="The actual model name to use",
    )
    tier: ModelTier = Field(
        description="Model tier classification",
    )
    complexity_score: int = Field(
        ge=0,
        le=100,
        description="Complexity score that led to this decision",
    )
    confidence: float = Field(
        ge=0,
        le=1.0,
        description="Confidence in the routing decision",
    )
    reasoning: str = Field(
        description="Human-readable explanation of the routing decision",
    )
    requires_quality_check: bool = Field(
        description="Whether the response should be quality-checked for potential escalation",
    )
    timestamp: datetime = Field(
        description="When the routing decision was made",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "selected_model": "gemini-2.0-flash",
                "tier": "fast",
                "complexity_score": 25,
                "confidence": 0.85,
                "reasoning": "Low complexity (25) below threshold (30)",
                "requires_quality_check": False,
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }
