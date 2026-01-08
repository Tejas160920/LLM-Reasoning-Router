"""Metrics service for tracking and querying request data."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.analyzer.schemas import ComplexityAnalysis
from src.escalation.schemas import EscalationChain
from src.llm.schemas import ChatResponse
from src.quality.schemas import QualityAssessment
from src.router.schemas import RoutingDecision

from .models import ModelTier, RequestLog
from .repository import MetricsRepository
from .schemas import DashboardMetrics, RequestMetrics


class MetricsService:
    """
    Service for tracking and querying metrics.

    Provides methods to:
    1. Log individual requests with all metadata
    2. Query aggregated metrics for dashboards
    3. Calculate cost savings and efficiency metrics

    Example:
        async with get_db_session() as session:
            service = MetricsService(session)

            # Log a request
            await service.log_request(
                prompt="What is Python?",
                analysis=analysis,
                routing=routing_decision,
                response=llm_response,
            )

            # Get dashboard metrics
            metrics = await service.get_metrics("last_hour")
            print(f"Total requests: {metrics.total_requests}")
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the metrics service.

        Args:
            session: Async SQLAlchemy session
        """
        self.repository = MetricsRepository(session)

    async def log_request(
        self,
        prompt: str,
        analysis: ComplexityAnalysis,
        routing: RoutingDecision,
        response: ChatResponse,
        quality: QualityAssessment | None = None,
        escalation: EscalationChain | None = None,
        error: Exception | None = None,
    ) -> RequestLog:
        """
        Log a complete request with all associated data.

        This should be called at the end of each request processing
        to record all metrics for later analysis.

        Args:
            prompt: The original user prompt
            analysis: Complexity analysis result
            routing: Routing decision made
            response: Final LLM response
            quality: Quality assessment (if performed)
            escalation: Escalation chain (if escalation occurred)
            error: Any error that occurred

        Returns:
            The created RequestLog record
        """
        request_id = f"req-{uuid.uuid4().hex[:12]}"

        # Determine escalation info
        was_escalated = escalation is not None and escalation.total_attempts > 1
        escalation_depth = escalation.total_attempts - 1 if escalation else 0
        final_model = escalation.final_model if escalation else routing.selected_model
        total_latency = escalation.total_latency_ms if escalation else response.latency_ms

        # Determine initial tier
        if "flash" in routing.selected_model.lower() and "thinking" not in routing.selected_model.lower():
            initial_tier = ModelTier.FAST
        else:
            initial_tier = ModelTier.COMPLEX

        log = RequestLog(
            request_id=request_id,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            # Prompt info
            prompt_preview=prompt[:500],
            prompt_length=len(prompt),
            # Complexity
            complexity_score=analysis.complexity_score,
            complexity_confidence=analysis.confidence,
            detected_signals=[s.signal_type.value for s in analysis.detected_signals],
            # Routing
            initial_model=routing.selected_model,
            initial_tier=initial_tier,
            final_model=final_model,
            routing_reasoning=routing.reasoning,
            # Quality
            quality_score=quality.quality_score if quality else None,
            was_escalated=was_escalated,
            escalation_depth=escalation_depth,
            escalation_reason=quality.escalation_reason if quality and quality.should_escalate else None,
            # Performance
            latency_ms=response.latency_ms,
            total_latency_ms=total_latency,
            # Tokens
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            # Cost
            estimated_cost=self._calculate_cost(response, final_model),
            # Response
            response_preview=response.content[:500] if response.content else None,
            finish_reason=response.finish_reason,
            # Errors
            error_occurred=error is not None,
            error_message=str(error) if error else None,
        )

        return await self.repository.create_request_log(log)

    async def get_metrics(
        self,
        period: str = "last_hour",
    ) -> DashboardMetrics:
        """
        Get aggregated metrics for the dashboard.

        Args:
            period: Time period - "last_hour", "last_day", or "last_week"

        Returns:
            DashboardMetrics with aggregated data
        """
        now = datetime.now(timezone.utc)

        period_map = {
            "last_hour": timedelta(hours=1),
            "last_day": timedelta(days=1),
            "last_week": timedelta(weeks=1),
        }

        delta = period_map.get(period, timedelta(hours=1))
        since = now - delta

        return await self.repository.get_dashboard_metrics(since)

    async def get_request_metrics(self, request_id: str) -> RequestMetrics | None:
        """
        Get metrics for a specific request.

        Args:
            request_id: The unique request identifier

        Returns:
            RequestMetrics if found, None otherwise
        """
        log = await self.repository.get_request_by_id(request_id)
        if not log:
            return None

        return RequestMetrics(
            request_id=log.request_id,
            complexity_score=log.complexity_score,
            initial_model=log.initial_model,
            final_model=log.final_model,
            was_escalated=log.was_escalated,
            quality_score=log.quality_score,
            latency_ms=log.total_latency_ms,
            tokens_used=log.total_tokens,
            estimated_cost=log.estimated_cost,
        )

    def _calculate_cost(self, response: ChatResponse, model: str) -> float:
        """
        Calculate estimated cost in USD.

        Args:
            response: The LLM response with token usage
            model: Model name used

        Returns:
            Estimated cost in USD
        """
        # Pricing per 1M tokens (approximate)
        # Flash models are cheaper, Pro models are more expensive
        is_flash = "flash" in model.lower() and "pro" not in model.lower()
        if is_flash:
            input_rate = 0.075  # $0.075 per 1M input tokens
            output_rate = 0.30  # $0.30 per 1M output tokens
        else:
            input_rate = 1.25  # $1.25 per 1M input tokens
            output_rate = 5.00  # $5.00 per 1M output tokens

        input_cost = (response.usage.prompt_tokens / 1_000_000) * input_rate
        output_cost = (response.usage.completion_tokens / 1_000_000) * output_rate

        return input_cost + output_cost
