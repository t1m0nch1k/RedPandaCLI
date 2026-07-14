from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from aios.core.models import Message, Role
from aios.runtime.models import (
    Plan,
    PlanStatus,
    PlanningContext,
    Step,
    ValidationResult,
    ValidationRetryConfig,
)
from aios.runtime.planner.base import PlannerProtocol
from aios.runtime.workspace_knowledge.base import WorkspaceKnowledgeProtocol

logger = logging.getLogger(__name__)

PLAN_PROMPT = """You are a planning agent. Given a user request, produce a step-by-step plan using the available tools.

AVAILABLE TOOLS:
{tools}

WORKSPACE CONTEXT:
{workspace_context}

CONVERSATION HISTORY:
{history}

USER REQUEST: {request}

USER PREFERENCES: {preferences}

Respond with ONLY valid JSON. No markdown, no explanation, no code fences.

{{
  "goal": "Restate the user's goal concisely",
  "steps": [
    {{
      "id": "step-1",
      "description": "What this step does",
      "tool_name": "tool_name_or_null_if_llm_only",
      "args": {{"key": "value"}} or null,
      "dependencies": [],
      "expected_outcome": "What success looks like"
    }}
  ],
  "parallel_groups": [["step-1", "step-2"]],
  "estimated_complexity": "simple|moderate|complex"
}}"""

REPLAN_PROMPT = """You are revising a plan based on execution feedback.

ORIGINAL GOAL: {goal}

REMAINING STEPS (still need to execute):
{remaining_steps}

EXECUTION FEEDBACK:
{feedback}

AVAILABLE TOOLS:
{tools}

WORKSPACE CONTEXT:
{workspace_context}

Produce a revised plan as JSON (same format as the original).
Only include the remaining/future steps. Do not repeat completed steps.

Respond with ONLY valid JSON. No markdown, no explanation, no code fences.

{{
  "goal": "Restate the goal",
  "steps": [
    {{
      "id": "step-1",
      "description": "...",
      "tool_name": "tool_name_or_null",
      "args": {{}} or null,
      "dependencies": [],
      "expected_outcome": "..."
    }}
  ],
  "parallel_groups": [["step-1", "step-2"]],
  "estimated_complexity": "simple|moderate|complex"
}}"""


def _generate_step_id(index: int) -> str:
    return f"step-{index + 1}"


def _parse_llm_response(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("\n", 1)
        if len(parts) > 1:
            cleaned = parts[1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


def _build_workspace_context(
    frameworks: list[Any] | None = None,
    deps: Any = None,
    entry_points: list[Any] | None = None,
    git: Any = None,
) -> str:
    parts: list[str] = []
    if frameworks:
        names = [getattr(f, "name", str(f)) for f in frameworks]
        parts.append(f"Frameworks: {', '.join(names)}")
    if deps:
        manager = getattr(deps, "manager", None)
        root = getattr(deps, "root", None)
        if manager:
            parts.append(f"Package manager: {manager}")
        if root:
            parts.append(f"Project root: {root}")
    if entry_points:
        names = [getattr(e, "name", str(e)) for e in entry_points]
        parts.append(f"Entry points: {', '.join(names)}")
    if git:
        branch = getattr(git, "branch", None)
        if branch:
            parts.append(f"Git branch: {branch}")
    return "\n".join(parts) if parts else "(no workspace context available)"


def _detect_circular_dependencies(steps: list[Step]) -> list[list[str]]:
    step_ids = {s.id for s in steps}
    dep_map: dict[str, list[str]] = {}
    for s in steps:
        dep_map[s.id] = [d for d in s.dependencies if d in step_ids]

    cycles: list[list[str]] = []
    visited: set[str] = set()
    rec_stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in dep_map.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
        path.pop()
        rec_stack.discard(node)

    for sid in step_ids:
        if sid not in visited:
            dfs(sid)

    return cycles


class Planner(PlannerProtocol):
    """Concrete Planner implementation.

    Responsibilities:
    - Generate structured execution plans from user requests via LLM.
    - Produce a dependency graph of Steps.
    - Validate generated plans (circular deps, missing tools, etc.).
    - Detect impossible or circular dependencies.
    - Estimate execution cost and complexity.
    - Support partial replanning via feedback.
    - Support plan serialization/deserialization.
    - Support plan validation retries using ValidationRetryConfig.
    - Integrate with PlanningContext.
    - Request WorkspaceKnowledge automatically when available.

    Never executes tools or calls providers directly.
    """

    def __init__(
        self,
        llm_chat: Callable[[list[dict]], Awaitable[str]],
        workspace: WorkspaceKnowledgeProtocol | None = None,
        retry_config: ValidationRetryConfig | None = None,
    ) -> None:
        self._llm_chat = llm_chat
        self._workspace = workspace
        self._retry_config = retry_config or ValidationRetryConfig()

    async def plan(self, request: str, context: PlanningContext) -> Plan:
        workspace_context = await self._get_workspace_context()
        tools_str = ", ".join(context.available_tools) if context.available_tools else "(none)"
        prompt = PLAN_PROMPT.format(
            tools=tools_str,
            workspace_context=workspace_context,
            history=context.conversation_history or "(empty)",
            request=request,
            preferences=str(context.user_preferences) if context.user_preferences else "(none)",
        )
        messages = [Message(role=Role.USER, content=prompt)]
        last_error = ""

        for attempt in range(self._retry_config.max_retries):
            raw = await self._llm_chat(messages)
            parsed, parse_error = self._try_parse(raw)
            if parse_error:
                last_error = parse_error
                if attempt < self._retry_config.max_retries - 1:
                    messages.append(Message(role=Role.ASSISTANT, content=raw))
                    messages.append(Message(
                        role=Role.USER,
                        content=self._retry_config.retry_prompt_template.format(
                            errors=parse_error,
                        ),
                    ))
                continue

            plan = self._build_plan(request, parsed)
            validation = await self.validate(plan)
            if validation.valid:
                return plan

            last_error = "; ".join(validation.errors)
            if attempt < self._retry_config.max_retries - 1:
                messages.append(Message(role=Role.ASSISTANT, content=raw))
                messages.append(Message(
                    role=Role.USER,
                    content=self._retry_config.retry_prompt_template.format(
                        errors=last_error,
                    ),
                ))

        return Plan(id="", goal=request, steps=[], status=PlanStatus.FAILED)

    async def replan(self, plan: Plan, feedback: str, context: PlanningContext | None = None) -> Plan:
        remaining = self._get_remaining_steps(plan)
        remaining_str = "\n".join(
            f"  {s.id}: {s.description} (tool: {s.tool_name or 'LLM'})"
            for s in remaining
        ) or "(no remaining steps)"
        workspace_context = await self._get_workspace_context()
        tools_str = (
            ", ".join(context.available_tools)
            if context and context.available_tools
            else "(none)"
        )
        prompt = REPLAN_PROMPT.format(
            goal=plan.goal,
            remaining_steps=remaining_str,
            feedback=feedback,
            tools=tools_str,
            workspace_context=workspace_context,
        )
        messages = [Message(role=Role.USER, content=prompt)]

        for attempt in range(self._retry_config.max_retries):
            raw = await self._llm_chat(messages)
            parsed, parse_error = self._try_parse(raw)
            if parse_error:
                if attempt < self._retry_config.max_retries - 1:
                    messages.append(Message(role=Role.ASSISTANT, content=raw))
                    messages.append(Message(
                        role=Role.USER,
                        content=self._retry_config.retry_prompt_template.format(
                            errors=parse_error,
                        ),
                    ))
                continue

            new_plan = self._build_plan(plan.goal, parsed)
            validation = await self.validate(new_plan)
            if validation.valid:
                return new_plan

            if attempt < self._retry_config.max_retries - 1:
                messages.append(Message(role=Role.ASSISTANT, content=raw))
                messages.append(Message(
                    role=Role.USER,
                    content=self._retry_config.retry_prompt_template.format(
                        errors="; ".join(validation.errors),
                    ),
                ))

        return Plan(id=plan.id, goal=plan.goal, steps=remaining, status=PlanStatus.FAILED)

    async def validate(self, plan: Plan) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not plan.steps:
            errors.append("Plan has no steps")

        step_ids = [s.id for s in plan.steps]

        if len(step_ids) != len(set(step_ids)):
            seen: set[str] = set()
            dupes: set[str] = set()
            for sid in step_ids:
                if sid in seen:
                    dupes.add(sid)
                seen.add(sid)
            errors.append(f"Duplicate step IDs: {sorted(dupes)}")

        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step '{step.id}' depends on unknown step '{dep}'")

        if step_ids:
            cycles = _detect_circular_dependencies(plan.steps)
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        for step in plan.steps:
            if not step.description.strip():
                errors.append(f"Step '{step.id}' has no description")

        for step in plan.steps:
            if not step.expected_outcome.strip():
                warnings.append(f"Step '{step.id}' has no expected outcome")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def estimate_cost(self, plan: Plan) -> float:
        total = 0.0
        for step in plan.steps:
            if step.tool_name:
                total += 0.01
            else:
                total += 0.005
        return total

    def estimate_complexity(self, plan: Plan) -> str:
        if not plan.steps:
            return "simple"
        step_count = len(plan.steps)
        tool_steps = sum(1 for s in plan.steps if s.tool_name is not None)
        has_parallel = bool(plan.parallel_groups)
        if step_count <= 2 and tool_steps <= 1 and not has_parallel:
            return "simple"
        if step_count <= 5 and tool_steps <= 3:
            return "moderate"
        return "complex"

    @staticmethod
    def serialize(plan: Plan) -> dict:
        return {
            "id": plan.id,
            "goal": plan.goal,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool_name": s.tool_name,
                    "args": s.args,
                    "dependencies": list(s.dependencies),
                    "expected_outcome": s.expected_outcome,
                    "timeout_s": s.timeout_s,
                }
                for s in plan.steps
            ],
            "parallel_groups": [list(g) for g in plan.parallel_groups],
            "created_at": plan.created_at,
            "status": plan.status.value,
        }

    @staticmethod
    def deserialize(data: dict) -> Plan:
        return Plan(
            id=data["id"],
            goal=data["goal"],
            steps=[
                Step(
                    id=s["id"],
                    description=s["description"],
                    tool_name=s.get("tool_name"),
                    args=s.get("args"),
                    dependencies=tuple(s.get("dependencies", [])),
                    expected_outcome=s.get("expected_outcome", ""),
                    timeout_s=s.get("timeout_s", 60),
                )
                for s in data["steps"]
            ],
            parallel_groups=[tuple(g) for g in data.get("parallel_groups", [])],
            created_at=data.get("created_at", time.time()),
            status=PlanStatus(data.get("status", "pending")),
        )

    async def _get_workspace_context(self) -> str:
        if self._workspace is None:
            return "(workspace knowledge unavailable)"
        try:
            frameworks = await self._workspace.detect_frameworks()
            deps = await self._workspace.dependency_graph()
            entry_points = await self._workspace.entry_points()
            git = await self._workspace.git_context()
            return _build_workspace_context(frameworks, deps, entry_points, git)
        except Exception:
            logger.exception("Failed to fetch workspace knowledge")
            return "(workspace knowledge unavailable)"

    def _try_parse(self, raw: str) -> tuple[dict, str]:
        try:
            parsed = _parse_llm_response(raw)
            if "steps" not in parsed or not isinstance(parsed["steps"], list):
                return {}, "Response missing 'steps' array"
            if "goal" not in parsed:
                return {}, "Response missing 'goal' field"
            return parsed, ""
        except json.JSONDecodeError as e:
            return {}, f"Invalid JSON: {e}"
        except Exception as e:
            return {}, f"Parse error: {e}"

    def _build_plan(self, goal: str, parsed: dict) -> Plan:
        steps: list[Step] = []
        for i, raw_step in enumerate(parsed.get("steps", [])):
            step_id = raw_step.get("id") or _generate_step_id(i)
            deps = raw_step.get("dependencies", [])
            if isinstance(deps, list):
                deps = [str(d) for d in deps]
            steps.append(
                Step(
                    id=step_id,
                    description=raw_step.get("description", ""),
                    tool_name=raw_step.get("tool_name"),
                    args=raw_step.get("args"),
                    dependencies=tuple(deps),
                    expected_outcome=raw_step.get("expected_outcome", ""),
                    timeout_s=raw_step.get("timeout_s", 60),
                )
            )
        parallel_groups_raw = parsed.get("parallel_groups", [])
        parallel_groups = [
            tuple(str(s) for s in group)
            for group in parallel_groups_raw
            if isinstance(group, list)
        ]
        return Plan(
            id=str(uuid.uuid4()),
            goal=parsed.get("goal", goal),
            steps=steps,
            parallel_groups=parallel_groups,
        )

    @staticmethod
    def _get_remaining_steps(plan: Plan) -> list[Step]:
        return [
            s
            for s in plan.steps
            if s.id not in getattr(plan, "_completed_ids", set())
        ]
