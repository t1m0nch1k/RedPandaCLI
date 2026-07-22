from __future__ import annotations

import pytest
from aios.runtime.capability_registry.registry import CapabilityRegistry
from aios.runtime.event_bus.base import Events
from aios.runtime.event_bus.bus import EventBus
from aios.runtime.models import (
    ModelCapabilities,
    PermissionAuditRecord,
    PermissionDecision,
    ProviderSelection,
    RiskLevel,
    RoutingConstraints,
    RoutingStrategy,
    TaskDescriptor,
)
from aios.runtime.permission_gate.gate import PermissionGate, PolicyProtocol
from aios.runtime.provider_health.health import ProviderHealth
from aios.runtime.provider_metrics.metrics import ProviderMetrics
from aios.runtime.provider_router.router import NoSuitableProvider, ProviderRouter

# ── CapabilityRegistry Tests ────────────────────────────────────────────────


class TestCapabilityRegistry:
    async def test_register_and_get(self) -> None:
        reg = CapabilityRegistry()
        caps = ModelCapabilities(model_name="gpt-4o", supports_vision=True, supports_tools=True)
        reg.register_model(caps)
        result = await reg.get_capabilities("gpt-4o")
        assert result is not None
        assert result.model_name == "gpt-4o"
        assert result.supports_vision is True
        assert result.supports_tools is True

    async def test_get_unknown_model(self) -> None:
        reg = CapabilityRegistry()
        result = await reg.get_capabilities("unknown")
        assert result is None

    async def test_list_models_with_capability(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="gpt-4o", supports_vision=True, supports_tools=True))
        reg.register_model(ModelCapabilities(model_name="gpt-4o-mini", supports_tools=True))
        reg.register_model(ModelCapabilities(model_name="dall-e-3", supports_vision=False))
        result = await reg.list_models_with({"tools"})
        assert "gpt-4o" in result
        assert "gpt-4o-mini" in result
        assert "dall-e-3" not in result

    async def test_list_models_with_multiple_capabilities(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="gpt-4o", supports_vision=True, supports_tools=True))
        reg.register_model(ModelCapabilities(model_name="gpt-4o-mini", supports_tools=True))
        result = await reg.list_models_with({"vision", "tools"})
        assert result == ["gpt-4o"]

    async def test_supports_capability(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="gpt-4o", supports_streaming=True))
        assert await reg.supports("gpt-4o", "streaming") is True
        assert await reg.supports("gpt-4o", "vision") is False

    async def test_supports_unknown_model(self) -> None:
        reg = CapabilityRegistry()
        assert await reg.supports("unknown", "streaming") is False

    async def test_unregister_model(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="gpt-4o"))
        assert len(reg.list_all_models()) == 1
        reg.unregister_model("gpt-4o")
        assert len(reg.list_all_models()) == 0

    async def test_list_all_models(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="a"))
        reg.register_model(ModelCapabilities(model_name="b"))
        models = reg.list_all_models()
        assert len(models) == 2
        assert "a" in models
        assert "b" in models

    async def test_extensible_capability(self) -> None:
        reg = CapabilityRegistry()
        caps = ModelCapabilities(
            model_name="gpt-5",
            extras={"reasoning_level": "advanced", "tool_parallelism": 5},
        )
        reg.register_model(caps)
        result = await reg.get_capabilities("gpt-5")
        assert result is not None
        assert result.get("reasoning_level") == "advanced"
        assert result.get("tool_parallelism") == 5
        assert result.get("nonexistent", "fallback") == "fallback"

    async def test_extensible_capability_listing(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(
            ModelCapabilities(
                model_name="claude-4",
                extras={"thinking_tokens": 16000},
            )
        )
        models = await reg.list_models_with({"thinking_tokens"})
        assert models == ["claude-4"]


# ── ProviderHealth Tests ────────────────────────────────────────────────────


class TestProviderHealth:
    async def test_initial_state_healthy(self) -> None:
        health = ProviderHealth()
        assert await health.is_healthy("openai", "gpt-4o") is True

    async def test_record_success(self) -> None:
        health = ProviderHealth()
        await health.record_success("openai", "gpt-4o", 100.0)
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.success_count == 1
        assert status.total_calls == 1
        assert status.failure_count == 0
        assert status.healthy is True

    async def test_record_failure(self) -> None:
        health = ProviderHealth()
        await health.record_failure("openai", "gpt-4o", "server error")
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.failure_count == 1
        assert status.consecutive_failures == 1

    async def test_unhealthy_after_three_failures(self) -> None:
        health = ProviderHealth()
        for _ in range(3):
            await health.record_failure("openai", "gpt-4o", "error")
        assert await health.is_healthy("openai", "gpt-4o") is False

    async def test_recovery_after_success(self) -> None:
        health = ProviderHealth()
        for _ in range(3):
            await health.record_failure("openai", "gpt-4o", "error")
        assert await health.is_healthy("openai", "gpt-4o") is False
        await health.record_success("openai", "gpt-4o", 50.0)
        assert await health.is_healthy("openai", "gpt-4o") is True

    async def test_get_unhealthy(self) -> None:
        health = ProviderHealth()
        await health.record_success("openai", "gpt-4o", 50.0)
        for _ in range(3):
            await health.record_failure("azure", "gpt-4o", "error")
        unhealthy = await health.get_unhealthy()
        assert len(unhealthy) == 1
        assert unhealthy[0].provider_name == "azure"

    async def test_get_all_statuses(self) -> None:
        health = ProviderHealth()
        await health.record_success("a", "m1", 10.0)
        await health.record_success("b", "m2", 20.0)
        statuses = await health.get_all_statuses()
        assert len(statuses) == 2

    async def test_latency_tracking(self) -> None:
        health = ProviderHealth()
        for lat in [100, 200, 150, 300, 250]:
            await health.record_success("openai", "gpt-4o", float(lat))
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.avg_latency_ms > 0
        assert status.p50_latency_ms > 0

    async def test_timeout_detection(self) -> None:
        health = ProviderHealth()
        await health.record_failure("openai", "gpt-4o", "timeout error")
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.timeout_count == 1

    async def test_rate_limit_detection(self) -> None:
        health = ProviderHealth()
        await health.record_failure("openai", "gpt-4o", "rate limit exceeded")
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.rate_limit_count == 1

    async def test_availability_calculation(self) -> None:
        health = ProviderHealth()
        await health.record_success("openai", "gpt-4o", 50.0)
        await health.record_failure("openai", "gpt-4o", "error")
        status = await health.get_status("openai", "gpt-4o")
        assert status is not None
        assert status.availability == 0.5

    async def test_health_event_emitted(self) -> None:
        bus = EventBus()
        health = ProviderHealth(event_bus=bus)
        events: list = []

        async def handler(event) -> None:
            events.append(event)

        bus.subscribe_all(handler)
        for _ in range(3):
            await health.record_failure("openai", "gpt-4o", "error")
        assert any(isinstance(e, Events.ProviderHealthChanged) for e in events)

    async def test_recovery_event_emitted(self) -> None:
        bus = EventBus()
        health = ProviderHealth(event_bus=bus)
        for _ in range(3):
            await health.record_failure("openai", "gpt-4o", "error")
        events: list = []

        async def handler(event) -> None:
            events.append(event)

        bus.subscribe_all(handler)
        await health.record_success("openai", "gpt-4o", 50.0)
        assert any(isinstance(e, Events.ProviderRecovered) for e in events)


# ── ProviderMetrics Tests ────────────────────────────────────────────────────


class TestProviderMetrics:
    async def test_record_and_get_stats(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("openai", "gpt-4o", 100, 50, 0.01, 200.0)
        stats = await metrics.get_stats("openai", "gpt-4o")
        assert stats is not None
        assert stats.total_requests == 1
        assert stats.total_cost == 0.01
        assert stats.total_input_tokens == 100
        assert stats.total_output_tokens == 50
        assert stats.provider_name == "openai"
        assert stats.model_name == "gpt-4o"

    async def test_multiple_calls_aggregate(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("openai", "gpt-4o", 100, 50, 0.01, 200.0)
        await metrics.record_call("openai", "gpt-4o", 200, 100, 0.02, 300.0)
        stats = await metrics.get_stats("openai", "gpt-4o")
        assert stats is not None
        assert stats.total_requests == 2
        assert stats.total_cost == 0.03
        assert stats.total_input_tokens == 300
        assert stats.total_output_tokens == 150
        assert stats.avg_duration_ms == 250.0

    async def test_get_unknown_stats(self) -> None:
        metrics = ProviderMetrics()
        result = await metrics.get_stats("unknown", "model")
        assert result is None

    async def test_total_cost(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("a", "m1", 0, 0, 1.0, 0)
        await metrics.record_call("b", "m2", 0, 0, 2.0, 0)
        total = await metrics.total_cost()
        assert total == 3.0

    async def test_total_tokens(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("a", "m1", 100, 50, 0, 0)
        await metrics.record_call("b", "m2", 200, 100, 0, 0)
        total = await metrics.total_tokens()
        assert total == 450

    async def test_top_by_cost(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("cheap", "m1", 0, 0, 1.0, 0)
        await metrics.record_call("expensive", "m2", 0, 0, 100.0, 0)
        top = await metrics.top_by_cost(1)
        assert len(top) == 1
        assert top[0].provider_name == "expensive"

    async def test_reset(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("a", "m1", 0, 0, 1.0, 0)
        await metrics.reset()
        total = await metrics.total_cost()
        assert total == 0.0

    async def test_get_all_stats(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("a", "m1", 0, 0, 1.0, 0)
        await metrics.record_call("b", "m2", 0, 0, 2.0, 0)
        stats = await metrics.get_all_stats()
        assert len(stats) == 2

    async def test_min_max_duration(self) -> None:
        metrics = ProviderMetrics()
        await metrics.record_call("a", "m1", 0, 0, 0, 100.0)
        await metrics.record_call("a", "m1", 0, 0, 0, 500.0)
        stats = await metrics.get_stats("a", "m1")
        assert stats is not None
        assert stats.min_duration_ms == 100.0
        assert stats.max_duration_ms == 500.0


# ── ProviderRouter Tests ────────────────────────────────────────────────────


class TestProviderRouter:
    @pytest.fixture
    def router(self) -> ProviderRouter:
        reg = CapabilityRegistry()
        reg.register_model(
            ModelCapabilities(
                model_name="gpt-4o",
                supports_vision=True,
                supports_tools=True,
                supports_streaming=True,
            )
        )
        reg.register_model(
            ModelCapabilities(
                model_name="gpt-4o-mini",
                supports_tools=True,
            )
        )
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics)
        r.register_provider("openai", object(), ["gpt-4o", "gpt-4o-mini"])
        return r

    async def test_select_by_capability(self, router: ProviderRouter) -> None:
        result = await router.select({"tools"})
        assert isinstance(result, ProviderSelection)
        assert result.provider_name == "openai"
        assert result.model_name in ("gpt-4o", "gpt-4o-mini")

    async def test_select_specific_capability(self, router: ProviderRouter) -> None:
        result = await router.select({"vision", "tools"})
        assert result.model_name == "gpt-4o"

    async def test_select_no_match_raises(self, router: ProviderRouter) -> None:
        with pytest.raises(NoSuitableProvider):
            await router.select({"audio"})

    async def test_select_preferred_provider(self, router: ProviderRouter) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="m1", supports_tools=True))
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics)
        r.register_provider("provider-a", object(), ["m1"])
        r.register_provider("provider-b", object(), ["m1"])
        result = await r.select({"tools"}, RoutingConstraints(preferred_provider="provider-a"))
        assert result.provider_name == "provider-a"

    async def test_fallback(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="m1", supports_tools=True))
        reg.register_model(ModelCapabilities(model_name="m2", supports_tools=True))
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics)
        r.register_provider("primary", object(), ["m1"])
        r.register_provider("backup", object(), ["m2"])
        task = TaskDescriptor(capabilities={"tools"})
        result = await r.fallback("primary", task)
        assert isinstance(result, ProviderSelection)
        assert result.provider_name == "backup"

    async def test_fallback_no_candidates_raises(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="m1", supports_tools=True))
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics)
        r.register_provider("only-one", object(), ["m1"])
        task = TaskDescriptor(capabilities={"tools"})
        with pytest.raises(NoSuitableProvider):
            await r.fallback("only-one", task)

    async def test_unhealthy_provider_excluded(self) -> None:
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="m1", supports_tools=True))
        health = ProviderHealth()
        for _ in range(3):
            await health.record_failure("broken", "m1", "error")
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics)
        r.register_provider("broken", object(), ["m1"])
        with pytest.raises(NoSuitableProvider):
            await r.select({"tools"})

    async def test_set_strategy(self, router: ProviderRouter) -> None:
        router.set_strategy(RoutingStrategy.COST_FIRST)
        result = await router.select({"tools"})
        assert isinstance(result, ProviderSelection)

    async def test_select_emits_events(self) -> None:
        bus = EventBus()
        reg = CapabilityRegistry()
        reg.register_model(ModelCapabilities(model_name="m1", supports_tools=True))
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics, event_bus=bus)
        r.register_provider("test", object(), ["m1"])
        events: list = []

        async def handler(event) -> None:
            events.append(event)

        bus.subscribe_all(handler)
        await r.select({"tools"})
        assert any(isinstance(e, Events.ProviderSelected) for e in events)
        assert any(isinstance(e, Events.RoutingDecision) for e in events)

    async def test_capability_mismatch_emits_event(self) -> None:
        bus = EventBus()
        reg = CapabilityRegistry()
        health = ProviderHealth()
        metrics = ProviderMetrics()
        r = ProviderRouter(reg, health, metrics, event_bus=bus)
        events: list = []

        async def handler(event) -> None:
            events.append(event)

        bus.subscribe_all(handler)
        with pytest.raises(NoSuitableProvider):
            await r.select({"nonexistent"})
        assert any(isinstance(e, Events.CapabilityMismatch) for e in events)


# ── PermissionGate Tests ─────────────────────────────────────────────────────


class TestPermissionGate:
    async def test_check_allows_low_risk(self) -> None:
        gate = PermissionGate()
        result = await gate.check("read_file", {})
        assert result == PermissionDecision.ALLOWED

    async def test_check_requires_confirmation_for_critical(self) -> None:
        gate = PermissionGate()
        result = await gate.check("filesystem_delete", {})
        assert result == PermissionDecision.REQUIRES_CONFIRMATION

    async def test_check_requires_confirmation_for_high_risk(self) -> None:
        gate = PermissionGate()
        result = await gate.check("shell_exec", {})
        assert result == PermissionDecision.REQUIRES_CONFIRMATION

    async def test_remember_allow_caches(self) -> None:
        gate = PermissionGate()
        gate.remember_allow("read_file", {})
        assert await gate.check("read_file", {}) == PermissionDecision.ALLOWED

    async def test_forget_allow_removes_cache(self) -> None:
        gate = PermissionGate()
        gate.remember_allow("read_file", {})
        assert await gate.check("read_file", {}) == PermissionDecision.ALLOWED
        gate.forget_allow("read_file", {})
        result = await gate.check("read_file", {"path": "new"})
        assert result == PermissionDecision.ALLOWED

    async def test_confirm_returns_false_with_no_callback(self) -> None:
        gate = PermissionGate()
        result = await gate.confirm("read_file", {})
        assert result is False

    async def test_audit_log_records_decisions(self) -> None:
        gate = PermissionGate()
        await gate.check("read_file", {})
        await gate.check("filesystem_delete", {})
        log = gate.get_audit_log()
        assert len(log) == 2
        assert isinstance(log[0], PermissionAuditRecord)

    async def test_audit_log_accessible(self) -> None:
        gate = PermissionGate()
        log = gate.get_audit_log()
        assert log == []

    async def test_set_policy(self) -> None:
        gate = PermissionGate()
        policy = PolicyProtocol()
        gate.set_policy(policy)
        assert gate._policy is policy

    async def test_risk_levels(self) -> None:
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    async def test_permission_decision_values(self) -> None:
        assert PermissionDecision.ALLOWED.value == "allowed"
        assert PermissionDecision.DENIED.value == "denied"
        assert PermissionDecision.REQUIRES_CONFIRMATION.value == "requires_confirmation"

    async def test_audit_event_emitted(self) -> None:
        bus = EventBus()
        gate = PermissionGate(event_bus=bus)
        events: list = []

        async def handler(event) -> None:
            events.append(event)

        bus.subscribe_all(handler)
        await gate.check("filesystem_delete", {})
        assert any(isinstance(e, Events.PermissionAudit) for e in events)
