"""Response combination strategies for escalation.

When a request is escalated through multiple models, these strategies
determine how to combine or select the final response.
"""

from abc import ABC, abstractmethod

from .schemas import CombinedResponse


class CombinationStrategy(ABC):
    """Base class for response combination strategies."""

    @abstractmethod
    def combine(
        self,
        responses: list[str],
        models: list[str],
    ) -> CombinedResponse:
        """
        Combine multiple responses into a single result.

        Args:
            responses: List of response texts from different models
            models: List of model names corresponding to each response

        Returns:
            CombinedResponse with the final result
        """
        pass


class UseLatestStrategy(CombinationStrategy):
    """
    Simply use the latest (escalated) response.

    This is the recommended default strategy as escalation is triggered
    because earlier responses were insufficient, so the latest response
    from the more capable model should be used.
    """

    def combine(
        self,
        responses: list[str],
        models: list[str],
    ) -> CombinedResponse:
        """Use the most recent response."""
        return CombinedResponse(
            primary_response=responses[-1],
            supporting_context=None,
            models_used=models,
            combination_strategy="use_latest",
        )


class MergeWithContextStrategy(CombinationStrategy):
    """
    Use the latest response but preserve earlier attempts as context.

    This can be useful for debugging or when you want to show
    users how the response evolved through escalation.
    """

    def combine(
        self,
        responses: list[str],
        models: list[str],
    ) -> CombinedResponse:
        """Use latest response with earlier attempts as context."""
        if len(responses) == 1:
            return CombinedResponse(
                primary_response=responses[0],
                supporting_context=None,
                models_used=models,
                combination_strategy="single_response",
            )

        # Build context from earlier attempts
        context_parts: list[str] = []
        for i, (resp, model) in enumerate(zip(responses[:-1], models[:-1])):
            # Truncate long responses
            preview = resp[:500] + "..." if len(resp) > 500 else resp
            context_parts.append(f"[Attempt {i + 1} from {model}]:\n{preview}")

        return CombinedResponse(
            primary_response=responses[-1],
            supporting_context="\n\n".join(context_parts),
            models_used=models,
            combination_strategy="merge_with_context",
        )


class UseBestQualityStrategy(CombinationStrategy):
    """
    Use the response with the highest quality score.

    This strategy requires quality scores to be passed along with
    responses, which happens through the escalation chain.

    Note: This is a simplified version that just uses the latest
    response, as quality scores would need to be passed separately.
    For production use, consider extending this to accept quality scores.
    """

    def combine(
        self,
        responses: list[str],
        models: list[str],
    ) -> CombinedResponse:
        """
        Use the response with best quality.

        Currently defaults to latest response as quality scores
        aren't passed to this method directly.
        """
        # In a full implementation, you'd pass quality scores and select best
        # For now, assume escalation improves quality, so use latest
        return CombinedResponse(
            primary_response=responses[-1],
            supporting_context=None,
            models_used=models,
            combination_strategy="use_best_quality",
        )
