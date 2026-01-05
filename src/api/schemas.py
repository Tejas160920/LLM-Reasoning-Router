"""OpenAI-compatible API schemas.

These schemas provide compatibility with the OpenAI chat completions API,
making it easy to use this router as a drop-in replacement.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"] = Field(
        description="The role of the message author"
    )
    content: str = Field(description="The content of the message")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str | None = Field(
        default=None,
        description="Model to use. If None, router decides automatically",
    )
    messages: list[ChatMessage] = Field(
        description="List of messages in the conversation"
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        description="Sampling temperature",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response (not yet supported)",
    )

    # Router-specific options
    force_model: str | None = Field(
        default=None,
        description="Force a specific model, bypassing routing logic",
    )
    skip_quality_check: bool = Field(
        default=False,
        description="Skip quality checking and potential escalation",
    )
    include_analysis: bool = Field(
        default=False,
        description="Include routing analysis details in response",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "Explain quantum entanglement step by step"}
                ],
                "temperature": 0.7,
                "include_analysis": True,
            }
        }


class ChatChoice(BaseModel):
    """A single completion choice."""

    index: int = Field(description="Index of this choice")
    message: ChatMessage = Field(description="The generated message")
    finish_reason: str = Field(description="Reason the generation stopped")


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(description="Tokens in the prompt")
    completion_tokens: int = Field(description="Tokens in the completion")
    total_tokens: int = Field(description="Total tokens used")


class RoutingInfo(BaseModel):
    """Routing decision details (optional in response)."""

    complexity_score: int = Field(description="Prompt complexity score (0-100)")
    complexity_level: str = Field(description="Complexity level (low/medium/high)")
    initial_model: str = Field(description="Initially selected model")
    final_model: str = Field(description="Final model used (after any escalation)")
    was_escalated: bool = Field(description="Whether escalation occurred")
    quality_score: int | None = Field(description="Response quality score")
    routing_reasoning: str = Field(description="Explanation of routing decision")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str = Field(description="Unique identifier for this completion")
    object: str = Field(default="chat.completion")
    created: int = Field(description="Unix timestamp of creation")
    model: str = Field(description="Model that generated the response")
    choices: list[ChatChoice] = Field(description="List of completion choices")
    usage: Usage = Field(description="Token usage information")

    # Router-specific (optional)
    routing_info: RoutingInfo | None = Field(
        default=None,
        description="Routing details (included if include_analysis=True)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-abc123",
                "object": "chat.completion",
                "created": 1705312200,
                "model": "gemini-2.0-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Quantum entanglement is...",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 150,
                    "total_tokens": 165,
                },
                "routing_info": {
                    "complexity_score": 72,
                    "complexity_level": "high",
                    "initial_model": "gemini-2.0-flash-thinking-exp",
                    "final_model": "gemini-2.0-flash-thinking-exp",
                    "was_escalated": False,
                    "quality_score": 85,
                    "routing_reasoning": "High complexity (72) exceeds threshold (70)",
                },
            }
        }


class ErrorDetail(BaseModel):
    """Error detail information."""

    message: str = Field(description="Error message")
    type: str = Field(description="Error type")
    code: str | None = Field(default=None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response format."""

    error: ErrorDetail = Field(description="Error details")
