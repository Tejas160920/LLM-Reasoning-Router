"""Escalation handler service.

This module contains the EscalationHandler class which manages
automatic escalation from fast models to complex models when
response quality is insufficient.
"""

import uuid
from datetime import datetime, timezone

from src.config import Settings
from src.llm.client import GeminiClient
from src.llm.schemas import ChatResponse, Message
from src.quality.service import QualityChecker

from .schemas import CombinedResponse, EscalationChain, EscalationStep
from .strategies import CombinationStrategy, UseLatestStrategy


class EscalationHandler:
    """
    Handles automatic escalation when response quality is poor.

    The handler:
    1. Generates a response with the initial model
    2. Checks response quality
    3. If quality is below threshold, escalates to a better model
    4. Tracks the escalation chain to prevent infinite loops
    5. Optionally combines responses from multiple attempts

    Example:
        settings = get_settings()
        client = GeminiClient(settings)
        checker = QualityChecker(settings)
        handler = EscalationHandler(settings, client, checker)

        messages = [Message(role="user", content="Complex question...")]
        response, chain = await handler.handle_with_escalation(
            messages=messages,
            initial_model="gemini-2.0-flash",
            complexity_score=55
        )

        if chain.total_attempts > 1:
            print(f"Escalated {chain.total_attempts - 1} times")
    """

    def __init__(
        self,
        settings: Settings,
        llm_client: GeminiClient,
        quality_checker: QualityChecker,
        combination_strategy: CombinationStrategy | None = None,
    ):
        """
        Initialize the escalation handler.

        Args:
            settings: Application settings with model config
            llm_client: Client for making LLM requests
            quality_checker: Checker for assessing response quality
            combination_strategy: Strategy for combining multiple responses
        """
        self.settings = settings
        self.llm_client = llm_client
        self.quality_checker = quality_checker
        self.combination_strategy = combination_strategy or UseLatestStrategy()
        self.max_depth = settings.max_escalation_depth

    async def handle_with_escalation(
        self,
        messages: list[Message],
        initial_model: str,
        complexity_score: int,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> tuple[ChatResponse, EscalationChain]:
        """
        Handle a request with automatic escalation if quality is poor.

        Args:
            messages: The conversation messages
            initial_model: Starting model to use
            complexity_score: Complexity score of the prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (final ChatResponse, EscalationChain record)
        """
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        prompt = messages[-1].content if messages else ""
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt

        steps: list[EscalationStep] = []
        responses: list[str] = []
        models_used: list[str] = []
        total_latency_ms = 0.0

        current_model = initial_model
        loop_prevented = False
        final_response: ChatResponse | None = None

        for attempt in range(self.max_depth + 1):
            # Generate response
            response = await self.llm_client.generate(
                messages=messages,
                model=current_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            responses.append(response.content)
            models_used.append(current_model)
            total_latency_ms += response.latency_ms
            final_response = response

            # Check quality
            quality = self.quality_checker.check(
                response.content,
                complexity_score,
            )

            # Determine if we should escalate
            should_escalate = (
                quality.should_escalate
                and attempt < self.max_depth
                and current_model != self.settings.complex_model
            )

            # Record this step
            steps.append(
                EscalationStep(
                    model_used=current_model,
                    response_preview=(
                        response.content[:200] + "..."
                        if len(response.content) > 200
                        else response.content
                    ),
                    quality_score=quality.quality_score,
                    escalated=should_escalate,
                    latency_ms=response.latency_ms,
                    timestamp=datetime.now(timezone.utc),
                )
            )

            # Decide whether to continue
            if not quality.should_escalate:
                # Quality is acceptable, we're done
                break

            if attempt >= self.max_depth:
                # Max depth reached
                loop_prevented = True
                break

            if current_model == self.settings.complex_model:
                # Already at the best model, can't escalate further
                break

            # Escalate to complex model
            current_model = self.settings.complex_model

        # Build the escalation chain record
        chain = EscalationChain(
            request_id=request_id,
            original_prompt_preview=prompt_preview,
            steps=steps,
            final_model=current_model,
            final_response=final_response.content if final_response else "",
            total_attempts=len(steps),
            total_latency_ms=total_latency_ms,
            escalation_prevented_loop=loop_prevented,
        )

        # Return the final response (already a ChatResponse object)
        assert final_response is not None
        return final_response, chain

    def combine_responses(self, chain: EscalationChain) -> CombinedResponse:
        """
        Combine responses from an escalation chain.

        Args:
            chain: The escalation chain to combine

        Returns:
            CombinedResponse with the combined result
        """
        responses = [step.response_preview for step in chain.steps]
        models = [step.model_used for step in chain.steps]
        return self.combination_strategy.combine(responses, models)

    async def handle_direct(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """
        Handle a request directly without escalation.

        Use this when you want to bypass escalation logic,
        for example when routing directly to the complex model.

        Args:
            messages: The conversation messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            ChatResponse from the specified model
        """
        return await self.llm_client.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
