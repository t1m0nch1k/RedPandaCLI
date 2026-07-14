from __future__ import annotations

from collections.abc import Sequence

from aios.runtime.models import HealthRecord


class ProviderHealthProtocol:
    """
    Tracks runtime health of provider endpoints.

    Monitors success/failure counts, latency percentiles, and
    consecutive failures. Used by ProviderRouter to exclude
    unhealthy providers from selection and by monitoring/alerting
    layers via EventBus.
    """

    async def record_success(
        self,
        provider_name: str,
        model_name: str,
        latency_ms: float,
    ) -> None:
        """Record a successful provider call with observed latency."""

    async def record_failure(
        self,
        provider_name: str,
        model_name: str,
        error: str,
    ) -> None:
        """Record a provider failure with error details."""

    async def is_healthy(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> bool:
        """Return True if the provider (or provider/model combo) is healthy."""

    async def get_status(
        self,
        provider_name: str,
        model_name: str | None = None,
    ) -> HealthRecord | None:
        """Return the current health record for a provider or provider/model."""

    async def get_unhealthy(self) -> list[HealthRecord]:
        """Return all unhealthy provider/model combinations."""

    async def get_all_statuses(self) -> Sequence[HealthRecord]:
        """Return health records for all tracked provider/model combinations."""
