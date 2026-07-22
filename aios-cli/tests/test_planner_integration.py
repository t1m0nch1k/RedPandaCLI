from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aios.runtime.models import (
    Plan,
    PlanningContext,
    PlanStatus,
    Step,
    ValidationRetryConfig,
)
from aios.runtime.planner.planner import Planner
from aios.runtime.workspace_knowledge.base import WorkspaceKnowledgeProtocol


class FakeWorkspace(WorkspaceKnowledgeProtocol):
    """Minimal WorkspaceKnowledgeImplementation for integration testing."""

    def __init__(self) -> None:
        self._frameworks: list[Any] = []
        self._deps: Any = None
        self._entry_points: list[Any] = []
        self._git: Any = None
        self._raise_on_detect = False

    async def detect_frameworks(self) -> list[Any]:
        if self._raise_on_detect:
            raise RuntimeError("WK unavailable")
        return self._frameworks

    async def dependency_graph(self) -> Any:
        return self._deps

    async def entry_points(self) -> list[Any]:
        return self._entry_points

    async def git_context(self) -> Any:
        return self._git

    @property
    def workspace_root(self) -> Path:
        return Path("/fake")

    async def build_index(self) -> None:
        pass

    async def query_symbol(self, symbol: str) -> list:
        return []

    async def file_context(self, path: str, start_line: int = 0, end_line: int | None = None) -> str:
        return ""

    async def repo_map(self, max_tokens: int = 1024) -> str:
        return ""

    async def search_text(self, pattern: str, include: str | None = None) -> list:
        return []

    async def list_directory(self, path: str = ".") -> list:
        return []

    async def package_managers(self) -> list:
        return []

    async def test_config(self) -> None:
        return None

    async def git_history(self, path: str | None = None, max_commits: int = 20) -> list:
        return []


def _make_planner(
    llm_response: str,
    workspace: WorkspaceKnowledgeProtocol | None = None,
    retry_config: ValidationRetryConfig | None = None,
) -> tuple[Planner, list[list[dict]]]:
    calls: list[list[dict]] = []

    async def chat(messages: list[dict]) -> str:
        calls.append(messages)
        return llm_response

    planner = Planner(
        llm_chat=chat,
        workspace=workspace,
        retry_config=retry_config,
    )
    return planner, calls


CONTEXT = PlanningContext(
    workspace_root=Path("/workspace"),
    available_tools=["bash", "read", "write", "edit", "search", "list_dir"],
    max_steps=10,
)


class TestIntegrationFullFlow:
    async def test_plan_validate_serialize_deserialize_flow(self) -> None:
        llm_response = json.dumps({
            "goal": "Build a Python CLI tool",
            "steps": [
                {
                    "id": "step-1",
                    "description": "Create project structure",
                    "tool_name": "bash",
                    "args": {"command": "mkdir -p cli_tool"},
                    "dependencies": [],
                    "expected_outcome": "Directory created",
                },
                {
                    "id": "step-2",
                    "description": "Write main CLI entry point",
                    "tool_name": "write",
                    "dependencies": ["step-1"],
                    "expected_outcome": "cli.py created",
                },
                {
                    "id": "step-3",
                    "description": "Install dependencies",
                    "tool_name": "bash",
                    "args": {"command": "pip install click"},
                    "dependencies": ["step-1"],
                    "expected_outcome": "Click installed",
                },
            ],
            "parallel_groups": [],
            "estimated_complexity": "moderate",
        })
        planner, calls = _make_planner(llm_response)

        plan = await planner.plan("Build a Python CLI tool", CONTEXT)
        assert isinstance(plan, Plan)
        assert len(plan.steps) == 3
        assert plan.status == PlanStatus.PENDING

        validation = await planner.validate(plan)
        assert validation.valid is True
        assert validation.errors == []

        data = Planner.serialize(plan)
        restored = Planner.deserialize(data)
        assert restored.goal == plan.goal
        assert len(restored.steps) == len(plan.steps)
        assert restored.steps[0].dependencies == plan.steps[0].dependencies

        revalidate = await planner.validate(restored)
        assert revalidate.valid is True

    async def test_complex_dependency_chain(self) -> None:
        llm_response = json.dumps({
            "goal": "Deploy web app",
            "steps": [
                {"id": "s1", "description": "Build", "tool_name": "bash", "dependencies": [], "expected_outcome": "Built"},
                {"id": "s2", "description": "Test", "tool_name": "bash", "dependencies": ["s1"], "expected_outcome": "Tested"},
                {"id": "s3", "description": "Package", "tool_name": "bash", "dependencies": ["s2"], "expected_outcome": "Packaged"},
                {"id": "s4", "description": "Deploy", "tool_name": "bash", "dependencies": ["s3"], "expected_outcome": "Deployed"},
                {"id": "s5", "description": "Verify", "tool_name": "bash", "dependencies": ["s4"], "expected_outcome": "Verified"},
            ],
            "parallel_groups": [],
            "estimated_complexity": "moderate",
        })
        planner, _ = _make_planner(llm_response)
        plan = await planner.plan("Deploy web app", CONTEXT)
        validation = await planner.validate(plan)
        assert validation.valid is True

    async def test_plan_with_parallel_groups(self) -> None:
        llm_response = json.dumps({
            "goal": "Set up CI/CD",
            "steps": [
                {"id": "s1", "description": "Install tools", "tool_name": "bash", "dependencies": [], "expected_outcome": "Installed"},
                {"id": "s2", "description": "Configure linter", "tool_name": "write", "dependencies": ["s1"], "expected_outcome": "Configured"},
                {"id": "s3", "description": "Configure formatter", "tool_name": "write", "dependencies": ["s1"], "expected_outcome": "Configured"},
            ],
            "parallel_groups": [["s2", "s3"]],
            "estimated_complexity": "moderate",
        })
        planner, _ = _make_planner(llm_response)
        plan = await planner.plan("Set up CI/CD", CONTEXT)
        assert len(plan.parallel_groups) == 1
        assert "s2" in plan.parallel_groups[0]
        assert "s3" in plan.parallel_groups[0]

    async def test_replan_full_flow(self) -> None:
        original = Plan(
            id="p1",
            goal="Deploy app",
            steps=[
                Step(id="s1", description="Build", tool_name="bash", dependencies=(), expected_outcome="Built"),
                Step(id="s2", description="Deploy", tool_name="bash", dependencies=("s1",), expected_outcome="Deployed"),
            ],
        )
        replan_json = json.dumps({
            "goal": "Deploy app",
            "steps": [
                {"id": "s2", "description": "Deploy with Docker", "tool_name": "bash", "dependencies": ["s1"], "expected_outcome": "Deployed via Docker"},
                {"id": "s3", "description": "Verify deployment", "tool_name": "bash", "dependencies": ["s2"], "expected_outcome": "Verified"},
            ],
            "parallel_groups": [],
            "estimated_complexity": "moderate",
        })
        planner, _ = _make_planner(replan_json)
        revised = await planner.replan(original, "Build succeeded but deploy failed", CONTEXT)
        assert isinstance(revised, Plan)
        validation = await planner.validate(revised)
        assert validation.valid is True


class TestIntegrationWorkspaceKnowledge:
    async def test_workspace_context_injected_into_prompt(self) -> None:
        ws = FakeWorkspace()
        ws._frameworks = [type("FW", (), {"name": "FastAPI"})()]
        ws._deps = type("DG", (), {"manager": "pip", "root": Path("/project")})()
        ws._entry_points = [type("EP", (), {"name": "main.py"})()]
        ws._git = type("GC", (), {"branch": "main"})()

        llm_response = json.dumps({"goal": "test", "steps": []})
        planner, calls = _make_planner(llm_response, workspace=ws)

        await planner.plan("test", CONTEXT)
        prompt = calls[0][0].content
        assert "FastAPI" in prompt
        assert "pip" in prompt
        assert "main.py" in prompt
        assert "main" in prompt

    async def test_workspace_knowledge_fallback_on_error(self) -> None:
        ws = FakeWorkspace()
        ws._raise_on_detect = True

        llm_response = json.dumps({"goal": "test", "steps": []})
        planner, calls = _make_planner(llm_response, workspace=ws)

        plan = await planner.plan("test", CONTEXT)
        assert isinstance(plan, Plan)

    async def test_workspace_context_without_git(self) -> None:
        ws = FakeWorkspace()
        ws._frameworks = [type("FW", (), {"name": "Django"})()]
        ws._deps = type("DG", (), {"manager": "poetry", "root": Path("/app")})()

        llm_response = json.dumps({"goal": "test", "steps": []})
        planner, calls = _make_planner(llm_response, workspace=ws)

        await planner.plan("test", CONTEXT)
        prompt = calls[0][0].content
        assert "Django" in prompt
        assert "poetry" in prompt
        assert "app" in prompt


class TestIntegrationValidation:
    async def test_detect_self_referencing_cycle(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="A", dependencies=("s2",)),
                Step(id="s2", description="B", dependencies=("s3",)),
                Step(id="s3", description="C", dependencies=("s1",)),
            ],
        )
        planner, _ = _make_planner(json.dumps({"goal": "test", "steps": []}))
        result = await planner.validate(plan)
        assert result.valid is False
        assert len(result.errors) >= 1

    async def test_diamond_dependency_is_valid(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="Root", dependencies=()),
                Step(id="s2", description="Left", dependencies=("s1",)),
                Step(id="s3", description="Right", dependencies=("s1",)),
                Step(id="s4", description="Merge", dependencies=("s2", "s3")),
            ],
        )
        planner, _ = _make_planner("")
        result = await planner.validate(plan)
        assert result.valid is True

    async def test_detects_multiple_errors_simultaneously(self) -> None:
        plan = Plan(
            id="p1",
            goal="test",
            steps=[
                Step(id="s1", description="  ", dependencies=("ghost",)),
            ],
        )
        planner, _ = _make_planner("")
        result = await planner.validate(plan)
        assert result.valid is False
        assert len(result.errors) >= 2


class TestIntegrationLargePlan:
    async def test_generates_plan_with_many_steps(self) -> None:
        steps = [
            {
                "id": f"s{i}",
                "description": f"Step {i}",
                "tool_name": "bash" if i % 2 == 0 else "write",
                "dependencies": [f"s{i-1}"] if i > 0 else [],
                "expected_outcome": f"Done {i}",
            }
            for i in range(15)
        ]
        llm_response = json.dumps({
            "goal": "Large plan test",
            "steps": steps,
            "parallel_groups": [],
            "estimated_complexity": "complex",
        })
        planner, _ = _make_planner(llm_response)
        plan = await planner.plan("Large plan test", CONTEXT)
        assert len(plan.steps) == 15
        validation = await planner.validate(plan)
        assert validation.valid is True

    async def test_validates_serialized_large_plan(self) -> None:
        steps = [
            Step(id=f"s{i}", description=f"S{i}", tool_name="bash", dependencies=(f"s{i-1}",) if i > 0 else ())
            for i in range(20)
        ]
        plan = Plan(id="big", goal="big test", steps=steps)
        data = Planner.serialize(plan)
        restored = Planner.deserialize(data)
        assert len(restored.steps) == 20
        assert restored.steps[-1].dependencies == ("s18",)


class TestIntegrationEdgeCases:
    async def test_plan_with_no_available_tools(self) -> None:
        ctx = PlanningContext(
            workspace_root=Path("/x"),
            available_tools=[],
        )
        llm_response = json.dumps({
            "goal": "Think only",
            "steps": [{"id": "s1", "description": "Think", "tool_name": None, "dependencies": [], "expected_outcome": "Thought"}],
            "parallel_groups": [],
            "estimated_complexity": "simple",
        })
        planner, _ = _make_planner(llm_response)
        plan = await planner.plan("Think only", ctx)
        assert len(plan.steps) == 1
        assert plan.steps[0].tool_name is None

    async def test_retry_config_with_zero_retries(self) -> None:
        cfg = ValidationRetryConfig(max_retries=1)
        planner, calls = _make_planner(
            llm_response="bad json",
            retry_config=cfg,
        )
        plan = await planner.plan("test", CONTEXT)
        assert isinstance(plan, Plan)
        assert plan.status == PlanStatus.FAILED
        assert plan.goal == "test"
        assert len(calls) == 1
