from __future__ import annotations

from typing import Any

from aios.runtime.models import ProviderSelection, RoutingConstraints, RoutingStrategy, TaskDescriptor


class ProviderRouterProtocol:
    """
    Thin orchestration layer for provider/model selection.

    Does NOT own capability data, health tracking, or metrics.
    Delegates to three sub-services:

      1. CapabilityRegistry  — find models matching required capabilities
      2. ProviderHealth      — filter out unhealthy providers
      3. ProviderMetrics     — rank candidates by cost/latency

    Selection strategy is configurable via RoutingStrategy.
    Every routing decision emits structured events for observability.
    """

    async def select(
        self,
        capabilities: set[str],
        constraints: RoutingConstraints | None = None,
    ) -> ProviderSelection:
        """Select the best provider/model matching the required capabilities and constraints."""

    async def fallback(
        self,
        failed_provider: str,
        task: TaskDescriptor,
    ) -> ProviderSelection:
        """Called when a provider call fails. Returns the next best provider with overlapping capabilities."""

    def register_provider(
        self,
        name: str,
        provider: Any,
        model_names: list[str],
    ) -> None:
        """Register a provider that serves the given models."""

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy."""
