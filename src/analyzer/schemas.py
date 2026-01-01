"""Pydantic schemas for prompt complexity analysis."""

from enum import Enum

from pydantic import BaseModel, Field


class ComplexityLevel(str, Enum):
    """Complexity level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SignalType(str, Enum):
    """Types of complexity signals detected in prompts."""

    REASONING_KEYWORD = "reasoning_keyword"
    CODE_BLOCK = "code_block"
    MATH_EXPRESSION = "math_expression"
    MULTIPART_QUESTION = "multipart_question"
    LENGTH = "length"


class DetectedSignal(BaseModel):
    """A single detected complexity signal in a prompt."""

    signal_type: SignalType = Field(description="Type of signal detected")
    value: str = Field(description="The actual text/pattern that was detected")
    weight: float = Field(
        ge=0,
        le=1.0,
        description="Weight of this signal (0-1) indicating its importance",
    )
    position: int | None = Field(
        default=None,
        description="Character position in the prompt where signal was found",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "signal_type": "reasoning_keyword",
                "value": "analyze",
                "weight": 0.9,
                "position": 15,
            }
        }


class ComplexityAnalysis(BaseModel):
    """Complete complexity analysis result for a prompt."""

    complexity_score: int = Field(
        ge=0,
        le=100,
        description="Overall complexity score from 0-100",
    )
    confidence: float = Field(
        ge=0,
        le=1.0,
        description="Confidence in the analysis (0-1)",
    )
    level: ComplexityLevel = Field(
        description="Categorical complexity level (low/medium/high)",
    )
    detected_signals: list[DetectedSignal] = Field(
        default_factory=list,
        description="List of all detected complexity signals",
    )
    prompt_length: int = Field(
        ge=0,
        description="Length of the analyzed prompt in characters",
    )
    reasoning: str = Field(
        description="Human-readable explanation of the analysis",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "complexity_score": 75,
                "confidence": 0.85,
                "level": "high",
                "detected_signals": [
                    {
                        "signal_type": "reasoning_keyword",
                        "value": "analyze",
                        "weight": 0.9,
                        "position": 0,
                    },
                    {
                        "signal_type": "code_block",
                        "value": "```python...",
                        "weight": 0.7,
                        "position": 50,
                    },
                ],
                "prompt_length": 250,
                "reasoning": "Score 75/100. Contains reasoning keywords: analyze; Contains 1 code block(s); Prompt length: 250 characters",
            }
        }
