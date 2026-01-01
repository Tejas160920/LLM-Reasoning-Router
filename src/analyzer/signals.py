"""Signal detection utilities for prompt complexity analysis.

This module contains functions that detect various complexity signals
in user prompts, such as reasoning keywords, code blocks, mathematical
expressions, and multi-part questions.
"""

import re

from .constants import (
    CODE_PATTERNS,
    KEYWORD_WEIGHTS,
    LENGTH_THRESHOLDS,
    MATH_PATTERNS,
    MULTIPART_PATTERNS,
    REASONING_KEYWORDS,
)
from .schemas import DetectedSignal, SignalType


def detect_reasoning_keywords(text: str) -> list[DetectedSignal]:
    """
    Detect reasoning-related keywords in text.

    Searches for keywords that indicate the need for deeper reasoning,
    such as "analyze", "compare", "debug", "step by step", etc.

    Args:
        text: The prompt text to analyze

    Returns:
        List of DetectedSignal objects for each keyword found
    """
    signals: list[DetectedSignal] = []
    text_lower = text.lower()

    for level, keywords in REASONING_KEYWORDS.items():
        weight = KEYWORD_WEIGHTS[level]
        for keyword in keywords:
            # Find all occurrences of the keyword
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(text_lower):
                signals.append(
                    DetectedSignal(
                        signal_type=SignalType.REASONING_KEYWORD,
                        value=keyword,
                        weight=weight,
                        position=match.start(),
                    )
                )

    return signals


def detect_code_blocks(text: str) -> list[DetectedSignal]:
    """
    Detect code blocks and programming content in text.

    Looks for fenced code blocks (```), inline code (`), function
    definitions, class declarations, and other programming constructs.

    Args:
        text: The prompt text to analyze

    Returns:
        List of DetectedSignal objects for each code pattern found
    """
    signals: list[DetectedSignal] = []

    for pattern in CODE_PATTERNS:
        try:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                # Truncate long matches for readability
                matched_text = match.group()
                display_text = (
                    matched_text[:50] + "..."
                    if len(matched_text) > 50
                    else matched_text
                )

                signals.append(
                    DetectedSignal(
                        signal_type=SignalType.CODE_BLOCK,
                        value=display_text,
                        weight=0.7,  # Code has consistent weight
                        position=match.start(),
                    )
                )
        except re.error:
            # Skip invalid regex patterns
            continue

    return signals


def detect_math_expressions(text: str) -> list[DetectedSignal]:
    """
    Detect mathematical expressions and notation in text.

    Looks for LaTeX math notation, arithmetic expressions, mathematical
    symbols, and math-related terminology.

    Args:
        text: The prompt text to analyze

    Returns:
        List of DetectedSignal objects for each math pattern found
    """
    signals: list[DetectedSignal] = []

    for pattern in MATH_PATTERNS:
        try:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = match.group()
                display_text = (
                    matched_text[:30] + "..."
                    if len(matched_text) > 30
                    else matched_text
                )

                signals.append(
                    DetectedSignal(
                        signal_type=SignalType.MATH_EXPRESSION,
                        value=display_text,
                        weight=0.8,  # Math has high weight
                        position=match.start(),
                    )
                )
        except re.error:
            continue

    return signals


def detect_multipart_questions(text: str) -> list[DetectedSignal]:
    """
    Detect multi-part or compound questions in text.

    Looks for numbered/bulleted lists, sequence words (first, second),
    and multiple question marks indicating compound questions.

    Args:
        text: The prompt text to analyze

    Returns:
        List of DetectedSignal objects for each multi-part indicator found
    """
    signals: list[DetectedSignal] = []

    for pattern in MULTIPART_PATTERNS:
        try:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                matched_text = match.group().strip()
                display_text = (
                    matched_text[:30] + "..."
                    if len(matched_text) > 30
                    else matched_text
                )

                signals.append(
                    DetectedSignal(
                        signal_type=SignalType.MULTIPART_QUESTION,
                        value=display_text,
                        weight=0.5,  # Multi-part has moderate weight
                        position=match.start(),
                    )
                )
        except re.error:
            continue

    return signals


def calculate_length_signal(text: str) -> DetectedSignal:
    """
    Calculate complexity signal based on prompt length.

    Longer prompts tend to be more complex, though the relationship
    is not linear. Very short prompts are typically simple questions.

    Args:
        text: The prompt text to analyze

    Returns:
        A single DetectedSignal representing length-based complexity
    """
    length = len(text)

    # Calculate weight based on length thresholds
    if length < LENGTH_THRESHOLDS["very_short"]:
        weight = 0.1
    elif length < LENGTH_THRESHOLDS["short"]:
        weight = 0.2
    elif length < LENGTH_THRESHOLDS["medium"]:
        weight = 0.4
    elif length < LENGTH_THRESHOLDS["long"]:
        weight = 0.6
    elif length < LENGTH_THRESHOLDS["very_long"]:
        weight = 0.8
    else:
        # For very long prompts, cap at 0.9
        weight = min(0.9, 0.8 + (length - LENGTH_THRESHOLDS["very_long"]) / 10000)

    return DetectedSignal(
        signal_type=SignalType.LENGTH,
        value=f"{length} characters",
        weight=weight,
        position=None,  # Length doesn't have a specific position
    )


def deduplicate_signals(signals: list[DetectedSignal]) -> list[DetectedSignal]:
    """
    Remove duplicate signals based on value and type.

    When the same keyword or pattern is detected multiple times,
    keep only the first occurrence with the highest weight.

    Args:
        signals: List of detected signals

    Returns:
        Deduplicated list of signals
    """
    seen: dict[tuple[SignalType, str], DetectedSignal] = {}

    for signal in signals:
        key = (signal.signal_type, signal.value.lower())
        if key not in seen or signal.weight > seen[key].weight:
            seen[key] = signal

    return list(seen.values())
