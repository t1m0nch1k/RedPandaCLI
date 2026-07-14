from __future__ import annotations

from collections.abc import Awaitable, Callable

from aios.hooks.events import HookAction, HookContext, HookEvent

# A Hook is an async function that takes HookContext and returns HookAction
HookCallable = Callable[[HookContext], Awaitable[HookAction]]

class HookManager:
    """
    Orchestrates the registration and execution of hooks.
    """
    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[HookCallable]] = {
            event: [] for event in HookEvent
        }

    def register(self, event: HookEvent, callback: HookCallable) -> None:
        """Registers a hook for a specific event."""
        self._hooks[event].append(callback)

    async def trigger(self, event: HookEvent, context: HookContext) -> HookAction:
        """
        Executes all hooks registered for the given event.
        If any hook returns BLOCK, the operation is halted.
        """
        for callback in self._hooks[event]:
            try:
                action = await callback(context)
                if action == HookAction.BLOCK:
                    return HookAction.BLOCK
            except Exception as e:
                # Hooks should not crash the main agent loop
                print(f"Hook error: {e}")
                
        return HookAction.CONTINUE
