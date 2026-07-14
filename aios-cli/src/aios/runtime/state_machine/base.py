from __future__ import annotations

from collections.abc import Awaitable, Callable

from aios.runtime.models import AgentState


class StateMachineProtocol:
    """
    Deterministic finite state machine for the agent execution cycle.

    Defines 11 states (IDLE, PLANNING, WAITING_APPROVAL, EXECUTING,
    RUNNING_TOOL, OBSERVING, REVIEWING, REPLANNING, COMPLETED, FAILED,
    INTERRUPTED) with transitions validated against TRANSITION_TABLE.
    """

    @property
    def current(self) -> AgentState:
        """Return the current agent state."""

    async def transition(self, target: AgentState) -> bool:
        """
        Transition to target state. Returns True if successful.
        Emits StateChange event on success. Raises StateTransitionError
        on invalid transition.
        """

    def can_transition(self, target: AgentState) -> bool:
        """Check whether the transition to target state is legal."""

    def on_transition(
        self,
        callback: Callable[[AgentState, AgentState], Awaitable[None]],
    ) -> Callable[[], None]:
        """Register a transition callback. Returns an unregister callable."""

    def reset(self) -> None:
        """Reset to IDLE."""


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
