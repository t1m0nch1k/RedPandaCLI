from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from aios.runtime.models import Mission, MissionEvent, MissionStatus, MissionSummary, Plan, SubAgentResult, SubAgentTask


class MissionEngineProtocol:
    """
    Manages long-running autonomous missions with sub-task decomposition,
    parallel execution, progress tracking, checkpointing, and full
    lifecycle control (pause/resume/cancel/replan).

    Missions are checkpointed to a persisted store after every step
    and can resume after interruption. Lifecycle commands (pause,
    resume, cancel) are triggered via EventBus, not direct CLI calls.
    """

    async def create_mission(
        self,
        goal: str,
        conversation: Any,
    ) -> Mission:
        """Decompose goal into a Mission with initial Plan."""

    async def execute_mission(
        self,
        mission: Mission,
    ) -> AsyncIterator[MissionEvent]:
        """Execute mission steps. Yields events for progress tracking. Checkpoints after each step."""

    async def pause_mission(self, mission_id: str, reason: str = "") -> None:
        """Pause mission at the next safe point (after current step). State is checkpointed."""

    async def resume_mission(self, mission_id: str) -> AsyncIterator[MissionEvent]:
        """Resume a paused/checkpointed mission from its last completed step."""

    async def cancel_mission(self, mission_id: str) -> None:
        """Cancel mission immediately."""

    async def get_mission_status(self, mission_id: str) -> MissionStatus:
        """Return the current status of a mission."""

    async def request_replan(self, mission_id: str, feedback: str) -> Plan:
        """Request Planner to revise the remaining steps based on feedback."""

    async def spawn_sub_agent(self, task: SubAgentTask) -> SubAgentResult:
        """Spawn an isolated Runtime sub-agent with a restricted tool set."""

    async def list_missions(self) -> list[MissionSummary]:
        """List all active and completed missions with summary info."""
