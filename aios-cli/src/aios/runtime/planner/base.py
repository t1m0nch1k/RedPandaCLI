from __future__ import annotations

from aios.runtime.models import Plan, PlanningContext, ValidationResult


class PlannerProtocol:
    """
    Decomposes a user request into an executable Plan.

    Strategy: the Planner calls the LLM with a structured prompt to
    produce the plan. The plan can be reviewed by the user before
    execution (plan → approve → execute flow). A simple chat has null
    plan — Executor falls back to single-step.
    """

    async def plan(self, request: str, context: PlanningContext) -> Plan:
        """Decompose a request into an executable Plan."""

    async def replan(self, plan: Plan, feedback: str) -> Plan:
        """Revise an existing plan based on mid-execution feedback or error recovery."""

    async def validate(self, plan: Plan) -> ValidationResult:
        """Pre-execution validation: detect circular dependencies, missing tool references, ambiguous steps."""
