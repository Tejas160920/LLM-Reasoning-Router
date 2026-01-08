"""Database operations for metrics."""

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ModelTier, RequestLog
from .schemas import ComplexityDistribution, DashboardMetrics


class MetricsRepository:
    """Database operations for metrics storage and retrieval."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def create_request_log(self, log: RequestLog) -> RequestLog:
        """
        Insert a new request log.

        Args:
            log: RequestLog instance to insert

        Returns:
            The inserted RequestLog with generated ID
        """
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_request_by_id(self, request_id: str) -> RequestLog | None:
        """
        Get a specific request log by ID.

        Args:
            request_id: The unique request identifier

        Returns:
            RequestLog if found, None otherwise
        """
        result = await self.session.execute(
            select(RequestLog).where(RequestLog.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_dashboard_metrics(self, since: datetime) -> DashboardMetrics:
        """
        Compute dashboard metrics for a time period.

        Args:
            since: Start of the time period

        Returns:
            DashboardMetrics with aggregated data
        """
        base_filter = RequestLog.created_at >= since

        # Total requests
        total_result = await self.session.execute(
            select(func.count(RequestLog.id)).where(base_filter)
        )
        total_requests = total_result.scalar() or 0

        if total_requests == 0:
            # Return empty metrics if no data
            return DashboardMetrics(
                period=f"since_{since.isoformat()}",
                total_requests=0,
                requests_by_model={},
                escalation_count=0,
                escalation_rate=0.0,
                avg_complexity_score=0.0,
                complexity_distribution=ComplexityDistribution(),
                avg_quality_score=0.0,
                quality_issues_count=0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                total_cost=0.0,
                cost_savings=0.0,
                total_tokens=0,
                tokens_by_model={},
            )

        # Requests by model
        model_result = await self.session.execute(
            select(RequestLog.final_model, func.count(RequestLog.id))
            .where(base_filter)
            .group_by(RequestLog.final_model)
        )
        requests_by_model = dict(model_result.all())

        # Escalation rate
        escalated_result = await self.session.execute(
            select(func.count(RequestLog.id)).where(
                and_(base_filter, RequestLog.was_escalated == True)  # noqa: E712
            )
        )
        escalated_count = escalated_result.scalar() or 0
        escalation_rate = (escalated_count / total_requests * 100) if total_requests > 0 else 0

        # Average complexity
        complexity_result = await self.session.execute(
            select(func.avg(RequestLog.complexity_score)).where(base_filter)
        )
        avg_complexity = complexity_result.scalar() or 0

        # Complexity distribution
        low_count = await self._count_complexity_range(since, 0, 30)
        med_count = await self._count_complexity_range(since, 30, 70)
        high_count = await self._count_complexity_range(since, 70, 101)

        # Quality metrics
        quality_result = await self.session.execute(
            select(func.avg(RequestLog.quality_score)).where(
                and_(base_filter, RequestLog.quality_score.isnot(None))
            )
        )
        avg_quality = quality_result.scalar() or 0

        # Quality issues count (below threshold, assuming 60)
        quality_issues_result = await self.session.execute(
            select(func.count(RequestLog.id)).where(
                and_(
                    base_filter,
                    RequestLog.quality_score.isnot(None),
                    RequestLog.quality_score < 60,
                )
            )
        )
        quality_issues_count = quality_issues_result.scalar() or 0

        # Latency metrics
        avg_latency_result = await self.session.execute(
            select(func.avg(RequestLog.total_latency_ms)).where(base_filter)
        )
        avg_latency = avg_latency_result.scalar() or 0

        # P95 latency (using percentile_cont if available, otherwise approximate)
        try:
            p95_result = await self.session.execute(
                select(
                    func.percentile_cont(0.95).within_group(RequestLog.total_latency_ms)
                ).where(base_filter)
            )
            p95_latency = p95_result.scalar() or 0
        except Exception:
            # Fallback if percentile_cont not available
            p95_latency = avg_latency * 1.5 if avg_latency else 0

        # Cost and tokens
        cost_result = await self.session.execute(
            select(
                func.sum(RequestLog.estimated_cost),
                func.sum(RequestLog.total_tokens),
            ).where(base_filter)
        )
        cost_row = cost_result.one_or_none()
        total_cost = cost_row[0] if cost_row and cost_row[0] else 0
        total_tokens = cost_row[1] if cost_row and cost_row[1] else 0

        # Tokens by model
        tokens_by_model_result = await self.session.execute(
            select(RequestLog.final_model, func.sum(RequestLog.total_tokens))
            .where(base_filter)
            .group_by(RequestLog.final_model)
        )
        tokens_by_model = {
            model: int(tokens) for model, tokens in tokens_by_model_result.all() if tokens
        }

        # Cost savings estimate (difference between actual cost and if all used pro model)
        # Simplified: assume pro model costs ~10x more than flash
        fast_requests = requests_by_model.get("gemini-2.0-flash", 0)
        cost_savings = float(total_cost) * 0.9 * (fast_requests / total_requests) if total_requests > 0 else 0

        return DashboardMetrics(
            period=f"since_{since.isoformat()}",
            total_requests=total_requests,
            requests_by_model=requests_by_model,
            escalation_count=escalated_count,
            escalation_rate=float(escalation_rate),
            avg_complexity_score=float(avg_complexity),
            complexity_distribution=ComplexityDistribution(
                low=low_count,
                medium=med_count,
                high=high_count,
            ),
            avg_quality_score=float(avg_quality),
            quality_issues_count=quality_issues_count,
            avg_latency_ms=float(avg_latency),
            p95_latency_ms=float(p95_latency),
            total_cost=float(total_cost),
            cost_savings=float(cost_savings),
            total_tokens=int(total_tokens),
            tokens_by_model=tokens_by_model,
        )

    async def _count_complexity_range(
        self,
        since: datetime,
        min_score: int,
        max_score: int,
    ) -> int:
        """Count requests within a complexity score range."""
        result = await self.session.execute(
            select(func.count(RequestLog.id)).where(
                and_(
                    RequestLog.created_at >= since,
                    RequestLog.complexity_score >= min_score,
                    RequestLog.complexity_score < max_score,
                )
            )
        )
        return result.scalar() or 0

    async def get_recent_requests(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RequestLog]:
        """
        Get recent request logs.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of RequestLog objects
        """
        result = await self.session.execute(
            select(RequestLog)
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
