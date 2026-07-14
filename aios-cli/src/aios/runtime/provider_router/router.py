from __future__ import annotations

import time
from typing import Any

from aios.runtime.capability_registry.base import CapabilityRegistryProtocol
from aios.runtime.event_bus.base import EventBusProtocol, Events
from aios.runtime.models import (
    ProviderSelection,
    RoutingConstraints,
    RoutingStrategy,
    TaskDescriptor,
)
from aios.runtime.provider_health.base import ProviderHealthProtocol
from aios.runtime.provider_metrics.base import ProviderMetricsProtocol


class NoopEventBus:
    async def emit(self, event) -> None: ...


class NoSuitableProvider(Exception):
    """Raised when no provider can satisfy the requested capabilities."""


class ProviderRouter:
    """
    Thin orchestration layer for provider/model selection.

    Owns zero capability data, health state, or metrics.
    Delegates to:
      1. CapabilityRegistry — find models matching capabilities
      2. ProviderHealth     — filter out unhealthy providers
      3. ProviderMetrics    — rank candidates by cost/latency

    Every decision emits structured events for observability.
    """

    def __init__(
        self,
        capability_registry: CapabilityRegistryProtocol,
        provider_health: ProviderHealthProtocol,
        provider_metrics: ProviderMetricsProtocol,
        event_bus: EventBusProtocol | None = None,
    ) -> None:
        self._capabilities = capability_registry
        self._health = provider_health
        self._metrics = provider_metrics
        self._event_bus: EventBusProtocol = event_bus or NoopEventBus()
        self._strategy = RoutingStrategy.CAPABILITY_FIRST
        self._providers: dict[str, Any] = {}
        self._model_providers: dict[str, list[str]] = {}

    async def select(
        self,
        capabilities: set[str],
        constraints: RoutingConstraints | None = None,
    ) -> ProviderSelection:
        start = time.time()
        constraints = constraints or RoutingConstraints()

        models = await self._capabilities.list_models_with(capabilities)
        if not models:
            await self._event_bus.emit(
                Events.CapabilityMismatch(
                    requested_capabilities=list(capabilities),
                    available_models=len(self._capabilities.list_all_models()),
                )
            )
            raise NoSuitableProvider(f"No models match capabilities: {capabilities}")

        candidates: list[tuple[str, str, str, float]] = []
        for model in models:
            for provider_name in self._model_providers.get(model, []):
                is_healthy = await self._health.is_healthy(provider_name, model)
                if not is_healthy:
                    await self._event_bus.emit(
                        Events.ProviderRejected(
                            provider_name=provider_name,
                            model_name=model,
                            reason="unhealthy",
                        )
                    )
                    continue
                if constraints.preferred_provider and provider_name != constraints.preferred_provider:
                    await self._event_bus.emit(
                        Events.ProviderRejected(
                            provider_name=provider_name,
                            model_name=model,
                            reason="not_preferred",
                        )
                    )
                    continue
                stats = await self._metrics.get_stats(provider_name, model)
                cost = stats.total_cost if stats else 0.0
                candidates.append((provider_name, model, provider_name, cost))

        if not candidates:
            raise NoSuitableProvider("No healthy providers available for matching models")

        selected = self._rank(candidates, constraints)
        provider_name, model_name, _, estimated_cost = selected
        provider = self._providers[provider_name]

        elapsed = (time.time() - start) * 1000
        await self._event_bus.emit(
            Events.ProviderSelected(
                provider_name=provider_name,
                model_name=model_name,
                strategy=self._strategy.value,
                estimated_cost=estimated_cost,
            )
        )
        await self._event_bus.emit(
            Events.RoutingDecision(
                requested_capabilities=list(capabilities),
                candidates_count=len(candidates),
                selected_provider=provider_name,
                selected_model=model_name,
                strategy=self._strategy.value,
                duration_ms=elapsed,
            )
        )

        return ProviderSelection(
            provider_name=provider_name,
            model_name=model_name,
            provider=provider,
        )

    async def fallback(
        self,
        failed_provider: str,
        task: TaskDescriptor,
    ) -> ProviderSelection:
        models = await self._capabilities.list_models_with(task.capabilities)
        candidates: list[tuple[str, str, str, float]] = []
        for model in models:
            for provider_name in self._model_providers.get(model, []):
                if provider_name == failed_provider:
                    continue
                is_healthy = await self._health.is_healthy(provider_name, model)
                if not is_healthy:
                    continue
                stats = await self._metrics.get_stats(provider_name, model)
                cost = stats.total_cost if stats else 0.0
                candidates.append((provider_name, model, provider_name, cost))

        if not candidates:
            raise NoSuitableProvider("No fallback candidates available")

        selected = self._rank(candidates, RoutingConstraints())
        provider_name, model_name, _, estimated_cost = selected
        provider = self._providers[provider_name]

        await self._event_bus.emit(
            Events.ProviderFallback(
                failed_provider=failed_provider,
                fallback_provider=provider_name,
                reason="provider_failure",
            )
        )

        return ProviderSelection(
            provider_name=provider_name,
            model_name=model_name,
            provider=provider,
        )

    def register_provider(
        self,
        name: str,
        provider: Any,
        model_names: list[str],
    ) -> None:
        self._providers[name] = provider
        for model in model_names:
            if model not in self._model_providers:
                self._model_providers[model] = []
            if name not in self._model_providers[model]:
                self._model_providers[model].append(name)

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        self._strategy = strategy

    def _rank(
        self,
        candidates: list[tuple[str, str, str, float]],
        constraints: RoutingConstraints,
    ) -> tuple[str, str, str, float]:
        if self._strategy == RoutingStrategy.COST_FIRST:
            candidates.sort(key=lambda c: c[3])
        elif self._strategy == RoutingStrategy.LATENCY_FIRST:
            candidates.sort(key=lambda c: c[3])
        return candidates[0]
