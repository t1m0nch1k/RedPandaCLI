from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from aios.runtime.models import Event, EventHandler


class EventBusProtocol:
    """
    Typed asynchronous pub/sub for runtime-internal and cross-layer
    communication. Events are fire-and-forget — subscribers must not
    block the emitter.
    """

    async def emit(self, event: Event) -> None:
        """Publish an event to all matching subscribers."""

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> Callable[[], None]:
        """Register a handler for an event type. Returns an unregister callable."""

    def subscribe_all(
        self,
        handler: EventHandler,
    ) -> Callable[[], None]:
        """Register a handler for all event types. Returns an unregister callable."""


class Events:
    """Canonical event type registry — the primary inter-module communication contract."""

    @dataclass
    class SessionStart(Event):
        session_id: str = ""

    @dataclass
    class SessionEnd(Event):
        session_id: str = ""
        total_tokens: int = 0
        total_cost: float = 0.0

    @dataclass
    class RuntimeStarted(Event):
        config_snapshot: dict = field(default_factory=dict)

    @dataclass
    class RuntimeStopped(Event):
        reason: str = ""

    @dataclass
    class StateChange(Event):
        old_state: str = ""
        new_state: str = ""

    @dataclass
    class PlanCreated(Event):
        plan_id: str = ""
        goal: str = ""
        step_count: int = 0

    @dataclass
    class PlanApproved(Event):
        plan_id: str = ""

    @dataclass
    class PlanRejected(Event):
        plan_id: str = ""
        reason: str = ""

    @dataclass
    class StepStarted(Event):
        plan_id: str = ""
        step_id: str = ""
        tool_name: str | None = None

    @dataclass
    class StepCompleted(Event):
        plan_id: str = ""
        step_id: str = ""
        success: bool = True

    @dataclass
    class StepFailed(Event):
        plan_id: str = ""
        step_id: str = ""
        error: str = ""

    @dataclass
    class ExecutionComplete(Event):
        plan_id: str | None = None
        success: bool = True
        iterations: int = 0

    @dataclass
    class ExecutionCancelled(Event):
        reason: str = ""

    @dataclass
    class ToolExecution(Event):
        tool_name: str = ""
        args: dict = field(default_factory=dict)
        result: Any = None
        duration_ms: float = 0.0
        permission: str = "allowed"

    @dataclass
    class PermissionRequired(Event):
        tool_name: str = ""
        args: dict = field(default_factory=dict)
        decision: str = ""

    @dataclass
    class ModelCall(Event):
        provider: str = ""
        model: str = ""
        input_tokens: int = 0
        output_tokens: int = 0
        duration_ms: float = 0.0
        cost: float = 0.0

    @dataclass
    class ProviderFallback(Event):
        failed_provider: str = ""
        fallback_provider: str = ""
        reason: str = ""

    @dataclass
    class ProviderSelected(Event):
        provider_name: str = ""
        model_name: str = ""
        strategy: str = ""
        estimated_cost: float = 0.0

    @dataclass
    class ProviderRejected(Event):
        provider_name: str = ""
        model_name: str = ""
        reason: str = ""

    @dataclass
    class ProviderRecovered(Event):
        provider_name: str = ""
        model_name: str = ""
        consecutive_failures: int = 0

    @dataclass
    class ProviderHealthChanged(Event):
        provider_name: str = ""
        model_name: str = ""
        was_healthy: bool = True
        is_healthy: bool = True
        consecutive_failures: int = 0

    @dataclass
    class CapabilityMismatch(Event):
        requested_capabilities: list[str] = field(default_factory=list)
        available_models: int = 0

    @dataclass
    class RoutingDecision(Event):
        requested_capabilities: list[str] = field(default_factory=list)
        candidates_count: int = 0
        selected_provider: str = ""
        selected_model: str = ""
        strategy: str = ""
        duration_ms: float = 0.0

    @dataclass
    class IntentClassified(Event):
        raw_text: str = ""
        category: str = ""
        confidence: float = 0.0
        stage: str = ""

    @dataclass
    class MissionProgress(Event):
        mission_id: str = ""
        step_id: str = ""
        status: str = ""

    @dataclass
    class MissionPaused(Event):
        mission_id: str = ""
        reason: str = ""

    @dataclass
    class MissionResumed(Event):
        mission_id: str = ""

    @dataclass
    class MissionComplete(Event):
        mission_id: str = ""
        success: bool = True
        total_steps: int = 0
        duration_ms: float = 0.0

    @dataclass
    class MissionFailed(Event):
        mission_id: str = ""
        error: str = ""

    @dataclass
    class SubAgentSpawned(Event):
        sub_agent_id: str = ""
        mission_id: str = ""
        task_summary: str = ""

    @dataclass
    class IndexBuilt(Event):
        duration_ms: float = 0.0
        symbols_found: int = 0
        files_scanned: int = 0

    @dataclass
    class FileModified(Event):
        path: str = ""
        change_type: str = ""

    @dataclass
    class FactAdded(Event):
        source: str = ""
        fact_preview: str = ""

    # ── Permission / Audit ──────────────────────────────────────────
    @dataclass
    class PermissionAudit(Event):
        tool_name: str = ""
        risk_level: str = ""
        decision: str = ""
        policy_name: str = ""
        reason: str = ""
        user_confirmed: bool = False

    @dataclass
    class Error(Event):
        module: str = ""
        exception: str = ""
        recoverable: bool = True
