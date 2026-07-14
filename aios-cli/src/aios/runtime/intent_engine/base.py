from __future__ import annotations

from typing import Any

from aios.runtime.models import Intent, IntentResult


class IntentEngineProtocol:
    """
    Pluggable processing pipeline for user input classification.

    Stages run in priority order through four stages:
      1. Rule Engine    — deterministic pattern matching (regex, prefix)
      2. Local          — (future) on-device ML classifier
      3. Planner        — multi-step request decomposition
      4. LLM            — fallback for ambiguous/free-form input

    The first stage that returns handled=True wins. This guarantees
    that deterministic commands ("git status", "open VSCode") never
    touch an LLM.
    """

    async def classify(
        self,
        text: str,
        conversation: Any | None = None,
    ) -> Intent:
        """Classify user input into an intent category."""

    def register_stage(self, stage: IntentStage, priority: int) -> None:
        """Register an IntentStage with a priority level. Lower numbers run first."""

    def remove_stage(self, name: str) -> None:
        """Remove a registered stage by name."""

    def list_stages(self) -> list[str]:
        """Return registered stage names in execution order."""


class IntentStage:
    """A single stage in the IntentEngine pipeline."""

    @property
    def name(self) -> str:
        """Return the stage name."""

    async def can_handle(
        self,
        text: str,
        conversation: Any | None = None,
    ) -> bool:
        """Check whether this stage can handle the input."""

    async def handle(
        self,
        text: str,
        conversation: Any | None = None,
    ) -> IntentResult:
        """Handle the input and return an IntentResult."""
