"""Fast prompt analysis endpoint.

This endpoint provides instant complexity analysis without calling the LLM,
allowing the UI to show immediate feedback while waiting for the response.
"""

from pydantic import BaseModel

from fastapi import APIRouter

from src.dependencies import RoutingEngineDep


router = APIRouter(prefix="/analyze", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    """Request for prompt analysis."""
    prompt: str


class AnalyzeResponse(BaseModel):
    """Instant analysis response."""
    complexity_score: int
    complexity_level: str
    selected_model: str
    model_tier: str
    reasoning: str
    detected_signals: list[str]


@router.post("", response_model=AnalyzeResponse)
def analyze_prompt(
    request: AnalyzeRequest,
    routing_engine: RoutingEngineDep,
) -> AnalyzeResponse:
    """
    Instantly analyze prompt complexity without calling LLM.

    This endpoint is fast (<1ms) and returns:
    - Complexity score (0-100)
    - Complexity level (low/medium/high)
    - Which model will be used
    - Detected signals (reasoning keywords, code, math, etc.)

    Use this for instant UI feedback before the slower chat completion.
    """
    analysis, routing = routing_engine.route_with_analysis(request.prompt)

    return AnalyzeResponse(
        complexity_score=analysis.complexity_score,
        complexity_level=analysis.level.value,
        selected_model=routing.selected_model,
        model_tier=routing.tier.value,
        reasoning=routing.reasoning,
        detected_signals=[s.signal_type.value for s in analysis.detected_signals],
    )
