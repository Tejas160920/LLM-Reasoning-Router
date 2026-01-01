"""Prompt complexity analyzer service.

This module contains the PromptAnalyzer class which is responsible for
analyzing user prompts and determining their complexity level for
intelligent model routing.
"""

from .constants import SIGNAL_WEIGHTS
from .schemas import ComplexityAnalysis, ComplexityLevel, DetectedSignal
from .signals import (
    calculate_length_signal,
    deduplicate_signals,
    detect_code_blocks,
    detect_math_expressions,
    detect_multipart_questions,
    detect_reasoning_keywords,
)


class PromptAnalyzer:
    """
    Analyzes prompt complexity to determine appropriate model routing.

    The analyzer examines multiple signals in a prompt:
    1. Reasoning keywords (analyze, compare, debug, step-by-step, etc.)
    2. Code blocks and programming content
    3. Mathematical expressions and notation
    4. Multi-part questions and compound requests
    5. Overall length and structure

    Each signal contributes to a weighted complexity score (0-100).

    Example:
        analyzer = PromptAnalyzer()
        result = analyzer.analyze("Explain step by step how to debug this code")
        print(result.complexity_score)  # e.g., 65
        print(result.level)  # ComplexityLevel.MEDIUM
    """

    def __init__(
        self,
        keyword_weight: float = SIGNAL_WEIGHTS["keyword"],
        code_weight: float = SIGNAL_WEIGHTS["code"],
        math_weight: float = SIGNAL_WEIGHTS["math"],
        multipart_weight: float = SIGNAL_WEIGHTS["multipart"],
        length_weight: float = SIGNAL_WEIGHTS["length"],
    ):
        """
        Initialize the analyzer with configurable weights.

        Args:
            keyword_weight: Weight for reasoning keyword signals (default: 0.35)
            code_weight: Weight for code block signals (default: 0.25)
            math_weight: Weight for math expression signals (default: 0.20)
            multipart_weight: Weight for multi-part question signals (default: 0.10)
            length_weight: Weight for length-based signals (default: 0.10)
        """
        self.weights = {
            "keyword": keyword_weight,
            "code": code_weight,
            "math": math_weight,
            "multipart": multipart_weight,
            "length": length_weight,
        }

    def analyze(self, prompt: str) -> ComplexityAnalysis:
        """
        Analyze a prompt and return complexity assessment.

        Args:
            prompt: The user prompt to analyze

        Returns:
            ComplexityAnalysis with score, confidence, level, and detected signals
        """
        # Handle empty prompts
        if not prompt or not prompt.strip():
            return ComplexityAnalysis(
                complexity_score=0,
                confidence=1.0,
                level=ComplexityLevel.LOW,
                detected_signals=[],
                prompt_length=0,
                reasoning="Empty prompt",
            )

        # Collect all signals
        all_signals: list[DetectedSignal] = []

        keyword_signals = detect_reasoning_keywords(prompt)
        code_signals = detect_code_blocks(prompt)
        math_signals = detect_math_expressions(prompt)
        multipart_signals = detect_multipart_questions(prompt)
        length_signal = calculate_length_signal(prompt)

        # Deduplicate signals within each category
        keyword_signals = deduplicate_signals(keyword_signals)
        code_signals = deduplicate_signals(code_signals)
        math_signals = deduplicate_signals(math_signals)
        multipart_signals = deduplicate_signals(multipart_signals)

        # Combine all signals
        all_signals.extend(keyword_signals)
        all_signals.extend(code_signals)
        all_signals.extend(math_signals)
        all_signals.extend(multipart_signals)
        all_signals.append(length_signal)

        # Calculate weighted complexity score
        score = self._calculate_score(
            keyword_signals,
            code_signals,
            math_signals,
            multipart_signals,
            length_signal,
        )

        # Determine confidence based on signal clarity
        confidence = self._calculate_confidence(all_signals, score)

        # Map score to complexity level
        level = self._score_to_level(score)

        # Generate human-readable reasoning
        reasoning = self._generate_reasoning(
            keyword_signals,
            code_signals,
            math_signals,
            multipart_signals,
            length_signal,
            score,
        )

        return ComplexityAnalysis(
            complexity_score=score,
            confidence=confidence,
            level=level,
            detected_signals=all_signals,
            prompt_length=len(prompt),
            reasoning=reasoning,
        )

    def _calculate_score(
        self,
        keyword_signals: list[DetectedSignal],
        code_signals: list[DetectedSignal],
        math_signals: list[DetectedSignal],
        multipart_signals: list[DetectedSignal],
        length_signal: DetectedSignal,
    ) -> int:
        """
        Calculate weighted complexity score (0-100).

        Uses diminishing returns for multiple signals of the same type
        to prevent score inflation from repetitive patterns.
        """

        def aggregate_signals(signals: list[DetectedSignal]) -> float:
            """Aggregate multiple signals with diminishing returns."""
            if not signals:
                return 0.0

            # Sort by weight, highest first
            weights = sorted([s.weight for s in signals], reverse=True)

            # Apply diminishing returns: first signal full weight, others decay
            total = 0.0
            for i, w in enumerate(weights[:5]):  # Cap at 5 signals per category
                decay = 0.7**i  # Each subsequent signal worth 70% of previous
                total += w * decay

            return min(1.0, total)

        # Calculate score for each signal category
        keyword_score = aggregate_signals(keyword_signals) * self.weights["keyword"]
        code_score = aggregate_signals(code_signals) * self.weights["code"]
        math_score = aggregate_signals(math_signals) * self.weights["math"]
        multipart_score = aggregate_signals(multipart_signals) * self.weights["multipart"]
        length_score = length_signal.weight * self.weights["length"]

        # Sum all weighted scores
        total = keyword_score + code_score + math_score + multipart_score + length_score

        # Scale to 0-100 range
        return int(min(100, total * 100))

    def _calculate_confidence(
        self,
        signals: list[DetectedSignal],
        score: int,
    ) -> float:
        """
        Calculate confidence in the complexity assessment.

        Higher confidence when:
        - Multiple strong signals in the same direction
        - Score is clearly high or low (not borderline)
        """
        if not signals:
            return 0.5  # No signals = uncertain

        # Average signal weight
        avg_weight = sum(s.weight for s in signals) / len(signals)

        # More signals = higher confidence (up to a point)
        signal_count = len(signals)
        count_factor = min(1.0, signal_count / 5)

        # Score extremity: 0 or 100 = confident, 50 = uncertain
        extremity = abs(score - 50) / 50

        # Combine factors
        confidence = avg_weight * 0.4 + count_factor * 0.3 + extremity * 0.3

        return round(confidence, 2)

    def _score_to_level(self, score: int) -> ComplexityLevel:
        """Map numeric score to complexity level."""
        if score < 30:
            return ComplexityLevel.LOW
        elif score < 70:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.HIGH

    def _generate_reasoning(
        self,
        keyword_signals: list[DetectedSignal],
        code_signals: list[DetectedSignal],
        math_signals: list[DetectedSignal],
        multipart_signals: list[DetectedSignal],
        length_signal: DetectedSignal,
        score: int,
    ) -> str:
        """Generate human-readable explanation of the analysis."""
        reasons: list[str] = []

        if keyword_signals:
            keywords = [s.value for s in keyword_signals[:3]]  # Show up to 3
            reasons.append(f"Contains reasoning keywords: {', '.join(keywords)}")

        if code_signals:
            reasons.append(f"Contains {len(code_signals)} code block(s)")

        if math_signals:
            reasons.append("Contains mathematical expressions")

        if multipart_signals:
            reasons.append("Contains multi-part question structure")

        reasons.append(f"Prompt length: {length_signal.value}")

        return f"Score {score}/100. " + "; ".join(reasons)
