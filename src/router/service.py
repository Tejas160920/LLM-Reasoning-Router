"""Routing engine service.

This module contains the RoutingEngine class which combines prompt
analysis with routing strategies to make model selection decisions.
"""

from src.analyzer.schemas import ComplexityAnalysis
from src.analyzer.service import PromptAnalyzer
from src.config import Settings

from .schemas import RoutingDecision
from .strategies import RoutingStrategy, ThresholdRoutingStrategy


class RoutingEngine:
    """
    Main routing engine that combines analysis and routing decisions.

    The engine:
    1. Analyzes prompt complexity using PromptAnalyzer
    2. Applies a routing strategy to select the appropriate model
    3. Returns routing decision with metadata for logging

    Example:
        settings = get_settings()
        engine = RoutingEngine(settings)

        # Analyze and route in one step
        decision = engine.route("Explain quantum entanglement step by step")
        print(decision.selected_model)  # gemini-2.0-flash-thinking-exp
        print(decision.tier)  # ModelTier.COMPLEX

        # Or get both analysis and decision
        analysis, decision = engine.route_with_analysis("What is Python?")
        print(analysis.complexity_score)  # 15
        print(decision.selected_model)  # gemini-2.0-flash
    """

    def __init__(
        self,
        settings: Settings,
        analyzer: PromptAnalyzer | None = None,
        strategy: RoutingStrategy | None = None,
    ):
        """
        Initialize the routing engine.

        Args:
            settings: Application settings with model names and thresholds
            analyzer: Optional custom PromptAnalyzer instance
            strategy: Optional custom routing strategy
        """
        self.settings = settings
        self.analyzer = analyzer or PromptAnalyzer()
        self.strategy = strategy or ThresholdRoutingStrategy(
            low_threshold=settings.complexity_threshold_low,
            high_threshold=settings.complexity_threshold_high,
        )

    def analyze(self, prompt: str) -> ComplexityAnalysis:
        """
        Analyze prompt complexity without making a routing decision.

        Useful when you need the analysis for logging or display
        but will handle routing separately.

        Args:
            prompt: The user prompt to analyze

        Returns:
            ComplexityAnalysis with score, level, and detected signals
        """
        return self.analyzer.analyze(prompt)

    def route(self, prompt: str) -> RoutingDecision:
        """
        Analyze prompt and make routing decision.

        This is the main entry point for most use cases.

        Args:
            prompt: The user prompt to route

        Returns:
            RoutingDecision with selected model and metadata
        """
        analysis = self.analyzer.analyze(prompt)
        return self.strategy.decide(
            analysis,
            self.settings.fast_model,
            self.settings.complex_model,
        )

    def route_with_analysis(
        self,
        prompt: str,
    ) -> tuple[ComplexityAnalysis, RoutingDecision]:
        """
        Return both analysis and routing decision.

        Useful when you need both pieces of information for
        logging, metrics, or display to users.

        Args:
            prompt: The user prompt to analyze and route

        Returns:
            Tuple of (ComplexityAnalysis, RoutingDecision)
        """
        analysis = self.analyzer.analyze(prompt)
        decision = self.strategy.decide(
            analysis,
            self.settings.fast_model,
            self.settings.complex_model,
        )
        return analysis, decision

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """
        Change the routing strategy at runtime.

        Args:
            strategy: New routing strategy to use
        """
        self.strategy = strategy
