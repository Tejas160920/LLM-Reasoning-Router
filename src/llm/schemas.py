"""Pydantic schemas for LLM requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in a conversation (OpenAI-compatible format)."""

    role: Literal["system", "user", "assistant"] = Field(
        description="The role of the message author",
    )
    content: str = Field(
        description="The content of the message",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What is the capital of France?",
            }
        }


class TokenUsage(BaseModel):
    """Token usage information from LLM response."""

    prompt_tokens: int = Field(
        ge=0,
        description="Number of tokens in the prompt",
    )
    completion_tokens: int = Field(
        ge=0,
        description="Number of tokens in the completion",
    )
    total_tokens: int = Field(
        ge=0,
        description="Total tokens used (prompt + completion)",
    )


class ChatRequest(BaseModel):
    """Request to the LLM client."""

    messages: list[Message] = Field(
        description="List of messages in the conversation",
    )
    model: str | None = Field(
        default=None,
        description="Model to use (if None, router decides)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate",
    )
    system_instruction: str | None = Field(
        default=None,
        description="Optional system instruction to prepend",
    )


class ChatResponse(BaseModel):
    """Response from the LLM."""

    id: str = Field(
        description="Unique identifier for this response",
    )
    content: str = Field(
        description="The generated text content",
    )
    model: str = Field(
        description="The model that generated this response",
    )
    usage: TokenUsage = Field(
        description="Token usage information",
    )
    finish_reason: str = Field(
        description="Reason the generation stopped",
    )
    created_at: datetime = Field(
        description="When the response was generated",
    )
    latency_ms: float = Field(
        ge=0,
        description="Response latency in milliseconds",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chatcmpl-abc123",
                "content": "The capital of France is Paris.",
                "model": "gemini-2.0-flash",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18,
                },
                "finish_reason": "stop",
                "created_at": "2024-01-15T10:30:00Z",
                "latency_ms": 450.5,
            }
        }
