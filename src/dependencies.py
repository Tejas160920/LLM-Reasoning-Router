"""FastAPI dependency injection setup.

This module provides dependency functions that create and inject
service instances into API endpoints.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.analyzer.service import PromptAnalyzer
from src.config import Settings, get_settings
from src.db.session import get_db_session
from src.escalation.service import EscalationHandler
from src.llm.client import GeminiClient
from src.metrics.service import MetricsService
from src.quality.service import QualityChecker
from src.router.service import RoutingEngine


@lru_cache()
def get_prompt_analyzer() -> PromptAnalyzer:
    """Get cached PromptAnalyzer singleton."""
    return PromptAnalyzer()


@lru_cache()
def get_llm_client() -> GeminiClient:
    """Get cached GeminiClient singleton."""
    settings = get_settings()
    return GeminiClient(settings)


def get_routing_engine(
    settings: Annotated[Settings, Depends(get_settings)],
    analyzer: Annotated[PromptAnalyzer, Depends(get_prompt_analyzer)],
) -> RoutingEngine:
    """Get RoutingEngine instance."""
    return RoutingEngine(settings=settings, analyzer=analyzer)


def get_quality_checker(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QualityChecker:
    """Get QualityChecker instance."""
    return QualityChecker(settings)


def get_escalation_handler(
    settings: Annotated[Settings, Depends(get_settings)],
    llm_client: Annotated[GeminiClient, Depends(get_llm_client)],
    quality_checker: Annotated[QualityChecker, Depends(get_quality_checker)],
) -> EscalationHandler:
    """Get EscalationHandler instance."""
    return EscalationHandler(
        settings=settings,
        llm_client=llm_client,
        quality_checker=quality_checker,
    )


def get_metrics_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MetricsService:
    """Get MetricsService with database session."""
    return MetricsService(db)


# Type aliases for cleaner endpoint signatures
SettingsDep = Annotated[Settings, Depends(get_settings)]
LLMClientDep = Annotated[GeminiClient, Depends(get_llm_client)]
RoutingEngineDep = Annotated[RoutingEngine, Depends(get_routing_engine)]
QualityCheckerDep = Annotated[QualityChecker, Depends(get_quality_checker)]
EscalationHandlerDep = Annotated[EscalationHandler, Depends(get_escalation_handler)]
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
