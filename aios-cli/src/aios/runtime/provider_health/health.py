from __future__ import annotations

import time
from collections.abc import Sequence

from aios.runtime.event_bus.base import EventBusProtocol, Events
from aios.runtime.models import HealthRecord


class NoopEventBus:
    async def emit(self, event) -> None: ...


class ProviderHealth:
    """
    Tracks runtime health of provider endpoints with predictive metrics.

    Monitors success/failure counts, latency trends, timeout frequency,
    rate limits, and availability. Detects health transitions and emits
    ProviderHealthChanged / ProviderRecovered events.
    """

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._records: dict[str, HealthRecord] = {}
        self._event_bus: EventBusProtocol = event_bus or NoopEventBus()

    async def record_success(
        self,
        provider_name: str,
        model_name: str,
        latency_ms: float,
    ) -> None:
        now = time.time()
        key = self._key(provider_name, model_name)
        record = self._records.setdefault(
            key,
            HealthRecord(provider_name=provider_name, model_name=model_name),
        )

        was_healthy = record.healthy
        was_degraded = record.degraded

        record.success_count += 1
        record.total_calls += 1
        record.last_success = now
        record.consecutive_failures = 0
        self._update_latency(record, latency_ms)

        if was_degraded and record.healthy:
            record.recovery_time_ms = (now - record.degraded_since) * 1000
            record.degraded_since = 0.0
            await self._event_bus.emit(
                Events.ProviderRecovered(
                    provider_name=provider_name,
                    model_name=model_name,
                    consecutive_failures=was_degraded,
                )
            )

        if was_healthy != record.healthy:
            await self._emit_health_change(provider_name, model_name, was_healthy, record)

    async def record_failure(
        self,
        provider_name: str,
        model_name: str,
        error: str,
    ) -> None:
        now = time.time()
        key = self._key(provider_name, model_name)
        record = self._records.setdefault(
            key,
            HealthRecord(provider_name=provider_name, model_name=model_name),
        )

        was_healthy = record.healthy

        record.failure_count += 1
        record.total_calls += 1
        record.last_failure = now
        record.consecutive_failures += 1

        if "timeout" in error.lower():
            record.timeout_count += 1
        if "rate limit" in error.lower():
            record.rate_limit_count += 1

        if was_healthy and not record.healthy:
            record.degraded_since = now

        if was_healthy != record.healthy:
            await self._emit_health_change(provider_name, model_name, was_healthy, record)

    async def is_healthy(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> bool:
        if model_name:
            key = self._key(provider_name, model_name)
            record = self._records.get(key)
            return record.healthy if record else True
        prefix = f"{provider_name}:"
        matching = [r for k, r in self._records.items() if k.startswith(prefix)]
        if not matching:
            return True
        return any(r.healthy for r in matching)

    async def get_status(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> HealthRecord | None:
        if model_name:
            return self._records.get(self._key(provider_name, model_name))
        prefix = f"{provider_name}:"
        matching = [r for k, r in self._records.items() if k.startswith(prefix)]
        if not matching:
            return None
        return matching[-1]

    async def get_unhealthy(self) -> list[HealthRecord]:
        return [r for r in self._records.values() if not r.healthy]

    async def get_all_statuses(self) -> Sequence[HealthRecord]:
        return list(self._records.values())

    def _key(self, provider_name: str, model_name: str) -> str:
        return f"{provider_name}:{model_name}"

    def _update_latency(self, record: HealthRecord, latency_ms: float) -> None:
        total = record.success_count
        record.avg_latency_ms = (record.avg_latency_ms * (total - 1) + latency_ms) / total
        record.last_latencies.append(latency_ms)
        if len(record.last_latencies) > 100:
            record.last_latencies = record.last_latencies[-100:]

        sorted_lats = sorted(record.last_latencies)
        n = len(sorted_lats)
        record.p50_latency_ms = sorted_lats[n // 2] if n else 0.0
        record.p95_latency_ms = sorted_lats[int(n * 0.95)] if n >= 20 else record.avg_latency_ms
        record.p99_latency_ms = sorted_lats[int(n * 0.99)] if n >= 100 else 0.0

        if len(record.last_latencies) >= 5:
            recent = record.last_latencies[-5:]
            older = record.last_latencies[-10:-5] if len(record.last_latencies) >= 10 else record.last_latencies[:5]
            if older:
                record.latency_trend = (sum(recent) / len(recent)) - (sum(older) / len(older))

    async def _emit_health_change(
        self,
        provider_name: str,
        model_name: str,
        was_healthy: bool,
        record: HealthRecord,
    ) -> None:
        await self._event_bus.emit(
            Events.ProviderHealthChanged(
                provider_name=provider_name,
                model_name=model_name,
                was_healthy=was_healthy,
                is_healthy=record.healthy,
                consecutive_failures=record.consecutive_failures,
            )
        )
