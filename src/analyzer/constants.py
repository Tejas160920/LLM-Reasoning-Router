"""Constants for prompt complexity analysis.

This module defines the keywords, patterns, and weights used to analyze
prompt complexity and determine appropriate model routing.
"""

# Keywords indicating need for deeper reasoning
# Organized by complexity level (weight)
REASONING_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "analyze",
        "analyse",
        "compare",
        "contrast",
        "evaluate",
        "assess",
        "design",
        "architect",
        "debug",
        "troubleshoot",
        "optimize",
        "refactor",
        "prove",
        "derive",
        "step by step",
        "step-by-step",
        "explain why",
        "reasoning",
        "trade-off",
        "tradeoff",
        "pros and cons",
        "advantages and disadvantages",
        "critically",
        "in-depth",
        "comprehensive",
    ],
    "medium": [
        "explain",
        "describe",
        "summarize",
        "how does",
        "how do",
        "what if",
        "implement",
        "create",
        "build",
        "develop",
        "solve",
        "calculate",
        "compute",
        "determine",
        "figure out",
        "work through",
        "walk through",
        "help me understand",
        "elaborate",
        "clarify",
    ],
    "low": [
        "what is",
        "what are",
        "define",
        "list",
        "name",
        "when",
        "where",
        "who",
        "translate",
        "convert",
        "format",
        "give me",
        "tell me",
        "show me",
    ],
}

# Weights for each keyword level (used in scoring)
KEYWORD_WEIGHTS: dict[str, float] = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}

# Regex patterns for detecting code content
CODE_PATTERNS: list[str] = [
    r"```[\s\S]*?```",  # Fenced code blocks (```code```)
    r"`[^`]+`",  # Inline code (`code`)
    r"def\s+\w+\s*\(",  # Python function definitions
    r"function\s+\w+\s*\(",  # JavaScript function definitions
    r"class\s+\w+[\s:{]",  # Class definitions
    r"import\s+[\w.]+",  # Import statements
    r"from\s+[\w.]+\s+import",  # From imports
    r"const\s+\w+\s*=",  # JavaScript const
    r"let\s+\w+\s*=",  # JavaScript let
    r"var\s+\w+\s*=",  # JavaScript var
    r"public\s+(?:static\s+)?(?:void|int|string|bool)",  # C#/Java methods
    r"async\s+(?:def|function)",  # Async functions
    r"=>\s*{",  # Arrow functions
    r"SELECT\s+.+\s+FROM",  # SQL queries
    r"CREATE\s+TABLE",  # SQL DDL
]

# Regex patterns for detecting mathematical content
MATH_PATTERNS: list[str] = [
    r"\$\$[\s\S]*?\$\$",  # LaTeX display math ($$...$$)
    r"\$[^$]+\$",  # LaTeX inline math ($...$)
    r"\\frac\{",  # LaTeX fractions
    r"\\sum",  # LaTeX summation
    r"\\int",  # LaTeX integral
    r"\d+\s*[\+\-\*\/\^]\s*\d+",  # Basic arithmetic expressions
    r"\d+\s*[=<>]\s*\d+",  # Comparisons
    r"[∫∑∏√∞≤≥≠±×÷]",  # Mathematical symbols
    r"\b(?:integral|derivative|matrix|vector|equation|formula)\b",  # Math terms
    r"\b(?:polynomial|factorial|logarithm|exponential|trigonometric)\b",
    r"\b(?:probability|statistics|regression|correlation)\b",
]

# Patterns indicating multi-part questions
MULTIPART_PATTERNS: list[str] = [
    r"^\s*\d+[.)]\s+",  # Numbered lists (1. or 1))
    r"^\s*[a-z][.)]\s+",  # Lettered lists (a. or a))
    r"^\s*[-*•]\s+",  # Bullet points
    r"\b(?:first|firstly|second|secondly|third|thirdly|finally)\b",
    r"\b(?:additionally|moreover|furthermore|also)\b",
    r"\b(?:and also|as well as|in addition|on top of that)\b",
    r"\?\s*\n.*\?",  # Multiple questions (question marks separated by newlines)
    r"\?\s+(?:And|Also|What|How|Why|Can)",  # Multiple questions in sequence
]

# Signal type weights for final score calculation
SIGNAL_WEIGHTS: dict[str, float] = {
    "keyword": 0.35,  # Reasoning keywords have highest impact
    "code": 0.25,  # Code blocks indicate technical complexity
    "math": 0.20,  # Math content requires analytical thinking
    "multipart": 0.10,  # Multi-part questions add complexity
    "length": 0.10,  # Longer prompts tend to be more complex
}

# Length thresholds for complexity scoring
LENGTH_THRESHOLDS: dict[str, int] = {
    "very_short": 50,  # < 50 chars: minimal complexity from length
    "short": 100,  # 50-100 chars: low complexity
    "medium": 500,  # 100-500 chars: moderate complexity
    "long": 1000,  # 500-1000 chars: higher complexity
    "very_long": 2000,  # > 1000 chars: significant length contribution
}
