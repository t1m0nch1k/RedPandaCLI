from __future__ import annotations

import json
from pathlib import Path

import pytest
from aios.runtime.models import (
    Plan,
    PlanningContext,
    PlanStatus,
    Step,
    ValidationRetryConfig,
)
from aios.runtime.planner.planner import (
    Planner,
    _detect_circular_dependencies,
    _parse_llm_response,
)

GOAL = "Set up a Python project with FastAPI"
TOOLS = ["bash", "read", "write", "edit", "search", "list_dir"]

VALID_PLAN_JSON = json.dumps({
    "goal": GOAL,
    "steps": [
        {
            "id": "step-1",
            "description": "Create project directory structure",
            "tool_name": "bash",
            "args": {"command": "mkdir -p my_project"},
            "dependencies": [],
            "expected_outcome": "Project directory created",
        },
        {
            "id": "step-2",
            "description": "Initialize FastAPI project",
            "tool_name": "bash",
            "args": {"command": "pip install fastapi"},
            "dependencies": ["step-1"],
            "expected_outcome": "FastAPI installed",
        },
        {
            "id": "step-3",
            "description": "Create main application file",
            "tool_name": "write",
            "dependencies": ["step-2"],
            "expected_outcome": "main.py created",
        },
    ],
    "parallel_groups": [],
    "estimated_complexity": "moderate",
})

CONTEXT = PlanningContext(
    workspace_root=Path("/workspace"),
    available_tools=TOOLS,
    conversation_history="",
    max_steps=10,
)


async def _mock_llm(response: str) -> str:
    return response


def _make_planner(
    llm_response: str = VALID_PLAN_JSON,
    retry_config: ValidationRetryConfig | None = None,
) -> tuple[Planner, list[list[dict]]]:
    calls: list[list[dict]] = []

    async def chat(messages: list[dict]) -> str:
        calls.append(messages)
        return llm_response

    planner = Planner(
        llm_chat=chat,
        workspace=None,
        retry_config=retry_config,
    )
    return planner, calls


class TestParseLlmResponse:
    def test_parses_clean_json(self) -> None:
        result = _parse_llm_response('{"steps": [], "goal": "test"}')
        assert result["goal"] == "test"

    def test_strips_markdown_fence(self) -> None:
        raw = """```json
{"steps": [], "goal": "test"}
```"""
        result = _parse_llm_response(raw)
        assert result["goal"] == "test"

    def test_strips_markdown_no_lang(self) -> None:
        raw = """```
{"steps": [], "goal": "test"}
```"""
        result = _parse_llm_response(raw)
        assert result["goal"] == "test"

    def test_strips_code_fence_start_only(self) -> None:
        raw = """```json
{"steps": [], "goal": "test"}"""
        result = _parse_llm_response(raw)
        assert result["goal"] == "test"

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("not json")


class TestDetectCircularDependencies:
    def test_no_cycle(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=()),
            Step(id="s2", description="b", dependencies=("s1",)),
            Step(id="s3", description="c", dependencies=("s2",)),
        ]
        assert _detect_circular_dependencies(steps) == []

    def test_simple_cycle(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=("s2",)),
            Step(id="s2", description="b", dependencies=("s1",)),
        ]
        cycles = _detect_circular_dependencies(steps)
        assert len(cycles) == 1

    def test_self_dependency(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=("s1",)),
        ]
        cycles = _detect_circular_dependencies(steps)
        assert len(cycles) >= 1

    def test_complex_cycle(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=("s2",)),
            Step(id="s2", description="b", dependencies=("s3",)),
            Step(id="s3", description="c", dependencies=("s4",)),
            Step(id="s4", description="d", dependencies=("s1",)),
        ]
        cycles = _detect_circular_dependencies(steps)
        assert len(cycles) >= 1

    def test_ignores_external_deps(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=("external",)),
        ]
        assert _detect_circular_dependencies(steps) == []

    def test_multiple_independent_chains(self) -> None:
        steps = [
            Step(id="s1", description="a", dependencies=()),
            Step(id="s2", description="b", dependencies=("s1",)),
            Step(id="s3", description="c", dependencies=()),
            Step(id="s4", description="d", dependencies=("s3",)),
        ]
        assert _detect_circular_dependencies(steps) == []

    def test_single_step_no_deps(self) -> None:
        steps = [Step(id="s1", description="a", dependencies=())]
        assert _detect_circular_dependencies(steps) == []

    def test_empty_steps(self) -> None:
        assert _detect_circular_dependencies([]) == []


class TestPlannerPlan:
    async def test_plan_generates_valid_plan(self) -> None:
        planner, calls = _make_planner()
        plan = await planner.plan(GOAL, CONTEXT)
        assert isinstance(plan, Plan)
        assert plan.goal == GOAL
        assert len(plan.steps) == 3
        assert plan.steps[0].id == "step-1"
        assert plan.steps[0].tool_name == "bash"
        assert len(calls) == 1

    async def test_plan_passes_tools_in_prompt(self) -> None:
        planner, calls = _make_planner()
        await planner.plan(GOAL, CONTEXT)
        prompt = calls[0][0].content
        for tool in TOOLS:
            assert tool in prompt

    async def test_plan_includes_request_in_prompt(self) -> None:
        planner, calls = _make_planner()
        await planner.plan(GOAL, CONTEXT)
        prompt = calls[0][0].content
        assert GOAL in prompt

    async def test_plan_returns_failed_on_parse_error(self) -> None:
        planner, _ = _make_planner(llm_response="not valid json")
        plan = await planner.plan(GOAL, CONTEXT)
        assert isinstance(plan, Plan)
        assert plan.status == PlanStatus.FAILED
        assert plan.goal == GOAL

    async def test_plan_retries_on_parse_error(self) -> None:
        calls: list[list[dict]] = []
        responses = iter(["bad json", VALID_PLAN_JSON])

        async def chat(messages: list[dict]) -> str:
            calls.append(messages)
            return next(responses)

        planner = Planner(llm_chat=chat, retry_config=ValidationRetryConfig(max_retries=3))
        plan = await planner.plan(GOAL, CONTEXT)
        assert len(calls) == 2
        assert isinstance(plan, Plan)
        assert len(plan.steps) == 3

    async def test_plan_exhausts_retries(self) -> None:
        calls: list[list[dict]] = []

        async def chat(messages: list[dict]) -> str:
            calls.append(messages)
            return "bad json forever"

        planner = Planner(llm_chat=chat, retry_config=ValidationRetryConfig(max_retries=3))
        plan = await planner.plan(GOAL, CONTEXT)
        assert len(calls) == 3
        assert isinstance(plan, Plan)
        assert plan.status == PlanStatus.FAILED
        assert plan.goal == GOAL

    async def test_plan_retries_on_validation_failure(self) -> None:
        bad_plan = json.dumps({
            "goal": GOAL,
            "steps": [
                {
                    "id": "step-1",
                    "description": "",
                    "tool_name": None,
                    "dependencies": [],
                    "expected_outcome": "",
                },
            ],
        })
        calls: list[list[dict]] = []
        responses = iter([bad_plan, VALID_PLAN_JSON])

        async def chat(messages: list[dict]) -> str:
            calls.append(messages)
            return next(responses)

        planner = Planner(llm_chat=chat, retry_config=ValidationRetryConfig(max_retries=3))
        plan = await planner.plan(GOAL, CONTEXT)
        assert len(calls) == 2
        assert isinstance(plan, Plan)
        assert len(plan.steps) == 3

    async def test_empty_tools_in_context(self) -> None:
        ctx = PlanningContext(
            workspace_root=Path("/x"),
            available_tools=[],
        )
        planner, calls = _make_planner()
        plan = await planner.plan("hello", ctx)
        prompt = calls[0][0].content
        assert "(none)" in prompt
        assert isinstance(plan, Plan)

    async def test_plan_with_conversation_history(self) -> None:
        ctx = PlanningContext(
            workspace_root=Path("/x"),
            available_tools=TOOLS,
            conversation_history="User asked about FastAPI",
        )
        planner, calls = _make_planner()
        await planner.plan(GOAL, ctx)
        prompt = calls[0][0].content
        assert "User asked about FastAPI" in prompt

    async def test_plan_with_user_preferences(self) -> None:
        ctx = PlanningContext(
            workspace_root=Path("/x"),
            available_tools=TOOLS,
            user_preferences={"preferred_tools": ["bash", "write"]},
        )
        planner, calls = _make_planner()
        await planner.plan(GOAL, ctx)
        prompt = calls[0][0].content
        assert "preferred_tools" in prompt

    async def test_plan_without_workspace(self) -> None:
        planner, calls = _make_planner()
        await planner.plan(GOAL, CONTEXT)
        prompt = calls[0][0].content
        assert "workspace knowledge unavailable" in prompt.lower()


class TestPlannerReplan:
    async def test_replan_generates_plan(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="step-1", description="First step", tool_name="bash", dependencies=()),
                Step(id="step-2", description="Second step", tool_name="write", dependencies=("step-1",)),
            ],
        )
        planner, calls = _make_planner()
        revised = await planner.replan(original, "Step 1 failed: permission denied", CONTEXT)
        assert isinstance(revised, Plan)
        assert len(calls) == 1

    async def test_replan_includes_feedback_in_prompt(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[Step(id="step-1", description="A", tool_name="bash", dependencies=())],
        )
        planner, calls = _make_planner()
        await planner.replan(original, "permission denied", CONTEXT)
        prompt = calls[0][0].content
        assert "permission denied" in prompt

    async def test_replan_retries_on_parse_error(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[Step(id="step-1", description="A", tool_name="bash", dependencies=())],
        )
        calls: list[list[dict]] = []
        responses = iter(["bad json", VALID_PLAN_JSON])

        async def chat(messages: list[dict]) -> str:
            calls.append(messages)
            return next(responses)

        planner = Planner(llm_chat=chat, retry_config=ValidationRetryConfig(max_retries=3))
        revised = await planner.replan(original, "error", CONTEXT)
        assert len(calls) == 2
        assert isinstance(revised, Plan)

    async def test_replan_returns_failed_on_exhaustion(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[Step(id="step-1", description="A", tool_name="bash", dependencies=())],
        )

        async def chat(messages: list[dict]) -> str:
            return "bad json"

        planner = Planner(llm_chat=chat, retry_config=ValidationRetryConfig(max_retries=2))
        result = await planner.replan(original, "error", CONTEXT)
        assert isinstance(result, Plan)
        assert result.status == PlanStatus.FAILED

    async def test_replan_without_context(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[Step(id="step-1", description="A", tool_name="bash", dependencies=())],
        )
        planner, calls = _make_planner()
        revised = await planner.replan(original, "nope", None)
        assert isinstance(revised, Plan)
        assert len(calls) == 1


class TestPlannerValidate:
    VALID_PLAN = Plan(
        id="p1",
        goal=GOAL,
        steps=[
            Step(id="s1", description="A", tool_name="bash", dependencies=(), expected_outcome="Done"),
            Step(id="s2", description="B", tool_name="write", dependencies=("s1",), expected_outcome="Done"),
        ],
    )

    async def test_validate_valid(self) -> None:
        planner, _ = _make_planner()
        result = await planner.validate(self.VALID_PLAN)
        assert result.valid is True
        assert result.errors == []

    async def test_validate_no_steps(self) -> None:
        plan = Plan(id="p1", goal=GOAL, steps=[])
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False
        assert any("no steps" in e.lower() for e in result.errors)

    async def test_validate_duplicate_ids(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
                Step(id="s1", description="B", tool_name="write", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False
        assert any("duplicate" in e.lower() for e in result.errors)

    async def test_validate_unknown_dependency(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="A", dependencies=("nonexistent",)),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False
        assert any("unknown step" in e.lower() for e in result.errors)

    async def test_validate_circular_dependency(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="A", dependencies=("s2",)),
                Step(id="s2", description="B", dependencies=("s1",)),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False
        assert any("circular" in e.lower() for e in result.errors)

    async def test_validate_missing_description(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="  ", tool_name="bash", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False

    async def test_validate_warns_on_missing_expected_outcome(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=(), expected_outcome=""),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is True
        assert any("expected outcome" in w.lower() for w in result.warnings)

    async def test_validate_self_dependency(self) -> None:
        plan = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(id="s1", description="A", dependencies=("s1",)),
            ],
        )
        planner, _ = _make_planner()
        result = await planner.validate(plan)
        assert result.valid is False
        assert any("circular" in e.lower() for e in result.errors)


class TestPlannerCostAndComplexity:
    def test_estimate_cost_no_tools(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name=None, dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        cost = planner.estimate_cost(plan)
        assert cost == 0.005

    def test_estimate_cost_with_tools(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
                Step(id="s2", description="B", tool_name="write", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        cost = planner.estimate_cost(plan)
        assert cost == 0.02

    def test_estimate_cost_mixed(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
                Step(id="s2", description="B", tool_name=None, dependencies=()),
                Step(id="s3", description="C", tool_name="write", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        cost = planner.estimate_cost(plan)
        assert cost == pytest.approx(0.025)

    def test_estimate_complexity_simple(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "simple"

    def test_estimate_complexity_simple_no_tools(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name=None, dependencies=()),
                Step(id="s2", description="B", tool_name=None, dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "simple"

    def test_estimate_complexity_moderate(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
                Step(id="s2", description="B", tool_name="write", dependencies=()),
                Step(id="s3", description="C", tool_name="bash", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "moderate"

    def test_estimate_complexity_complex(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
                Step(id="s2", description="B", tool_name="write", dependencies=()),
                Step(id="s3", description="C", tool_name="bash", dependencies=()),
                Step(id="s4", description="D", tool_name="read", dependencies=()),
                Step(id="s5", description="E", tool_name="edit", dependencies=()),
                Step(id="s6", description="F", tool_name="search", dependencies=()),
            ],
        )
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "complex"

    def test_estimate_complexity_parallel(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", tool_name="bash", dependencies=()),
            ],
            parallel_groups=[("s1",)],
        )
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "moderate"

    def test_estimate_complexity_empty(self) -> None:
        plan = Plan(id="p1", goal="test", steps=[])
        planner, _ = _make_planner()
        assert planner.estimate_complexity(plan) == "simple"


class TestPlannerSerialization:
    def test_serialize_roundtrip(self) -> None:
        original = Plan(
            id="p1",
            goal=GOAL,
            steps=[
                Step(
                    id="s1",
                    description="Create dir",
                    tool_name="bash",
                    args={"command": "mkdir"},
                    dependencies=("s0",),
                    expected_outcome="Dir created",
                    timeout_s=120,
                ),
            ],
            parallel_groups=[],
        )
        data = Planner.serialize(original)
        restored = Planner.deserialize(data)
        assert restored.id == original.id
        assert restored.goal == original.goal
        assert len(restored.steps) == len(original.steps)
        assert restored.steps[0].id == original.steps[0].id
        assert restored.steps[0].tool_name == original.steps[0].tool_name
        assert restored.steps[0].args == original.steps[0].args
        assert restored.steps[0].dependencies == original.steps[0].dependencies
        assert restored.steps[0].timeout_s == original.steps[0].timeout_s

    def test_serialize_roundtrip_all_fields(self) -> None:
        original = Plan(
            id="p-unique",
            goal="Test all fields",
            steps=[
                Step(id="a", description="A", tool_name=None, dependencies=(), expected_outcome="X", timeout_s=30),
                Step(id="b", description="B", tool_name="bash", args={"x": 1}, dependencies=("a",), expected_outcome="Y", timeout_s=60),
            ],
            parallel_groups=[("a", "b")],
            status=PlanStatus.APPROVED,
        )
        data = Planner.serialize(original)
        restored = Planner.deserialize(data)
        assert restored.id == "p-unique"
        assert restored.status == PlanStatus.APPROVED
        assert ("a", "b") in restored.parallel_groups
        assert restored.steps[1].args == {"x": 1}
        assert restored.steps[1].dependencies == ("a",)

    def test_serialize_parallel_groups_preserved(self) -> None:
        original = Plan(
            id="p1",
            goal="test",
            steps=[Step(id="a", description="A", dependencies=()), Step(id="b", description="B", dependencies=())],
            parallel_groups=[("a", "b")],
        )
        data = Planner.serialize(original)
        restored = Planner.deserialize(data)
        assert ("a", "b") in restored.parallel_groups

    def test_deserialize_with_missing_optional_fields(self) -> None:
        data = {
            "id": "p1",
            "goal": "test",
            "steps": [
                {
                    "id": "s1",
                    "description": "A",
                }
            ],
        }
        plan = Planner.deserialize(data)
        assert plan.id == "p1"
        assert plan.steps[0].tool_name is None
        assert plan.steps[0].dependencies == ()
        assert plan.steps[0].timeout_s == 60


class TestPlannerConstructor:
    def test_default_retry_config(self) -> None:
        planner, _ = _make_planner()
        assert planner._retry_config.max_retries == 3

    def test_custom_retry_config(self) -> None:
        cfg = ValidationRetryConfig(max_retries=5, retry_prompt_template="Fix: {errors}")
        planner, _ = _make_planner(retry_config=cfg)
        assert planner._retry_config.max_retries == 5

    def test_planner_is_planner_protocol(self) -> None:
        from aios.runtime.planner.base import PlannerProtocol
        planner, _ = _make_planner()
        assert isinstance(planner, PlannerProtocol)


class TestPlannerBuildPlan:
    def test_fills_missing_step_ids(self) -> None:
        planner, _ = _make_planner()
        parsed = {
            "goal": "test",
            "steps": [
                {"description": "A"},
                {"description": "B"},
            ],
        }
        plan = planner._build_plan("test", parsed)
        assert len(plan.steps) == 2
        assert plan.steps[0].id == "step-1"
        assert plan.steps[1].id == "step-2"

    def test_preserves_explicit_step_ids(self) -> None:
        planner, _ = _make_planner()
        parsed = {
            "goal": "test",
            "steps": [
                {"id": "custom-id", "description": "A"},
            ],
        }
        plan = planner._build_plan("test", parsed)
        assert plan.steps[0].id == "custom-id"

    def test_generates_uuid_plan_id(self) -> None:
        planner, _ = _make_planner()
        plan1 = planner._build_plan("test", {"goal": "t", "steps": []})
        plan2 = planner._build_plan("test", {"goal": "t", "steps": []})
        assert plan1.id != plan2.id
