"""Pydantic schemas for escalation handling."""

from datetime import datetime

from pydantic import BaseModel, Field


class EscalationStep(BaseModel):
    """Record of a single escalation step."""

    model_used: str = Field(
        description="The model used in this step",
    )
    response_preview: str = Field(
        description="First 200 characters of the response",
    )
    quality_score: int = Field(
        ge=0,
        le=100,
        description="Quality score of this response",
    )
    escalated: bool = Field(
        description="Whether this step triggered escalation",
    )
    latency_ms: float = Field(
        ge=0,
        description="Latency of this step in milliseconds",
    )
    timestamp: datetime = Field(
        description="When this step completed",
    )


class EscalationChain(BaseModel):
    """Complete escalation chain for a request."""

    request_id: str = Field(
        description="Unique identifier for this request",
    )
    original_prompt_preview: str = Field(
        description="First 200 characters of the original prompt",
    )
    steps: list[EscalationStep] = Field(
        default_factory=list,
        description="List of all escalation steps",
    )
    final_model: str = Field(
        description="The model that produced the final response",
    )
    final_response: str = Field(
        description="The final response content",
    )
    total_attempts: int = Field(
        ge=1,
        description="Total number of generation attempts",
    )
    total_latency_ms: float = Field(
        ge=0,
        description="Total latency across all steps",
    )
    escalation_prevented_loop: bool = Field(
        default=False,
        description="Whether max depth was reached, preventing further escalation",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req-abc123",
                "original_prompt_preview": "Explain quantum...",
                "steps": [
                    {
                        "model_used": "gemini-2.0-flash",
                        "response_preview": "I'm not sure...",
                        "quality_score": 45,
                        "escalated": True,
                        "latency_ms": 450,
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                ],
                "final_model": "gemini-2.0-flash-thinking-exp",
                "final_response": "Quantum entanglement is...",
                "total_attempts": 2,
                "total_latency_ms": 1200,
                "escalation_prevented_loop": False,
            }
        }


class CombinedResponse(BaseModel):
    """Response that optionally combines multiple model outputs."""

    primary_response: str = Field(
        description="The main response content",
    )
    supporting_context: str | None = Field(
        default=None,
        description="Additional context from earlier attempts",
    )
    models_used: list[str] = Field(
        description="List of models that contributed to this response",
    )
    combination_strategy: str = Field(
        description="Strategy used to combine responses",
    )
