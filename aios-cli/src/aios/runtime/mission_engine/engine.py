from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from aios.core.models import Conversation, Role
from aios.runtime.event_bus.base import EventBusProtocol
from aios.runtime.mission_engine.base import MissionEngineProtocol
from aios.runtime.models import (
    Mission,
    MissionEvent,
    MissionStatus,
    MissionSummary,
    Plan,
    PlanningContext,
    PlanStatus,
    SubAgentResult,
    SubAgentTask,
)

logger = logging.getLogger(__name__)


class MissionEngine(MissionEngineProtocol):
    """
    Handles execution of long-running missions by breaking them into steps,
    executing them, and monitoring progress with checkpointing.
    """

    def __init__(
        self,
        planner: Any,
        executor: Any,
        context_manager: Any,
        event_bus: EventBusProtocol,
        max_iterations_per_step: int = 25,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._context_manager = context_manager
        self._event_bus = event_bus
        self._max_iterations = max_iterations_per_step
        self._active_missions: dict[str, Mission] = {}
        
        # Determine missions directory
        self._missions_dir = Path.cwd() / ".aios" / "missions"
        self._missions_dir.mkdir(parents=True, exist_ok=True)

    def _save_checkpoint(self, mission: Mission) -> None:
        if not mission.checkpoint_path:
            mission.checkpoint_path = self._missions_dir / f"{mission.id}.json"
        
        import dataclasses
        plan_dict = dataclasses.asdict(mission.plan) if mission.plan else None
        conv_dict = mission.conversation.model_dump() if mission.conversation and hasattr(mission.conversation, "model_dump") else None

        data = {
            "id": mission.id,
            "goal": mission.goal,
            "status": mission.status.value,
            "current_step_index": mission.current_step_index,
            "total_steps": len(mission.plan.steps) if mission.plan else 0,
            "plan": plan_dict,
            "conversation": conv_dict,
        }
        
        try:
            mission.checkpoint_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save mission checkpoint: {e}")

    def _load_mission(self, mission_id: str) -> Mission | None:
        path = self._missions_dir / f"{mission_id}.json"
        if not path.exists():
            return None
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            
            plan_data = data.get("plan")
            plan = None
            if plan_data:
                from aios.runtime.models import Plan, PlanStatus, Step
                steps = [Step(**s) for s in plan_data.get("steps", [])]
                plan = Plan(
                    id=plan_data.get("id", ""),
                    goal=plan_data.get("goal", ""),
                    steps=steps,
                    parallel_groups=plan_data.get("parallel_groups", []),
                    created_at=plan_data.get("created_at", 0.0),
                    status=PlanStatus(plan_data.get("status", "pending"))
                )
                
            conv_data = data.get("conversation")
            conv = None
            if conv_data:
                from aios.core.models import Conversation
                conv = Conversation(**conv_data)
                
            mission = Mission(
                id=data["id"],
                goal=data["goal"],
                plan=plan,
                conversation=conv,
                status=MissionStatus(data.get("status", "failed")),
                current_step_index=data.get("current_step_index", 0),
                total_steps=data.get("total_steps", 0),
                checkpoint_path=path,
            )
            
            self._active_missions[mission.id] = mission
            return mission
        except Exception as e:
            logger.error(f"Failed to load mission {mission_id}: {e}")
            return None

    async def create_mission(self, goal: str, conversation: Any) -> Mission:
        context = PlanningContext(
            workspace_root=Path.cwd(),
            available_tools=[t.name for t in self._executor.tool_registry.list()],
            conversation_history="", 
        )

        plan = await self._planner.plan(goal, context)
        
        mission = Mission(
            id=str(uuid.uuid4()),
            goal=goal,
            plan=plan,
            conversation=conversation,
            status=MissionStatus.CREATED if plan.status != PlanStatus.FAILED else MissionStatus.FAILED,
            total_steps=len(plan.steps) if plan else 0
        )
        
        self._active_missions[mission.id] = mission
        self._save_checkpoint(mission)
        return mission

    async def execute_mission(self, mission: Mission) -> AsyncIterator[MissionEvent]:
        if mission.status == MissionStatus.FAILED or not mission.plan:
            yield MissionEvent(mission_id=mission.id, type="error", error="Planning failed or no plan available.")
            return

        mission.status = MissionStatus.EXECUTING
        self._save_checkpoint(mission)
        yield MissionEvent(mission_id=mission.id, type="plan_created", result=mission.plan)

        for idx in range(mission.current_step_index, len(mission.plan.steps)):
            # Check for interrupt
            if mission.status in (MissionStatus.PAUSED, MissionStatus.CANCELLED):
                yield MissionEvent(mission_id=mission.id, type="interrupted", content=f"Mission {mission.status.value}")
                return

            step = mission.plan.steps[idx]
            yield MissionEvent(mission_id=mission.id, type="step_started", step_id=step.id, result=step)

            step_instruction = (
                f"Execute the following step: {step.description}\\n"
                f"Expected outcome: {step.expected_outcome}\\n"
                f"Target tool: {step.tool_name or 'LLM only'}\\n"
                f"Please focus only on this step. When done, output a final answer summarizing the result."
            )
            mission.conversation.add(Role.USER, step_instruction)

            result = await self._executor.run(
                conversation=mission.conversation, 
                max_iterations=self._max_iterations
            )

            # Mark step complete and save checkpoint
            mission.current_step_index = idx + 1
            self._save_checkpoint(mission)
            
            yield MissionEvent(mission_id=mission.id, type="step_completed", step_id=step.id, result=result)

        mission.status = MissionStatus.COMPLETED
        self._save_checkpoint(mission)
        yield MissionEvent(mission_id=mission.id, type="mission_completed", result=mission.plan)
        
        # Cleanup memory
        self._active_missions.pop(mission.id, None)

    async def pause_mission(self, mission_id: str, reason: str = "") -> None:
        if mission_id in self._active_missions:
            self._active_missions[mission_id].status = MissionStatus.PAUSED
            self._save_checkpoint(self._active_missions[mission_id])

    async def resume_mission(self, mission_id: str) -> AsyncIterator[MissionEvent]:
        if mission_id not in self._active_missions:
            self._load_mission(mission_id)
            
        if mission_id in self._active_missions:
            mission = self._active_missions[mission_id]
            if mission.status == MissionStatus.PAUSED:
                mission.status = MissionStatus.EXECUTING
                self._save_checkpoint(mission)
                async for event in self.execute_mission(mission):
                    yield event
            else:
                yield MissionEvent(mission_id=mission_id, type="error", error="Mission is not paused.")
        else:
            yield MissionEvent(mission_id=mission_id, type="error", error="Mission not found in memory or disk.")

    async def cancel_mission(self, mission_id: str) -> None:
        if mission_id in self._active_missions:
            self._active_missions[mission_id].status = MissionStatus.CANCELLED
            self._save_checkpoint(self._active_missions[mission_id])

    async def get_mission_status(self, mission_id: str) -> MissionStatus:
        if mission_id not in self._active_missions:
            self._load_mission(mission_id)
            
        if mission_id in self._active_missions:
            return self._active_missions[mission_id].status
        return MissionStatus.FAILED

    async def request_replan(self, mission_id: str, feedback: str) -> Plan:
        if mission_id not in self._active_missions:
            self._load_mission(mission_id)
            
        if mission_id not in self._active_missions:
            raise ValueError(f"Mission {mission_id} not found.")
            
        mission = self._active_missions[mission_id]
        
        history = ""
        if mission.conversation:
            history = "\\n".join([f"{m.role}: {m.content}" for m in mission.conversation.messages])
            
        context = PlanningContext(
            workspace_root=Path.cwd(),
            available_tools=[t.name for t in self._executor.tool_registry.list()],
            conversation_history=history,
        )
        
        new_goal = f"{mission.goal}\\n\\nUser feedback for replanning: {feedback}"
        new_plan = await self._planner.plan(new_goal, context)
        
        mission.plan = new_plan
        mission.current_step_index = 0
        mission.total_steps = len(new_plan.steps)
        if mission.status in (MissionStatus.FAILED, MissionStatus.CANCELLED, MissionStatus.PAUSED):
            mission.status = MissionStatus.EXECUTING
        
        self._save_checkpoint(mission)
        return new_plan

    async def spawn_sub_agent(self, task: SubAgentTask) -> SubAgentResult:
        # Create an isolated ExecutionEngine
        from aios.executor.engine import ExecutionEngine
        from aios.tools.registry import ToolRegistry
        
        isolated_registry = ToolRegistry()
        for tool_name in task.allowed_tools:
            t = self._executor.tool_registry.get(tool_name)
            if t:
                isolated_registry.register(t)
                
        sub_executor = ExecutionEngine(
            provider=self._executor.provider,
            tool_registry=isolated_registry,
            permission_manager=self._executor.permission_manager, # Share permissions
            system_prompt=f"You are a Sub-Agent. Your goal is: {task.goal}. Instructions: {task.instructions}",
            workspace_root=self._executor.workspace_root
        )
        
        sub_conv = Conversation()
        sub_conv.add(Role.USER, "Begin your task.")
        
        try:
            result_content = await sub_executor.run(sub_conv, max_iterations=self._max_iterations)
            return SubAgentResult(success=True, summary=result_content)
        except Exception as e:
            return SubAgentResult(success=False, error=str(e))

    async def list_missions(self) -> list[MissionSummary]:
        summaries = []
        for path in self._missions_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                progress = data.get("current_step_index", 0) / max(1, data.get("total_steps", 1))
                summaries.append(MissionSummary(
                    id=data.get("id", ""),
                    goal=data.get("goal", ""),
                    status=MissionStatus(data.get("status", "failed")),
                    progress=progress,
                    step_count=data.get("total_steps", 0)
                ))
            except Exception:
                pass
        return summaries
