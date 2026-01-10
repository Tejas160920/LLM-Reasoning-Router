"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.analyzer.service import PromptAnalyzer
from src.config import Settings
from src.llm.schemas import ChatResponse, TokenUsage
from src.quality.service import QualityChecker
from src.router.service import RoutingEngine


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_llm_router",
        gemini_api_key="test-api-key",
        fast_model="gemini-2.0-flash",
        complex_model="gemini-2.0-flash-thinking-exp",
        complexity_threshold_low=30,
        complexity_threshold_high=70,
        quality_threshold=60,
        debug=True,
    )


@pytest.fixture
def prompt_analyzer():
    """Create a PromptAnalyzer instance."""
    return PromptAnalyzer()


@pytest.fixture
def routing_engine(test_settings, prompt_analyzer):
    """Create a RoutingEngine instance."""
    return RoutingEngine(settings=test_settings, analyzer=prompt_analyzer)


@pytest.fixture
def quality_checker(test_settings):
    """Create a QualityChecker instance."""
    return QualityChecker(test_settings)


@pytest.fixture
def mock_chat_response():
    """Create a mock ChatResponse."""
    from datetime import datetime, timezone

    return ChatResponse(
        id="test-response-123",
        content="This is a test response with clear and confident information.",
        model="gemini-2.0-flash",
        usage=TokenUsage(
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
        ),
        finish_reason="stop",
        created_at=datetime.now(timezone.utc),
        latency_ms=250.5,
    )


@pytest.fixture
def mock_uncertain_response():
    """Create a mock response with uncertainty phrases."""
    from datetime import datetime, timezone

    return ChatResponse(
        id="test-uncertain-123",
        content="I'm not sure, but I think it might be something like this. Possibly the answer could be 42.",
        model="gemini-2.0-flash",
        usage=TokenUsage(
            prompt_tokens=50,
            completion_tokens=80,
            total_tokens=130,
        ),
        finish_reason="stop",
        created_at=datetime.now(timezone.utc),
        latency_ms=200.0,
    )


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session
