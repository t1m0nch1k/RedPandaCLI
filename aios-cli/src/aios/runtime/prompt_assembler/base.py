from __future__ import annotations

from typing import Any

from aios.runtime.models import Plan, Step


class PromptAssemblerProtocol:
    """
    Builds the final message array sent to the LLM.

    Composes:
      1. System prompt (base + memory context + workspace info)
      2. Conversation history (possibly truncated/compacted)
      3. Tool definitions

    This is the last stop before the provider call. The assembled
    messages are passed to the selected provider.
    """

    async def assemble(
        self,
        conversation: Any,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        memory_context: str = "",
    ) -> list[Any]:
        """Return the final message list for the LLM."""

    async def assemble_with_plan(
        self,
        conversation: Any,
        plan: Plan,
        current_step: Step | None = None,
    ) -> list[Any]:
        """Build messages for plan-guided execution. Injects plan context and current step."""
