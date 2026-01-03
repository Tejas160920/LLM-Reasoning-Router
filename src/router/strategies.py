"""Routing strategies for model selection.

This module contains different strategies for deciding which model
to use based on prompt complexity analysis.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from src.analyzer.schemas import ComplexityAnalysis

from .schemas import ModelTier, RoutingDecision


class RoutingStrategy(ABC):
    """Base class for routing strategies."""

    @abstractmethod
    def decide(
        self,
        analysis: ComplexityAnalysis,
        fast_model: str,
        complex_model: str,
    ) -> RoutingDecision:
        """
        Make routing decision based on complexity analysis.

        Args:
            analysis: The complexity analysis result
            fast_model: Name of the fast/cheap model
            complex_model: Name of the complex/reasoning model

        Returns:
            RoutingDecision with selected model and metadata
        """
        pass


class ThresholdRoutingStrategy(RoutingStrategy):
    """
    Simple threshold-based routing strategy.

    Routes based on complexity score thresholds:
    - Score < low_threshold: fast model, no quality check
    - Score >= high_threshold: complex model, no quality check
    - Between thresholds: fast model with quality check (may escalate)

    This is the recommended default strategy as it provides good
    cost optimization while maintaining quality through escalation.
    """

    def __init__(
        self,
        low_threshold: int = 30,
        high_threshold: int = 70,
    ):
        """
        Initialize threshold-based routing.

        Args:
            low_threshold: Below this score, use fast model without quality check
            high_threshold: Above this score, use complex model directly
        """
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold

    def decide(
        self,
        analysis: ComplexityAnalysis,
        fast_model: str,
        complex_model: str,
    ) -> RoutingDecision:
        """Make routing decision based on thresholds."""
        score = analysis.complexity_score
        now = datetime.now(timezone.utc)

        if score >= self.high_threshold:
            # High complexity -> use complex model directly
            return RoutingDecision(
                selected_model=complex_model,
                tier=ModelTier.COMPLEX,
                complexity_score=score,
                confidence=analysis.confidence,
                reasoning=(
                    f"High complexity ({score}) exceeds threshold ({self.high_threshold})"
                ),
                requires_quality_check=False,
                timestamp=now,
            )
        elif score < self.low_threshold:
            # Low complexity -> use fast model, no quality check needed
            return RoutingDecision(
                selected_model=fast_model,
                tier=ModelTier.FAST,
                complexity_score=score,
                confidence=analysis.confidence,
                reasoning=(
                    f"Low complexity ({score}) below threshold ({self.low_threshold})"
                ),
                requires_quality_check=False,
                timestamp=now,
            )
        else:
            # Medium complexity -> use fast model with quality check
            return RoutingDecision(
                selected_model=fast_model,
                tier=ModelTier.FAST,
                complexity_score=score,
                confidence=analysis.confidence,
                reasoning=(
                    f"Medium complexity ({score}) - using fast model with quality check"
                ),
                requires_quality_check=True,
                timestamp=now,
            )


class ConfidenceAwareRoutingStrategy(RoutingStrategy):
    """
    Routes based on both complexity score and analysis confidence.

    When confidence in the complexity assessment is low and the score
    is in the borderline range, this strategy defaults to the complex
    model to be safe.

    This is useful when you want to minimize the risk of under-routing
    complex requests that might have been misclassified.
    """

    def __init__(
        self,
        low_threshold: int = 30,
        high_threshold: int = 70,
        confidence_threshold: float = 0.6,
    ):
        """
        Initialize confidence-aware routing.

        Args:
            low_threshold: Below this score, use fast model
            high_threshold: Above this score, use complex model
            confidence_threshold: Below this confidence with borderline score,
                                  default to complex model
        """
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.confidence_threshold = confidence_threshold
        self.fallback = ThresholdRoutingStrategy(low_threshold, high_threshold)

    def decide(
        self,
        analysis: ComplexityAnalysis,
        fast_model: str,
        complex_model: str,
    ) -> RoutingDecision:
        """Make routing decision considering confidence."""
        # If confidence is low and score is borderline, be conservative
        if (
            analysis.confidence < self.confidence_threshold
            and self.low_threshold <= analysis.complexity_score < self.high_threshold
        ):
            return RoutingDecision(
                selected_model=complex_model,
                tier=ModelTier.COMPLEX,
                complexity_score=analysis.complexity_score,
                confidence=analysis.confidence,
                reasoning=(
                    f"Low confidence ({analysis.confidence:.2f}) with borderline "
                    f"score ({analysis.complexity_score}) - defaulting to complex model"
                ),
                requires_quality_check=False,
                timestamp=datetime.now(timezone.utc),
            )

        # Otherwise, use standard threshold routing
        return self.fallback.decide(analysis, fast_model, complex_model)


class AlwaysFastStrategy(RoutingStrategy):
    """
    Always routes to the fast model.

    Useful for testing, development, or when cost is the primary concern.
    Quality checking can still catch issues and escalate if needed.
    """

    def decide(
        self,
        analysis: ComplexityAnalysis,
        fast_model: str,
        complex_model: str,
    ) -> RoutingDecision:
        """Always select fast model."""
        return RoutingDecision(
            selected_model=fast_model,
            tier=ModelTier.FAST,
            complexity_score=analysis.complexity_score,
            confidence=analysis.confidence,
            reasoning="Strategy: always use fast model (with quality check)",
            requires_quality_check=True,  # Always check quality
            timestamp=datetime.now(timezone.utc),
        )


class AlwaysComplexStrategy(RoutingStrategy):
    """
    Always routes to the complex model.

    Useful when quality is the top priority and cost is not a concern.
    """

    def decide(
        self,
        analysis: ComplexityAnalysis,
        fast_model: str,
        complex_model: str,
    ) -> RoutingDecision:
        """Always select complex model."""
        return RoutingDecision(
            selected_model=complex_model,
            tier=ModelTier.COMPLEX,
            complexity_score=analysis.complexity_score,
            confidence=analysis.confidence,
            reasoning="Strategy: always use complex model",
            requires_quality_check=False,
            timestamp=datetime.now(timezone.utc),
        )
