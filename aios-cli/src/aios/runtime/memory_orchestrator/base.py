from __future__ import annotations

from typing import Any


class MemoryOrchestratorProtocol:
    """
    Composes all memory sources into a single prompt fragment.

    Sources:
      - Global AIOS.md (~/.aios/AIOS.md)
      - Project AIOS.md (workspace root upward)
      - Auto memory (facts collected during previous sessions)
      - Conversation history (last N messages)

    Each source is a MemorySource with a weight and priority.
    The orchestrator assembles them in priority order, truncating
    to a token budget if needed.
    """

    async def assemble_context(
        self,
        conversation: Any,
        max_tokens: int = 2_048,
    ) -> str:
        """Build a memory context string from all memory sources."""

    async def add_fact(self, fact: str, source: str = "agent") -> None:
        """Persist a fact to auto memory."""

    def register_source(self, name: str, source: MemorySource, priority: int) -> None:
        """Register a memory source with a priority level."""


class MemorySource:
    """A single memory source that provides a text fragment."""

    async def load(self, conversation: Any) -> str:
        """Load the memory fragment for the given conversation."""

    @property
    def source_type(self) -> str:
        """Return the type identifier for this source."""

    @property
    def estimated_tokens(self) -> int:
        """Return the estimated token count for the loaded fragment."""
