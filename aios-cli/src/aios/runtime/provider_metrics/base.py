from __future__ import annotations

from collections.abc import Sequence

from aios.runtime.models import ProviderStats


class ProviderMetricsProtocol:
    """
    Exposes cost, token usage, and performance statistics for provider/model
    combinations.

    This is an observation-only service — stats are accumulated from
    EventBus subscriptions (ModelCall events). ProviderRouter queries
    these stats for cost-first and latency-first routing strategies.
    """

    async def record_call(
        self,
        provider_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        duration_ms: float,
    ) -> None:
        """Record a provider call with token usage, cost, and duration."""

    async def get_stats(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> ProviderStats | None:
        """Return aggregate stats for a provider or provider/model combo."""

    async def get_all_stats(self) -> Sequence[ProviderStats]:
        """Return stats for all tracked provider/model combinations."""

    async def total_cost(self) -> float:
        """Return the cumulative cost across all tracked calls."""

    async def total_tokens(self) -> int:
        """Return the cumulative token count across all tracked calls."""

    async def top_by_cost(self, limit: int = 10) -> list[ProviderStats]:
        """Return the top N most expensive provider/model combinations."""

    async def reset(self) -> None:
        """Reset all accumulated metrics."""
