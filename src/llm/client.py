"""Gemini API client wrapper.

This module provides a wrapper around the Google Gemini API for
generating chat completions with proper error handling and metrics.
"""

import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from src.config import Settings

from .exceptions import (
    LLMAuthenticationError,
    LLMContentFilterError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .schemas import ChatResponse, Message, TokenUsage


class GeminiClient:
    """
    Wrapper for Google Gemini API.

    Provides a clean interface for generating chat completions with:
    - Proper error handling and custom exceptions
    - Token usage tracking
    - Latency measurement
    - Cost calculation

    Example:
        settings = get_settings()
        client = GeminiClient(settings)

        messages = [Message(role="user", content="Hello!")]
        response = await client.generate(messages, "gemini-2.0-flash")

        print(response.content)
        print(response.usage.total_tokens)
        print(response.latency_ms)
    """

    def __init__(self, settings: Settings):
        """
        Initialize the Gemini client.

        Args:
            settings: Application settings with API key and model config
        """
        self.settings = settings

        if not settings.gemini_api_key:
            raise LLMAuthenticationError("Gemini API key not configured")

        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_instruction: str | None = None,
    ) -> ChatResponse:
        """
        Generate a response from the specified model.

        Args:
            messages: List of conversation messages
            model: Model name (e.g., "gemini-2.0-flash")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum output tokens
            system_instruction: Optional system prompt

        Returns:
            ChatResponse with content, usage, and metadata

        Raises:
            LLMTimeoutError: If the request times out
            LLMRateLimitError: If rate limit is exceeded
            LLMContentFilterError: If content is blocked
            LLMError: For other API errors
        """
        start_time = time.time()

        # Extract system instruction from messages if present
        system_msg = None
        conversation_messages: list[Message] = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                conversation_messages.append(msg)

        # Use provided system instruction or extracted one
        final_system = system_instruction or system_msg

        # Build content for Gemini
        contents = self._build_contents(conversation_messages)

        # Build generation config
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=final_system,
        )

        try:
            # Make the API call
            # Note: google-genai SDK is synchronous, so we run it directly
            # For true async, you could use asyncio.to_thread()
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response content
            content = response.text or ""

            # Extract usage metadata
            usage = self._extract_usage(response)

            # Extract finish reason
            finish_reason = self._extract_finish_reason(response)

            return ChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                created_at=datetime.now(timezone.utc),
                latency_ms=latency_ms,
            )

        except Exception as e:
            error_msg = str(e).lower()

            # Map specific errors to custom exceptions
            if "timeout" in error_msg:
                raise LLMTimeoutError(model, self.settings.llm_timeout) from e
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMRateLimitError(model) from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise LLMContentFilterError(model, str(e)) from e
            elif "api key" in error_msg or "authentication" in error_msg:
                raise LLMAuthenticationError(str(e)) from e
            else:
                raise LLMError(f"Gemini API error: {e}", model=model) from e

    def _build_contents(self, messages: list[Message]) -> list[types.Content]:
        """
        Convert messages to Gemini content format.

        Gemini uses a different format than OpenAI, so we need to convert
        the messages appropriately.
        """
        contents: list[types.Content] = []

        for msg in messages:
            # Map OpenAI roles to Gemini roles
            if msg.role == "user":
                role = "user"
            elif msg.role == "assistant":
                role = "model"
            else:
                # System messages are handled separately
                continue

            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg.content)],
                )
            )

        return contents

    def _extract_usage(self, response) -> TokenUsage:
        """Extract token usage from response."""
        try:
            usage_metadata = response.usage_metadata
            return TokenUsage(
                prompt_tokens=getattr(usage_metadata, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(usage_metadata, "candidates_token_count", 0) or 0,
                total_tokens=getattr(usage_metadata, "total_token_count", 0) or 0,
            )
        except (AttributeError, TypeError):
            # Fallback if usage not available
            return TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )

    def _extract_finish_reason(self, response) -> str:
        """Extract finish reason from response."""
        try:
            if response.candidates:
                reason = response.candidates[0].finish_reason
                if reason:
                    # Convert enum to string
                    return str(reason.name).lower()
        except (AttributeError, IndexError):
            pass
        return "stop"

    async def generate_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        system_instruction: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Generate a streaming response from the specified model.

        Yields chunks of text as they are generated, allowing for
        real-time display like ChatGPT.

        Args:
            messages: List of conversation messages
            model: Model name (e.g., "gemini-2.0-flash")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum output tokens
            system_instruction: Optional system prompt

        Yields:
            Dict with 'type' and 'content' keys:
            - {"type": "chunk", "content": "text..."} for content chunks
            - {"type": "done", "usage": {...}, "finish_reason": "stop"} when complete
        """
        # Extract system instruction from messages if present
        system_msg = None
        conversation_messages: list[Message] = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                conversation_messages.append(msg)

        final_system = system_instruction or system_msg
        contents = self._build_contents(conversation_messages)

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=final_system,
        )

        try:
            # Use streaming API
            response_stream = self.client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            )

            full_text = ""
            usage = None
            finish_reason = "stop"

            for chunk in response_stream:
                # Extract text from chunk
                if chunk.text:
                    full_text += chunk.text
                    yield {"type": "chunk", "content": chunk.text}

                # Try to get usage from final chunk
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage = {
                        "prompt_tokens": getattr(chunk.usage_metadata, "prompt_token_count", 0) or 0,
                        "completion_tokens": getattr(chunk.usage_metadata, "candidates_token_count", 0) or 0,
                        "total_tokens": getattr(chunk.usage_metadata, "total_token_count", 0) or 0,
                    }

                # Check finish reason
                if hasattr(chunk, "candidates") and chunk.candidates:
                    reason = getattr(chunk.candidates[0], "finish_reason", None)
                    if reason:
                        finish_reason = str(reason.name).lower()

            # Yield final message with usage info
            yield {
                "type": "done",
                "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "finish_reason": finish_reason,
                "full_text": full_text,
            }

        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                raise LLMTimeoutError(model, self.settings.llm_timeout) from e
            elif "rate limit" in error_msg or "quota" in error_msg:
                raise LLMRateLimitError(model) from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise LLMContentFilterError(model, str(e)) from e
            elif "api key" in error_msg or "authentication" in error_msg:
                raise LLMAuthenticationError(str(e)) from e
            else:
                raise LLMError(f"Gemini API error: {e}", model=model) from e

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate estimated cost in USD for token usage.

        Args:
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Determine pricing based on model
        if "flash" in model.lower() and "thinking" not in model.lower():
            input_rate = self.settings.cost_flash_input
            output_rate = self.settings.cost_flash_output
        else:
            # Pro/thinking models use higher rates
            input_rate = self.settings.cost_pro_input
            output_rate = self.settings.cost_pro_output

        # Calculate cost (rates are per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * input_rate
        output_cost = (completion_tokens / 1_000_000) * output_rate

        return input_cost + output_cost
