from __future__ import annotations

import time
from collections.abc import Sequence

from aios.runtime.event_bus.base import EventBusProtocol
from aios.runtime.models import ProviderStats


class NoopEventBus:
    async def emit(self, event) -> None: ...


class ProviderMetrics:
    """
    Observability layer for provider cost, token usage, and performance.

    Stats are accumulated from record_call() invocations (or EventBus
    ModelCall subscriptions). Designed to power Desktop UI dashboards
    showing token usage, request duration, provider distribution, and
    execution timelines.
    """

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._stats: dict[str, ProviderStats] = {}
        self._event_bus: EventBusProtocol = event_bus or NoopEventBus()

    async def record_call(
        self,
        provider_name: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        duration_ms: float,
    ) -> None:
        key = self._key(provider_name, model_name)
        stats = self._stats.get(key)
        if stats is None:
            stats = ProviderStats(
                provider_name=provider_name,
                model_name=model_name,
                total_requests=1,
                total_cost=cost,
                total_input_tokens=input_tokens,
                total_output_tokens=output_tokens,
                avg_duration_ms=duration_ms,
                min_duration_ms=duration_ms,
                max_duration_ms=duration_ms,
                last_request_time=time.time(),
            )
            stats.token_usage_history.append((time.time(), input_tokens, output_tokens))
            self._stats[key] = stats
            return

        stats.total_requests += 1
        stats.total_cost += cost
        stats.total_input_tokens += input_tokens
        stats.total_output_tokens += output_tokens
        stats.avg_duration_ms = (
            stats.avg_duration_ms * (stats.total_requests - 1) + duration_ms
        ) / stats.total_requests
        stats.min_duration_ms = min(stats.min_duration_ms, duration_ms)
        stats.max_duration_ms = max(stats.max_duration_ms, duration_ms)
        stats.last_request_time = time.time()
        if len(stats.token_usage_history) > 1000:
            stats.token_usage_history = stats.token_usage_history[-500:]
        stats.token_usage_history.append((time.time(), input_tokens, output_tokens))

    async def get_stats(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> ProviderStats | None:
        if model_name:
            return self._stats.get(self._key(provider_name, model_name))
        prefix = f"{provider_name}:"
        matching = [s for k, s in self._stats.items() if k.startswith(prefix)]
        if not matching:
            return None
        combined = ProviderStats(
            provider_name=provider_name,
            model_name="*",
            total_cost=sum(s.total_cost for s in matching),
            total_input_tokens=sum(s.total_input_tokens for s in matching),
            total_output_tokens=sum(s.total_output_tokens for s in matching),
            total_requests=sum(s.total_requests for s in matching),
            avg_duration_ms=(
                sum(s.avg_duration_ms * s.total_requests for s in matching)
                / max(sum(s.total_requests for s in matching), 1)
            ),
            min_duration_ms=min(s.min_duration_ms for s in matching),
            max_duration_ms=max(s.max_duration_ms for s in matching),
            last_request_time=max(s.last_request_time for s in matching),
        )
        return combined

    async def get_all_stats(self) -> Sequence[ProviderStats]:
        return list(self._stats.values())

    async def total_cost(self) -> float:
        return sum(s.total_cost for s in self._stats.values())

    async def total_tokens(self) -> int:
        return sum(s.total_input_tokens + s.total_output_tokens for s in self._stats.values())

    async def top_by_cost(self, limit: int = 10) -> list[ProviderStats]:
        sorted_stats = sorted(
            self._stats.values(),
            key=lambda s: s.total_cost,
            reverse=True,
        )
        return sorted_stats[:limit]

    async def reset(self) -> None:
        self._stats.clear()

    def _key(self, provider_name: str, model_name: str) -> str:
        return f"{provider_name}:{model_name}"
