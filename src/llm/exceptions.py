"""Custom exceptions for LLM operations."""


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(self, message: str, model: str | None = None):
        self.message = message
        self.model = model
        super().__init__(self.message)


class LLMTimeoutError(LLMError):
    """Raised when an LLM request times out."""

    def __init__(self, model: str, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Request to {model} timed out after {timeout_seconds}s",
            model=model,
        )


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(self, model: str, retry_after: float | None = None):
        self.retry_after = retry_after
        msg = f"Rate limit exceeded for {model}"
        if retry_after:
            msg += f". Retry after {retry_after}s"
        super().__init__(msg, model=model)


class LLMContentFilterError(LLMError):
    """Raised when content is filtered/blocked by safety settings."""

    def __init__(self, model: str, reason: str | None = None):
        self.reason = reason
        msg = f"Content blocked by {model}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, model=model)


class LLMAuthenticationError(LLMError):
    """Raised when API authentication fails."""

    def __init__(self, message: str = "API authentication failed"):
        super().__init__(message)


class LLMModelNotFoundError(LLMError):
    """Raised when the specified model doesn't exist."""

    def __init__(self, model: str):
        super().__init__(f"Model not found: {model}", model=model)


class LLMInvalidRequestError(LLMError):
    """Raised when the request is malformed or invalid."""

    def __init__(self, message: str, model: str | None = None):
        super().__init__(f"Invalid request: {message}", model=model)
