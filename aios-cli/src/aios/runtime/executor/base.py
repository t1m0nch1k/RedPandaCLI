from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aios.runtime.models import ExecutionResult, Plan, Step, StepResult

StreamCallback = Callable[[Any], Awaitable[None] | None]


class ExecutorProtocol:
    """
    The core agent loop: think -> act -> observe, repeated until a
    terminal state is reached.

    When a Plan is provided, Executor walks through steps in order,
    respecting dependencies. When no plan is provided, Executor runs
    a free-form loop (LLM decides tool calls).
    """

    async def run(
        self,
        conversation: Any,
        plan: Plan | None = None,
        stream_callback: StreamCallback | None = None,
        max_iterations: int = 25,
    ) -> ExecutionResult:
        """Run the agent loop. If plan is provided, execute plan steps."""

    async def run_step(self, step: Step, conversation: Any) -> StepResult:
        """Execute a single Plan step. Calls LLM once, executes any tool calls that result."""

    async def cancel(self) -> None:
        """Cancel a running execution at the next safe checkpoint."""
