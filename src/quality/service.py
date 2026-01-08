"""Quality checker service.

This module contains the QualityChecker class which assesses
LLM response quality and recommends escalation when needed.
"""

from src.config import Settings

from .detectors import (
    detect_failed_reasoning,
    detect_incomplete,
    detect_refusal,
    detect_repetition,
    detect_too_short,
    detect_uncertainty,
)
from .schemas import QualityAssessment, QualityIssue


class QualityChecker:
    """
    Checks LLM response quality and recommends escalation when needed.

    The checker examines multiple quality signals:
    1. Uncertainty phrases ("I'm not sure", "might be", etc.)
    2. Incomplete responses (trailing ellipsis, cut-off lists)
    3. Failed reasoning patterns ("I cannot", "I am unable")
    4. Refusal to answer
    5. Response length relative to prompt complexity
    6. Repetition patterns

    Example:
        settings = get_settings()
        checker = QualityChecker(settings)

        assessment = checker.check(
            "I'm not sure, but maybe the answer is 42...",
            prompt_complexity=65
        )

        if assessment.should_escalate:
            print(f"Escalating: {assessment.escalation_reason}")
    """

    def __init__(
        self,
        settings: Settings,
        min_response_length: int = 50,
        quality_threshold: int | None = None,
    ):
        """
        Initialize the quality checker.

        Args:
            settings: Application settings with quality threshold
            min_response_length: Minimum expected response length
            quality_threshold: Quality score below which to escalate
                              (defaults to settings.quality_threshold)
        """
        self.settings = settings
        self.min_response_length = min_response_length
        self.quality_threshold = quality_threshold or settings.quality_threshold

    def check(
        self,
        response_text: str,
        prompt_complexity: int = 50,
    ) -> QualityAssessment:
        """
        Check response quality and recommend escalation if needed.

        Args:
            response_text: The LLM response to check
            prompt_complexity: Complexity score of original prompt (0-100)

        Returns:
            QualityAssessment with score, issues, and escalation recommendation
        """
        # Handle empty responses
        if not response_text or not response_text.strip():
            return QualityAssessment(
                quality_score=0,
                issues=[
                    QualityIssue(
                        issue_type="too_short",
                        description="Response is empty",
                        severity=1.0,
                        evidence="(empty response)",
                    )
                ],
                should_escalate=True,
                escalation_reason="Empty response received",
                confidence=1.0,
            )

        # Run all detectors
        all_issues: list[QualityIssue] = []

        all_issues.extend(detect_uncertainty(response_text))
        all_issues.extend(detect_incomplete(response_text))
        all_issues.extend(detect_failed_reasoning(response_text))
        all_issues.extend(detect_refusal(response_text))
        all_issues.extend(
            detect_too_short(
                response_text,
                self.min_response_length,
                prompt_complexity,
            )
        )
        all_issues.extend(detect_repetition(response_text))

        # Calculate quality score
        quality_score = self._calculate_score(all_issues)

        # Determine if escalation is needed
        should_escalate = quality_score < self.quality_threshold

        # Generate escalation reason if needed
        escalation_reason = None
        if should_escalate and all_issues:
            main_issue = max(all_issues, key=lambda i: i.severity)
            escalation_reason = (
                f"Quality score {quality_score} below threshold ({self.quality_threshold}). "
                f"Main issue: {main_issue.description}"
            )
        elif should_escalate:
            escalation_reason = (
                f"Quality score {quality_score} below threshold ({self.quality_threshold})"
            )

        # Calculate confidence in assessment
        confidence = self._calculate_confidence(all_issues, response_text)

        return QualityAssessment(
            quality_score=quality_score,
            issues=all_issues,
            should_escalate=should_escalate,
            escalation_reason=escalation_reason,
            confidence=confidence,
        )

    def _calculate_score(self, issues: list[QualityIssue]) -> int:
        """
        Calculate quality score from 0-100.

        Each issue reduces the score based on its severity.
        """
        if not issues:
            return 100

        # Each issue reduces score based on severity
        # Max penalty per issue is 25 points
        total_penalty = sum(issue.severity * 25 for issue in issues)

        # Ensure score stays in 0-100 range
        return max(0, int(100 - total_penalty))

    def _calculate_confidence(
        self,
        issues: list[QualityIssue],
        response_text: str,
    ) -> float:
        """
        Calculate confidence in quality assessment.

        Higher confidence when:
        - More text to analyze
        - Clear issues with high severity
        """
        # More text = more reliable assessment
        length_factor = min(1.0, len(response_text) / 500)

        if issues:
            # Clear issues = higher confidence
            avg_severity = sum(i.severity for i in issues) / len(issues)
            issue_clarity = avg_severity
        else:
            # No issues is somewhat ambiguous (could be good or missed issues)
            issue_clarity = 0.7

        # Combine factors
        confidence = length_factor * 0.4 + issue_clarity * 0.6

        return round(min(1.0, confidence), 2)
