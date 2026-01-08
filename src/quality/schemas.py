"""Pydantic schemas for response quality assessment."""

from enum import Enum

from pydantic import BaseModel, Field


class QualityIssueType(str, Enum):
    """Types of quality issues that can be detected in responses."""

    UNCERTAINTY = "uncertainty"
    INCOMPLETE = "incomplete"
    FAILED_REASONING = "failed_reasoning"
    TOO_SHORT = "too_short"
    REPETITION = "repetition"
    REFUSAL = "refusal"


class QualityIssue(BaseModel):
    """A detected quality issue in an LLM response."""

    issue_type: QualityIssueType = Field(
        description="Type of quality issue detected",
    )
    description: str = Field(
        description="Human-readable description of the issue",
    )
    severity: float = Field(
        ge=0,
        le=1.0,
        description="Severity of the issue (0=minor, 1=severe)",
    )
    evidence: str | None = Field(
        default=None,
        description="Text snippet showing the issue",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "issue_type": "uncertainty",
                "description": "Response contains uncertainty phrases",
                "severity": 0.6,
                "evidence": "I'm not sure",
            }
        }


class QualityAssessment(BaseModel):
    """Complete quality assessment of an LLM response."""

    quality_score: int = Field(
        ge=0,
        le=100,
        description="Overall quality score (0-100)",
    )
    issues: list[QualityIssue] = Field(
        default_factory=list,
        description="List of detected quality issues",
    )
    should_escalate: bool = Field(
        description="Whether the request should be escalated to a better model",
    )
    escalation_reason: str | None = Field(
        default=None,
        description="Reason for escalation recommendation",
    )
    confidence: float = Field(
        ge=0,
        le=1.0,
        description="Confidence in the quality assessment",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "quality_score": 45,
                "issues": [
                    {
                        "issue_type": "uncertainty",
                        "description": "Found 2 uncertainty phrase(s)",
                        "severity": 0.4,
                        "evidence": "might be",
                    }
                ],
                "should_escalate": True,
                "escalation_reason": "Quality score 45 below threshold. Main issue: Found 2 uncertainty phrase(s)",
                "confidence": 0.75,
            }
        }
