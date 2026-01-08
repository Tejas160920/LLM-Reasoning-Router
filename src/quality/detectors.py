"""Quality issue detection utilities.

This module contains functions that detect various quality issues
in LLM responses, such as uncertainty, incompleteness, and failed reasoning.
"""

import re

from .schemas import QualityIssue, QualityIssueType

# Phrases indicating uncertainty in responses
UNCERTAINTY_PATTERNS: list[str] = [
    r"i'?m not (?:entirely |completely |fully )?sure",
    r"i'?m not certain",
    r"i'?m uncertain",
    r"might be",
    r"may be",
    r"possibly",
    r"perhaps",
    r"i think(?! that)",  # "I think" but not "I think that X is Y"
    r"i believe(?! that)",
    r"it seems like",
    r"it appears (?:to be |that )",
    r"could be",
    r"probably",
    r"not 100% sure",
    r"hard to say",
    r"difficult to determine",
    r"i don'?t (?:really )?know",
    r"(?:this|that) is (?:just )?(?:a |my )?guess",
    r"if i had to guess",
    r"take this with a grain of salt",
]

# Patterns indicating incomplete responses
INCOMPLETE_PATTERNS: list[str] = [
    r"\.\.\.\s*$",  # Trailing ellipsis
    r"…\s*$",  # Unicode ellipsis at end
    r"(?:etc|and so on|and more|and others)\s*\.?\s*$",  # Trailing etc
    r":\s*$",  # Ends with colon (expecting list)
    r"\d+\.\s*$",  # Ends with numbered item start
    r"(?:First|1\.)[^.]*$",  # Starts numbered list but doesn't finish
    r"to be continued",
    r"i'll continue",
    r"let me know if you.{0,30}$",  # Trailing "let me know" without completion
]

# Patterns indicating failed reasoning or inability to help
FAILED_REASONING_PATTERNS: list[str] = [
    r"i cannot (?:help|assist|provide|answer)",
    r"i am unable to",
    r"i'?m unable to",
    r"i don'?t have (?:the |enough )?(?:ability|capability|information|access)",
    r"(?:this|that) is (?:beyond|outside) (?:my|the) (?:capabilities|scope|knowledge)",
    r"i apologize.{0,50}cannot",
    r"i'?m sorry.{0,30}(?:cannot|can't|unable)",
    r"unfortunately.{0,30}(?:cannot|can't|unable)",
    r"i'?m not able to",
]

# Patterns indicating refusal to answer
REFUSAL_PATTERNS: list[str] = [
    r"i (?:cannot|can't|won't|will not) (?:help|assist) with (?:that|this)",
    r"(?:this|that) (?:request|question) (?:is|seems) (?:inappropriate|harmful)",
    r"i'?m not (?:going to|able to) (?:help|assist) with",
    r"(?:that's|this is) not something i can",
    r"i have to decline",
    r"i must refuse",
]


def detect_uncertainty(text: str) -> list[QualityIssue]:
    """
    Detect uncertainty phrases in response.

    Args:
        text: The LLM response text

    Returns:
        List of QualityIssue objects for detected uncertainty
    """
    issues: list[QualityIssue] = []
    text_lower = text.lower()

    matches_found: list[str] = []
    for pattern in UNCERTAINTY_PATTERNS:
        matches = list(re.finditer(pattern, text_lower))
        for match in matches:
            matches_found.append(match.group())

    if matches_found:
        # More matches = higher severity, capped at 0.8
        severity = min(0.8, 0.2 * len(matches_found))
        issues.append(
            QualityIssue(
                issue_type=QualityIssueType.UNCERTAINTY,
                description=f"Found {len(matches_found)} uncertainty phrase(s)",
                severity=severity,
                evidence=matches_found[0][:50],
            )
        )

    return issues


def detect_incomplete(text: str) -> list[QualityIssue]:
    """
    Detect signs of incomplete responses.

    Args:
        text: The LLM response text

    Returns:
        List of QualityIssue objects for detected incompleteness
    """
    issues: list[QualityIssue] = []

    for pattern in INCOMPLETE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            # Get the last 100 chars as evidence
            evidence = text[-100:].strip() if len(text) > 100 else text.strip()
            issues.append(
                QualityIssue(
                    issue_type=QualityIssueType.INCOMPLETE,
                    description="Response appears to be incomplete",
                    severity=0.7,
                    evidence=evidence,
                )
            )
            break  # One incomplete issue is enough

    return issues


def detect_failed_reasoning(text: str) -> list[QualityIssue]:
    """
    Detect patterns indicating the model couldn't complete the task.

    Args:
        text: The LLM response text

    Returns:
        List of QualityIssue objects for detected reasoning failures
    """
    issues: list[QualityIssue] = []
    text_lower = text.lower()

    for pattern in FAILED_REASONING_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            issues.append(
                QualityIssue(
                    issue_type=QualityIssueType.FAILED_REASONING,
                    description="Response indicates inability to complete task",
                    severity=0.9,
                    evidence=match.group()[:50],
                )
            )
            break  # One is enough

    return issues


def detect_refusal(text: str) -> list[QualityIssue]:
    """
    Detect explicit refusal to answer.

    Args:
        text: The LLM response text

    Returns:
        List of QualityIssue objects for detected refusals
    """
    issues: list[QualityIssue] = []
    text_lower = text.lower()

    for pattern in REFUSAL_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            issues.append(
                QualityIssue(
                    issue_type=QualityIssueType.REFUSAL,
                    description="Model refused to answer the request",
                    severity=1.0,  # Refusal is highest severity
                    evidence=match.group()[:50],
                )
            )
            break

    return issues


def detect_too_short(
    text: str,
    min_length: int = 50,
    prompt_complexity: int = 50,
) -> list[QualityIssue]:
    """
    Detect responses that are suspiciously short.

    Args:
        text: The LLM response text
        min_length: Minimum expected length
        prompt_complexity: Complexity score of the original prompt (0-100)

    Returns:
        List of QualityIssue objects if response is too short
    """
    issues: list[QualityIssue] = []
    text_stripped = text.strip()

    # Adjust expected minimum based on prompt complexity
    expected_min = min_length + (prompt_complexity * 2)

    if len(text_stripped) < expected_min:
        severity = max(0.3, 1.0 - (len(text_stripped) / expected_min))
        issues.append(
            QualityIssue(
                issue_type=QualityIssueType.TOO_SHORT,
                description=f"Response is only {len(text_stripped)} characters (expected >{expected_min})",
                severity=min(0.7, severity),
                evidence=text_stripped[:100] if text_stripped else "(empty)",
            )
        )

    return issues


def detect_repetition(text: str) -> list[QualityIssue]:
    """
    Detect excessive repetition in response.

    Args:
        text: The LLM response text

    Returns:
        List of QualityIssue objects if excessive repetition detected
    """
    issues: list[QualityIssue] = []

    # Split into sentences
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip().lower() for s in sentences if s.strip() and len(s.strip()) > 10]

    if len(sentences) < 3:
        return issues  # Not enough sentences to check

    # Check for repeated sentences
    unique_sentences = set(sentences)
    repetition_ratio = 1 - (len(unique_sentences) / len(sentences))

    if repetition_ratio > 0.3:  # More than 30% repeated
        issues.append(
            QualityIssue(
                issue_type=QualityIssueType.REPETITION,
                description=f"High repetition ratio: {repetition_ratio:.0%}",
                severity=min(0.8, repetition_ratio),
                evidence=None,
            )
        )

    # Check for repeated phrases (3+ consecutive repeated words)
    words = text.lower().split()
    if len(words) > 10:
        for i in range(len(words) - 6):
            phrase = " ".join(words[i : i + 3])
            rest = " ".join(words[i + 3 :])
            if phrase in rest:
                # Found repeated phrase
                if not any(i.issue_type == QualityIssueType.REPETITION for i in issues):
                    issues.append(
                        QualityIssue(
                            issue_type=QualityIssueType.REPETITION,
                            description="Contains repeated phrases",
                            severity=0.5,
                            evidence=phrase,
                        )
                    )
                break

    return issues
