from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from aios.runtime.event_bus.base import Events
from aios.runtime.event_bus.bus import EventBus
from aios.runtime.models import AgentState, Event
from aios.runtime.runtime import Runtime, RuntimeConfig
from aios.runtime.state_machine.base import StateTransitionError
from aios.runtime.state_machine.machine import StateMachine

# ── EventBus Tests ─────────────────────────────────────────────────────────


class TestEventBus:
    async def test_emit_and_subscribe(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(Events.SessionStart, handler)
        event = Events.SessionStart(source="test", session_id="sess-1")
        await bus.emit(event)
        assert len(received) == 1
        assert received[0].session_id == "sess-1"

    async def test_multiple_subscribers(self) -> None:
        bus = EventBus()
        results: list[int] = []

        async def h1(event: Event) -> None:
            results.append(1)

        async def h2(event: Event) -> None:
            results.append(2)

        bus.subscribe(Events.StateChange, h1)
        bus.subscribe(Events.StateChange, h2)
        await bus.emit(Events.StateChange(source="test"))
        assert sorted(results) == [1, 2]

    async def test_unsubscribe(self) -> None:
        bus = EventBus()
        results: list[int] = []

        async def handler(event: Event) -> None:
            results.append(1)

        unsub = bus.subscribe(Events.Error, handler)
        await bus.emit(Events.Error(source="test", module="x", exception="e"))
        assert len(results) == 1

        unsub()
        await bus.emit(Events.Error(source="test", module="x", exception="e"))
        assert len(results) == 1

    async def test_subscribe_all(self) -> None:
        bus = EventBus()
        received: list[str] = []

        async def handler(event: Event) -> None:
            received.append(type(event).__name__)

        bus.subscribe_all(handler)
        await bus.emit(Events.SessionStart(source="test"))
        await bus.emit(Events.Error(source="test", module="x", exception="e"))
        assert "SessionStart" in received
        assert "Error" in received

    async def test_subscribe_all_unsubscribe(self) -> None:
        bus = EventBus()
        results: list[int] = []

        async def handler(event: Event) -> None:
            results.append(1)

        unsub = bus.subscribe_all(handler)
        await bus.emit(Events.SessionStart(source="test"))
        assert len(results) == 1

        unsub()
        await bus.emit(Events.SessionStart(source="test"))
        assert len(results) == 1

    async def test_handler_error_is_caught(self) -> None:
        bus = EventBus()

        async def failing_handler(event: Event) -> None:
            raise ValueError("test error")

        async def good_handler(event: Event) -> None:
            pass

        bus.subscribe(Events.Error, failing_handler)
        bus.subscribe(Events.Error, good_handler)
        # Should not raise — errors are logged, not propagated
        await bus.emit(Events.Error(source="test", module="x", exception="e"))

    async def test_type_filtering(self) -> None:
        bus = EventBus()
        received: list[str] = []

        async def handler(event: Event) -> None:
            received.append(type(event).__name__)

        bus.subscribe(Events.SessionStart, handler)
        await bus.emit(Events.Error(source="test", module="x", exception="e"))
        assert len(received) == 0
        await bus.emit(Events.SessionStart(source="test"))
        assert len(received) == 1

    async def test_concurrent_emit(self) -> None:
        bus = EventBus()
        results: list[int] = []

        async def handler(event: Event) -> None:
            results.append(1)
            await asyncio.sleep(0.01)

        bus.subscribe(Events.StateChange, handler)
        await asyncio.gather(
            bus.emit(Events.StateChange(source="a")),
            bus.emit(Events.StateChange(source="b")),
        )
        assert len(results) == 2


# ── StateMachine Tests ──────────────────────────────────────────────────────


class TestStateMachine:
    async def test_initial_state(self) -> None:
        sm = StateMachine()
        assert sm.current == AgentState.IDLE

    async def test_valid_transition(self) -> None:
        sm = StateMachine()
        result = await sm.transition(AgentState.PLANNING)
        assert result is True
        assert sm.current == AgentState.PLANNING

    async def test_invalid_transition_raises_error(self) -> None:
        sm = StateMachine()
        with pytest.raises(StateTransitionError) as exc:
            await sm.transition(AgentState.COMPLETED)
        assert "Cannot transition" in str(exc.value)

    async def test_can_transition(self) -> None:
        sm = StateMachine()
        assert sm.can_transition(AgentState.PLANNING) is True
        assert sm.can_transition(AgentState.COMPLETED) is False

    async def test_reset(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.PLANNING)
        assert sm.current == AgentState.PLANNING
        sm.reset()
        assert sm.current == AgentState.IDLE

    async def test_full_execution_cycle(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.PLANNING)
        await sm.transition(AgentState.WAITING_APPROVAL)
        await sm.transition(AgentState.EXECUTING)
        await sm.transition(AgentState.RUNNING_TOOL)
        await sm.transition(AgentState.OBSERVING)
        await sm.transition(AgentState.REVIEWING)
        await sm.transition(AgentState.COMPLETED)
        assert sm.current == AgentState.COMPLETED

    async def test_error_path(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.EXECUTING)
        await sm.transition(AgentState.RUNNING_TOOL)
        await sm.transition(AgentState.FAILED)
        assert sm.current == AgentState.FAILED
        await sm.transition(AgentState.IDLE)
        assert sm.current == AgentState.IDLE

    async def test_interrupt_from_any_state(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.PLANNING)
        await sm.transition(AgentState.INTERRUPTED)
        assert sm.current == AgentState.INTERRUPTED
        sm.reset()
        assert sm.current == AgentState.IDLE

    async def test_on_transition_callback(self) -> None:
        sm = StateMachine()
        transitions: list[tuple[AgentState, AgentState]] = []

        async def callback(old: AgentState, new: AgentState) -> None:
            transitions.append((old, new))

        unsub = sm.on_transition(callback)
        await sm.transition(AgentState.PLANNING)
        assert len(transitions) == 1
        assert transitions[0] == (AgentState.IDLE, AgentState.PLANNING)

        unsub()
        await sm.transition(AgentState.WAITING_APPROVAL)
        assert len(transitions) == 1

    async def test_on_transition_multiple_callbacks(self) -> None:
        sm = StateMachine()
        results: list[int] = []

        async def cb1(old: AgentState, new: AgentState) -> None:
            results.append(1)

        async def cb2(old: AgentState, new: AgentState) -> None:
            results.append(2)

        sm.on_transition(cb1)
        sm.on_transition(cb2)
        await sm.transition(AgentState.PLANNING)
        assert sorted(results) == [1, 2]

    async def test_callback_error_is_caught(self) -> None:
        sm = StateMachine()

        async def failing(old: AgentState, new: AgentState) -> None:
            raise ValueError("callback error")

        sm.on_transition(failing)
        await sm.transition(AgentState.PLANNING)
        assert sm.current == AgentState.PLANNING

    async def test_state_change_event_emitted(self) -> None:
        bus = EventBus()
        sm = StateMachine(event_bus=bus)
        received: list[str] = []

        async def handler(event: Event) -> None:
            received.append(event.old_state)
            received.append(event.new_state)

        bus.subscribe(Events.StateChange, handler)
        await sm.transition(AgentState.PLANNING)
        assert "idle" in received
        assert "planning" in received

    async def test_completed_can_go_to_idle(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.EXECUTING)
        await sm.transition(AgentState.COMPLETED)
        await sm.transition(AgentState.IDLE)
        assert sm.current == AgentState.IDLE

    async def test_planning_to_executing_direct(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.PLANNING)
        await sm.transition(AgentState.EXECUTING)
        assert sm.current == AgentState.EXECUTING

    async def test_interrupted_to_idle(self) -> None:
        sm = StateMachine()
        await sm.transition(AgentState.EXECUTING)
        await sm.transition(AgentState.INTERRUPTED)
        await sm.transition(AgentState.IDLE)
        assert sm.current == AgentState.IDLE


# ── Runtime Facade Tests ────────────────────────────────────────────────────


class TestRuntime:
    async def test_construct(self) -> None:
        runtime = Runtime(RuntimeConfig())
        assert runtime._initialized is False

    async def test_start_stop(self) -> None:
        runtime = Runtime(RuntimeConfig())
        await runtime.start()
        assert runtime._initialized is True
        await runtime.stop()
        assert runtime._initialized is False

    async def test_start_idempotent(self) -> None:
        runtime = Runtime(RuntimeConfig())
        await runtime.start()
        await runtime.start()
        assert runtime._initialized is True

    async def test_stop_idempotent(self) -> None:
        runtime = Runtime(RuntimeConfig())
        await runtime.stop()
        assert runtime._initialized is False

    async def test_context_manager(self) -> None:
        async with Runtime(RuntimeConfig()) as runtime:
            assert runtime._initialized is True
        assert runtime._initialized is False

    async def test_event_bus_property(self) -> None:
        runtime = Runtime(RuntimeConfig())
        assert runtime.event_bus is not None

    async def test_state_machine_property(self) -> None:
        runtime = Runtime(RuntimeConfig())
        assert runtime.state_machine is not None

    async def test_state_machine_bus_integration(self) -> None:
        runtime = Runtime(RuntimeConfig())
        await runtime.start()
        sm = runtime.state_machine
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        runtime.event_bus.subscribe(Events.StateChange, handler)
        await sm.transition(AgentState.PLANNING)
        assert len(received) == 1
        assert received[0].new_state == "planning"
        await runtime.stop()

    async def test_config_with_workspace(self) -> None:
        config = RuntimeConfig(workspace_root=Path("/tmp/test"), permission_profile="restrictive")
        runtime = Runtime(config)
        assert runtime._config.workspace_root == Path("/tmp/test")
        assert runtime._config.permission_profile == "restrictive"

    async def test_unimplemented_properties_raise(self) -> None:
        runtime = Runtime(RuntimeConfig())
        unimplemented = [
            "tool_executor",
            "permission_gate",
            "provider_router",
            "workspace_knowledge",
            "mission_engine",
            "intent_engine",
            "memory_orchestrator",
            "prompt_assembler",
        ]
        for name in unimplemented:
            with pytest.raises(NotImplementedError):
                getattr(runtime, name)
                
        requires_provider = [
            "planner",
            "executor",
            "context_manager",
        ]
        for name in requires_provider:
            with pytest.raises(RuntimeError):
                getattr(runtime, name)

    async def test_unimplemented_methods_raise(self) -> None:
        runtime = Runtime(RuntimeConfig())
        with pytest.raises(RuntimeError):
            await runtime.chat(None)
        with pytest.raises(NotImplementedError):
            await runtime.execute_plan(None, None)
        with pytest.raises(NotImplementedError):
            await runtime.classify_intent("test")
        assert hasattr(runtime, "run_mission")
        assert callable(runtime.run_mission)

    async def test_config_snapshot(self) -> None:
        config = RuntimeConfig(
            workspace_root=Path("/project"),
            permission_profile="strict",
            max_iterations=50,
            token_limit=64_000,
        )
        runtime = Runtime(config)
        snapshot = runtime._snapshot_config()
        assert snapshot["workspace_root"] == str(Path("/project"))
        assert snapshot["permission_profile"] == "strict"
        assert snapshot["max_iterations"] == 50
        assert snapshot["token_limit"] == 64_000

    async def test_runtime_start_emits_event(self) -> None:
        runtime = Runtime(RuntimeConfig())
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        runtime.event_bus.subscribe(Events.RuntimeStarted, handler)
        await runtime.start()
        assert len(received) == 1
        assert received[0].source == "runtime"

    async def test_runtime_stop_emits_event(self) -> None:
        runtime = Runtime(RuntimeConfig())
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        runtime.event_bus.subscribe(Events.RuntimeStopped, handler)
        await runtime.start()
        await runtime.stop()
        assert len(received) == 1
        assert received[0].reason == "shutdown"
