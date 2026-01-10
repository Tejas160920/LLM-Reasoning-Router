"""Unit tests for the PromptAnalyzer."""

import pytest

from src.analyzer.schemas import ComplexityLevel
from src.analyzer.service import PromptAnalyzer


class TestPromptAnalyzer:
    """Unit tests for PromptAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create a PromptAnalyzer instance."""
        return PromptAnalyzer()

    def test_empty_prompt(self, analyzer):
        """Empty prompts should have complexity 0."""
        result = analyzer.analyze("")
        assert result.complexity_score == 0
        assert result.level == ComplexityLevel.LOW

    def test_simple_prompt_low_complexity(self, analyzer):
        """Simple questions should have low complexity."""
        result = analyzer.analyze("What is Python?")
        assert result.complexity_score < 30
        assert result.level == ComplexityLevel.LOW

    def test_reasoning_keywords_increase_complexity(self, analyzer):
        """Reasoning keywords should increase complexity score."""
        simple = analyzer.analyze("Tell me about Python")
        complex_prompt = analyzer.analyze("Analyze and compare Python with Java")

        assert complex_prompt.complexity_score > simple.complexity_score

    def test_code_blocks_detected(self, analyzer):
        """Code blocks should be detected and increase complexity."""
        prompt = """
        Fix this code:
        ```python
        def foo():
            return bar
        ```
        """
        result = analyzer.analyze(prompt)

        # Should have code block signals
        signal_types = [s.signal_type.value for s in result.detected_signals]
        assert "code_block" in signal_types

    def test_math_expressions_detected(self, analyzer):
        """Math expressions should be detected."""
        result = analyzer.analyze("Solve: $x^2 + 2x + 1 = 0$")

        signal_types = [s.signal_type.value for s in result.detected_signals]
        assert "math_expression" in signal_types

    def test_multipart_questions_increase_complexity(self, analyzer):
        """Multi-part questions should increase complexity."""
        single = analyzer.analyze("What is Python?")
        multi = analyzer.analyze(
            "1. What is Python? 2. How does it work? 3. Why use it?"
        )

        assert multi.complexity_score > single.complexity_score

    def test_step_by_step_high_complexity(self, analyzer):
        """'Step by step' should trigger high complexity weight."""
        result = analyzer.analyze(
            "Explain step by step how to implement a binary search tree"
        )

        assert result.complexity_score >= 50
        signal_types = [s.signal_type.value for s in result.detected_signals]
        assert "reasoning_keyword" in signal_types

    def test_longer_prompts_higher_complexity(self, analyzer):
        """Longer prompts should have higher length-based complexity."""
        short = analyzer.analyze("Hello")
        long_prompt = analyzer.analyze(
            "Please provide a comprehensive explanation of " * 20
        )

        # Check length signals
        short_length = next(
            s.weight for s in short.detected_signals if s.signal_type.value == "length"
        )
        long_length = next(
            s.weight for s in long_prompt.detected_signals if s.signal_type.value == "length"
        )

        assert long_length > short_length

    def test_confidence_varies_with_signals(self, analyzer):
        """Confidence should reflect signal clarity."""
        # Very clear complex prompt
        complex_result = analyzer.analyze(
            """
            Analyze, compare, and evaluate the following algorithms step by step:
            ```python
            def sort1(arr): pass
            def sort2(arr): pass
            ```
            Consider time complexity, space complexity, and stability.
            """
        )

        # Ambiguous prompt
        ambiguous = analyzer.analyze("Hello there")

        # Complex prompt should have higher confidence
        assert complex_result.confidence > ambiguous.confidence

    def test_complexity_levels_map_correctly(self, analyzer):
        """Complexity levels should map to correct score ranges."""
        # Low complexity
        low = analyzer.analyze("Hi")
        assert low.level == ComplexityLevel.LOW

        # Should be able to achieve high complexity with multiple signals
        high = analyzer.analyze(
            """
            Analyze step by step and compare the following:
            ```python
            def algorithm1(): pass
            def algorithm2(): pass
            ```
            Calculate: $O(n) vs O(log n)$
            1. Time complexity
            2. Space complexity
            3. Use cases
            """
        )
        assert high.level == ComplexityLevel.HIGH

    def test_reasoning_includes_detected_signals(self, analyzer):
        """Reasoning explanation should mention detected signals."""
        result = analyzer.analyze("Analyze this code block: ```python pass```")

        assert "code block" in result.reasoning.lower()


class TestPromptAnalyzerWeights:
    """Tests for customizable weights."""

    def test_custom_weights_affect_score(self):
        """Custom weights should change the final score."""
        default_analyzer = PromptAnalyzer()
        heavy_keyword_analyzer = PromptAnalyzer(keyword_weight=0.8, code_weight=0.05)

        prompt = "Analyze this code: ```python pass```"

        default_result = default_analyzer.analyze(prompt)
        custom_result = heavy_keyword_analyzer.analyze(prompt)

        # With higher keyword weight, the "analyze" keyword should have more impact
        # But this depends on the specific prompt
        assert default_result.complexity_score != custom_result.complexity_score
