from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from aios.runtime.event_bus.base import EventBusProtocol
from aios.runtime.models import TRANSITION_TABLE, AgentState
from aios.runtime.state_machine.base import StateMachineProtocol, StateTransitionError

logger = logging.getLogger(__name__)


class StateMachine(StateMachineProtocol):
    """
    Deterministic finite state machine with 11 states and transitions
    validated against TRANSITION_TABLE.

    On every successful transition, emits a StateChange event via the
    optional EventBus.
    """

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._state: AgentState = AgentState.IDLE
        self._event_bus = event_bus
        self._callbacks: list[Callable[[AgentState, AgentState], Awaitable[None]]] = []

    @property
    def current(self) -> AgentState:
        return self._state

    async def transition(self, target: AgentState) -> bool:
        if not self.can_transition(target):
            raise StateTransitionError(f"Cannot transition from {self._state.value} to {target.value}")

        old_state = self._state
        self._state = target

        if self._event_bus is not None:
            from aios.runtime.event_bus.base import Events

            await self._event_bus.emit(
                Events.StateChange(
                    source="state_machine",
                    old_state=old_state.value,
                    new_state=target.value,
                )
            )

        for callback in self._callbacks:
            try:
                result = callback(old_state, target)
                if isinstance(result, Awaitable):
                    await result
            except Exception:
                logger.exception("State transition callback failed")

        return True

    def can_transition(self, target: AgentState) -> bool:
        return target in TRANSITION_TABLE.get(self._state, set())

    def on_transition(
        self,
        callback: Callable[[AgentState, AgentState], Awaitable[None]],
    ) -> Callable[[], None]:
        self._callbacks.append(callback)

        def unregister() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unregister

    def reset(self) -> None:
        self._state = AgentState.IDLE
