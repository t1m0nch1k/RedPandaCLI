from __future__ import annotations

from typing import Any, Protocol

from aios.runtime.models import ContextStatus


class CompactionStrategy(Protocol):
    """Strategy for conversation compaction when the token budget is exceeded.

    Each strategy implements a different approach:
    - DropOldestStrategy: drops oldest non-system messages until under budget
    - SummarizeStrategy: summarizes oldest messages via LLM
    - TruncateToolResultsStrategy: truncates large tool results
    """

    @property
    def name(self) -> str:
        """Human-readable name for this strategy."""

    async def compact(
        self,
        conversation: Any,
        provider: Any = None,
        token_budget: int | None = None,
    ) -> ContextStatus:
        """Compact the conversation to fit within the token budget.

        Args:
            conversation: The conversation object with messages to compact.
            provider: Optional LLM provider for summarization strategies.
            token_budget: Maximum token count after compaction.

        Returns:
            ContextStatus indicating the result of compaction.
        """


class ContextManagerProtocol:
    """
    Tracks token usage, enforces budget, applies compaction.

    This is the only Runtime module that knows about token counting.
    It delegates to TokenBudget, ContextWindow, and Compactor from
    the existing aios.context package (or replaces them later).
    """

    async def estimate_tokens(self, conversation: Any) -> int:
        """Estimate the token count for a conversation."""

    async def manage(self, conversation: Any, provider: Any) -> ContextStatus:
        """Check token usage against budget. Apply compaction if over threshold."""

    def set_budget(self, limit: int) -> None:
        """Set the token budget limit."""

    def set_model(self, model_name: str) -> None:
        """Set the model name for accurate token counting."""

    def set_compaction_strategy(self, strategy: CompactionStrategy) -> None:
        """Set the compaction strategy to use when budget is exceeded."""
