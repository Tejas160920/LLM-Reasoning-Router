"""Chat completion API endpoint.

This module provides the main /chat/completions endpoint that handles
intelligent model routing, quality checking, and automatic escalation.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    RoutingInfo,
    Usage,
)
from src.dependencies import (
    EscalationHandlerDep,
    LLMClientDep,
    MetricsServiceDep,
    QualityCheckerDep,
    RoutingEngineDep,
)
from src.db.session import async_session_factory
from src.llm.exceptions import LLMError
from src.llm.schemas import ChatResponse, Message, TokenUsage
from src.metrics.service import MetricsService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    routing_engine: RoutingEngineDep,
    quality_checker: QualityCheckerDep,
    escalation_handler: EscalationHandlerDep,
    metrics_service: MetricsServiceDep,
) -> ChatCompletionResponse:
    """
    Create a chat completion with intelligent model routing.

    This endpoint:
    1. Analyzes prompt complexity to determine appropriate model
    2. Routes simple prompts to fast/cheap models
    3. Routes complex prompts to reasoning models
    4. Checks response quality and escalates if needed
    5. Logs all metrics for analysis

    The API is compatible with OpenAI's chat completion format.
    """
    try:
        # Convert API messages to internal format
        messages = [
            Message(role=m.role, content=m.content)
            for m in request.messages
        ]

        # Get the user's prompt (last user message)
        user_prompt = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )

        if not user_prompt:
            raise HTTPException(
                status_code=400,
                detail="No user message found in request",
            )

        # Analyze and route
        analysis, routing_decision = routing_engine.route_with_analysis(user_prompt)

        # Determine which model to use
        if request.force_model:
            model_to_use = request.force_model
        elif request.model:
            model_to_use = request.model
        else:
            model_to_use = routing_decision.selected_model

        # Handle request with potential escalation
        quality_assessment = None
        escalation_chain = None

        if routing_decision.requires_quality_check and not request.skip_quality_check:
            # Use escalation handler for medium complexity requests
            response, escalation_chain = await escalation_handler.handle_with_escalation(
                messages=messages,
                initial_model=model_to_use,
                complexity_score=analysis.complexity_score,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            final_model = escalation_chain.final_model
            was_escalated = escalation_chain.total_attempts > 1

            # Get quality score from the last step
            if escalation_chain.steps:
                quality_score = escalation_chain.steps[-1].quality_score
            else:
                quality_score = None
        else:
            # Direct call without quality check
            response = await escalation_handler.handle_direct(
                messages=messages,
                model=model_to_use,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            final_model = model_to_use
            was_escalated = False

            # Optionally check quality for metrics even if not escalating
            quality_assessment = quality_checker.check(
                response.content,
                analysis.complexity_score,
            )
            quality_score = quality_assessment.quality_score

        # Log metrics to database
        try:
            await metrics_service.log_request(
                prompt=user_prompt,
                analysis=analysis,
                routing=routing_decision,
                response=response,
                quality=quality_assessment,
                escalation=escalation_chain,
            )
        except Exception as log_error:
            # Don't fail the request if logging fails
            print(f"Warning: Failed to log metrics: {log_error}")

        # Build response
        completion_response = ChatCompletionResponse(
            id=response.id,
            created=int(datetime.now(timezone.utc).timestamp()),
            model=final_model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response.content),
                    finish_reason=response.finish_reason,
                )
            ],
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
        )

        # Include routing info if requested
        if request.include_analysis:
            completion_response.routing_info = RoutingInfo(
                complexity_score=analysis.complexity_score,
                complexity_level=analysis.level.value,
                initial_model=routing_decision.selected_model,
                final_model=final_model,
                was_escalated=was_escalated,
                quality_score=quality_score,
                routing_reasoning=routing_decision.reasoning,
            )

        return completion_response

    except LLMError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM error: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


@router.post("/completions/stream")
async def create_chat_completion_stream(
    request: ChatCompletionRequest,
    routing_engine: RoutingEngineDep,
    llm_client: LLMClientDep,
    quality_checker: QualityCheckerDep,
) -> StreamingResponse:
    """
    Create a streaming chat completion with intelligent model routing.

    Returns Server-Sent Events (SSE) stream with:
    - Analysis results (instant)
    - Content chunks as they're generated
    - Final usage statistics

    Use this for ChatGPT-like streaming responses.
    """
    # Convert API messages to internal format
    messages = [
        Message(role=m.role, content=m.content)
        for m in request.messages
    ]

    # Get the user's prompt
    user_prompt = next(
        (m.content for m in reversed(messages) if m.role == "user"),
        "",
    )

    if not user_prompt:
        raise HTTPException(
            status_code=400,
            detail="No user message found in request",
        )

    # Analyze and route
    analysis, routing_decision = routing_engine.route_with_analysis(user_prompt)

    # Determine model
    if request.force_model:
        model_to_use = request.force_model
    elif request.model:
        model_to_use = request.model
    else:
        model_to_use = routing_decision.selected_model

    async def generate_stream():
        """Generate SSE stream."""
        # First, send analysis results immediately
        analysis_data = {
            "type": "analysis",
            "complexity_score": analysis.complexity_score,
            "complexity_level": analysis.level.value,
            "selected_model": model_to_use,
            "model_tier": routing_decision.tier.value,
            "reasoning": routing_decision.reasoning,
            "detected_signals": [s.signal_type.value for s in analysis.detected_signals],
        }
        yield f"data: {json.dumps(analysis_data)}\n\n"

        # Stream LLM response
        full_text = ""
        final_usage = None
        quality_result = None
        start_time = datetime.now(timezone.utc)
        try:
            async for chunk in llm_client.generate_stream(
                messages=messages,
                model=model_to_use,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                if chunk["type"] == "chunk":
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk["type"] == "done":
                    full_text = chunk.get("full_text", "")
                    final_usage = chunk.get("usage", {})

                    # Calculate quality score immediately
                    quality_result = quality_checker.check(full_text, analysis.complexity_score)

                    # Log metrics to database BEFORE sending done (create new session)
                    try:
                        latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                        response_obj = ChatResponse(
                            id=f"stream-{start_time.timestamp()}",
                            content=full_text,
                            finish_reason=chunk.get("finish_reason", "stop"),
                            usage=TokenUsage(
                                prompt_tokens=final_usage.get("prompt_tokens", 0),
                                completion_tokens=final_usage.get("completion_tokens", 0),
                                total_tokens=final_usage.get("total_tokens", 0),
                            ),
                            latency_ms=latency_ms,
                        )

                        async with async_session_factory() as log_session:
                            log_metrics_service = MetricsService(log_session)
                            await log_metrics_service.log_request(
                                prompt=user_prompt,
                                analysis=analysis,
                                routing=routing_decision,
                                response=response_obj,
                                quality=quality_result,
                            )
                            await log_session.commit()
                    except Exception as log_error:
                        import traceback
                        print(f"Warning: Failed to log streaming metrics: {log_error}")
                        traceback.print_exc()

                    # Send done with quality score included
                    done_data = {
                        "type": "done",
                        "usage": final_usage,
                        "finish_reason": chunk.get("finish_reason", "stop"),
                        "quality_score": quality_result.quality_score,
                    }
                    yield f"data: {json.dumps(done_data)}\n\n"
        except LLMError as e:
            error_data = {"type": "error", "message": e.message}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
