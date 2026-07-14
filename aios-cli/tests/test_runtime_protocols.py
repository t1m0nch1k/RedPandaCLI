from __future__ import annotations

from pathlib import Path

from aios.runtime import (
    AgentState,
    CompactionStrategy,
    ExecutionState,
    Capability,
    CommitInfo,
    ContextManagerProtocol,
    ContextStatus,
    Dependency,
    DependencyGraph,
    EntryPoint,
    Event,
    EventBusProtocol,
    Events,
    ExecutionResult,
    ExecutorProtocol,
    FileEntry,
    FrameworkInfo,
    GitContext,
    Intent,
    IntentCategory,
    IntentEngineProtocol,
    IntentResult,
    IntentStage,
    MemoryOrchestratorProtocol,
    MemorySource,
    Mission,
    MissionCheckpoint,
    MissionEngineProtocol,
    MissionEvent,
    MissionStatus,
    MissionSummary,
    PackageManager,
    PermissionDecision,
    PermissionGateProtocol,
    Plan,
    PlannerProtocol,
    Planner,
    PlanningContext,
    PlanStatus,
    PromptAssemblerProtocol,
    ProviderRouterProtocol,
    ProviderSelection,
    RoutingConstraints,
    RoutingStrategy,
    SearchResult,
    StateMachineProtocol,
    StateTransitionError,
    Step,
    StepResult,
    StepStatus,
    SubAgentResult,
    SubAgentTask,
    SymbolLocation,
    TaskDescriptor,
    TestConfig,
    ToolCall,
    ToolCallDef,
    ToolExecutorProtocol,
    ValidationResult,
    ValidationRetryConfig,
    WorkspaceKnowledgeProtocol,
)


class TestStrEnums:
    """Verify all StrEnum types have expected values."""

    def test_execution_state_values(self) -> None:
        assert ExecutionState.IDLE == "idle"
        assert ExecutionState.THINKING == "thinking"
        assert ExecutionState.TOOL == "tool"
        assert ExecutionState.ERROR == "error"
        assert ExecutionState.DONE == "done"

    def test_execution_state_count(self) -> None:
        assert len(ExecutionState) == 5

    def test_agent_state_values(self) -> None:
        assert AgentState.IDLE == "idle"
        assert AgentState.PLANNING == "planning"
        assert AgentState.WAITING_APPROVAL == "waiting_approval"
        assert AgentState.EXECUTING == "executing"
        assert AgentState.RUNNING_TOOL == "running_tool"
        assert AgentState.OBSERVING == "observing"
        assert AgentState.REVIEWING == "reviewing"
        assert AgentState.REPLANNING == "replanning"
        assert AgentState.COMPLETED == "completed"
        assert AgentState.FAILED == "failed"
        assert AgentState.INTERRUPTED == "interrupted"

    def test_capability_values(self) -> None:
        assert Capability.CHAT == "chat"
        assert Capability.TOOLS == "tools"
        assert Capability.STREAMING == "streaming"
        assert Capability.VISION == "vision"
        assert Capability.STRUCTURED_OUTPUT == "structured_output"
        assert Capability.CODE_GENERATION == "code_generation"
        assert Capability.LONG_CONTEXT == "long_context"

    def test_routing_strategy_values(self) -> None:
        assert RoutingStrategy.COST_FIRST == "cost_first"
        assert RoutingStrategy.LATENCY_FIRST == "latency_first"
        assert RoutingStrategy.CAPABILITY_FIRST == "capability_first"
        assert RoutingStrategy.MANUAL == "manual"

    def test_intent_category_values(self) -> None:
        assert IntentCategory.CHAT == "chat"
        assert IntentCategory.CODE_TASK == "code_task"
        assert IntentCategory.FILE_OPERATION == "file_op"
        assert IntentCategory.QUESTION == "question"
        assert IntentCategory.COMMAND == "command"
        assert IntentCategory.PLAN == "plan"
        assert IntentCategory.MISSION == "mission"
        assert IntentCategory.CONTINUATION == "continuation"
        assert IntentCategory.UNKNOWN == "unknown"

    def test_step_status_values(self) -> None:
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.SUCCEEDED == "succeeded"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"
        assert StepStatus.CANCELLED == "cancelled"

    def test_plan_status_values(self) -> None:
        assert PlanStatus.PENDING == "pending"
        assert PlanStatus.APPROVED == "approved"
        assert PlanStatus.RUNNING == "running"
        assert PlanStatus.COMPLETED == "completed"
        assert PlanStatus.FAILED == "failed"
        assert PlanStatus.CANCELLED == "cancelled"

    def test_mission_status_values(self) -> None:
        assert MissionStatus.CREATED == "created"
        assert MissionStatus.PLANNING == "planning"
        assert MissionStatus.WAITING_APPROVAL == "waiting_approval"
        assert MissionStatus.EXECUTING == "executing"
        assert MissionStatus.PAUSED == "paused"
        assert MissionStatus.COMPLETED == "completed"
        assert MissionStatus.FAILED == "failed"
        assert MissionStatus.CANCELLED == "cancelled"

    def test_permission_decision_values(self) -> None:
        assert PermissionDecision.ALLOWED == "allowed"
        assert PermissionDecision.DENIED == "denied"
        assert PermissionDecision.REQUIRES_CONFIRMATION == "requires_confirmation"

    def test_agent_state_count(self) -> None:
        assert len(AgentState) == 11


class TestTransitionTable:
    """Verify TRANSITION_TABLE is complete and consistent."""

    def test_all_states_have_entries(self) -> None:
        from aios.runtime.models import TRANSITION_TABLE

        for state in AgentState:
            assert state in TRANSITION_TABLE, f"Missing transition entry for {state}"

    def test_all_transitions_are_valid_states(self) -> None:
        from aios.runtime.models import TRANSITION_TABLE

        valid_states = set(AgentState)
        for src, targets in TRANSITION_TABLE.items():
            for t in targets:
                assert t in valid_states, f"Invalid target state {t} from {src}"

    def test_interrupted_goes_to_idle_only(self) -> None:
        from aios.runtime.models import TRANSITION_TABLE

        assert TRANSITION_TABLE[AgentState.INTERRUPTED] == {AgentState.IDLE}

    def test_completed_goes_to_idle_or_interrupted(self) -> None:
        from aios.runtime.models import TRANSITION_TABLE

        assert TRANSITION_TABLE[AgentState.COMPLETED] == {AgentState.IDLE, AgentState.INTERRUPTED}

    def test_idle_to_executing_is_direct(self) -> None:
        from aios.runtime.models import TRANSITION_TABLE

        assert AgentState.EXECUTING in TRANSITION_TABLE[AgentState.IDLE]


class TestDataModels:
    """Verify all dataclass models can be constructed with default values."""

    def test_event_defaults(self) -> None:
        event = Event()
        assert event.id
        assert event.source == ""
        assert event.payload is None

    def test_step_frozen(self) -> None:
        step = Step(id="s1", description="test step")
        assert step.id == "s1"
        assert step.description == "test step"
        assert step.tool_name is None
        assert step.dependencies == ()

    def test_plan_defaults(self) -> None:
        plan = Plan(id="p1", goal="test", steps=[])
        assert plan.id == "p1"
        assert plan.goal == "test"
        assert plan.status == PlanStatus.PENDING
        assert plan.parallel_groups == []

    def test_plan_with_steps(self) -> None:
        step_a = Step(id="a", description="step a")
        step_b = Step(id="b", description="step b", dependencies=("a",))
        plan = Plan(id="p1", goal="test", steps=[step_a, step_b])
        assert len(plan.steps) == 2
        assert plan.steps[0].id == "a"
        assert plan.steps[1].dependencies == ("a",)

    def test_planning_context_defaults(self) -> None:
        ctx = PlanningContext(workspace_root=Path("/"), available_tools=["echo"])
        assert ctx.max_steps == 10
        assert ctx.mission_mode is False
        assert ctx.checkpoint_enabled is False

    def test_validation_result_defaults(self) -> None:
        r = ValidationResult(valid=True)
        assert r.valid
        assert r.errors == []
        assert r.warnings == []

    def test_execution_result_defaults(self) -> None:
        r = ExecutionResult()
        assert r.success
        assert r.iterations == 0
        assert r.error is None

    def test_step_result_defaults(self) -> None:
        r = StepResult(step_id="s1")
        assert r.step_id == "s1"
        assert r.status == StepStatus.PENDING
        assert r.error is None

    def test_intent_construction(self) -> None:
        intent = Intent(category=IntentCategory.CHAT, confidence=0.95, raw_text="hello")
        assert intent.category == IntentCategory.CHAT
        assert intent.confidence == 0.95
        assert intent.parsed_args == {}

    def test_intent_result_defaults(self) -> None:
        r = IntentResult()
        assert r.handled is False
        assert r.intent is None

    def test_mission_construction(self) -> None:
        plan = Plan(id="p1", goal="test", steps=[])
        mission = Mission(id="m1", goal="test", plan=plan, total_steps=0)
        assert mission.id == "m1"
        assert mission.status == MissionStatus.CREATED
        assert mission.current_step_index == 0

    def test_mission_summary_defaults(self) -> None:
        s = MissionSummary(id="m1", goal="test", status=MissionStatus.CREATED)
        assert s.progress == 0.0
        assert s.error is None

    def test_mission_event_defaults(self) -> None:
        e = MissionEvent(mission_id="m1", type="step_start")
        assert e.step_id is None
        assert e.error is None

    def test_mission_checkpoint_defaults(self) -> None:
        c = MissionCheckpoint(mission_id="m1")
        assert c.goal == ""
        assert c.completed_step_ids == []
        assert c.artifacts == {}

    def test_mission_deadline_support(self) -> None:
        plan = Plan(id="p1", goal="test", steps=[])
        mission = Mission(id="m1", goal="test", plan=plan, deadline=1000.0, failure_policy="retry")
        assert mission.deadline == 1000.0
        assert mission.failure_policy == "retry"

    def test_sub_agent_task_defaults(self) -> None:
        t = SubAgentTask(goal="test", instructions="do x")
        assert t.timeout_s == 120
        assert t.sub_agent_id == ""
        assert t.max_cost is None
        assert t.max_tool_calls is None

    def test_sub_agent_task_with_limits(self) -> None:
        t = SubAgentTask(goal="test", instructions="do x", max_cost=0.5, max_tool_calls=20)
        assert t.max_cost == 0.5
        assert t.max_tool_calls == 20

    def test_sub_agent_result_defaults(self) -> None:
        r = SubAgentResult()
        assert r.success is False
        assert r.artifacts is None

    def test_routing_constraints_defaults(self) -> None:
        c = RoutingConstraints()
        assert c.max_cost_per_request is None
        assert c.requires_streaming is False

    def test_provider_selection_defaults(self) -> None:
        s = ProviderSelection(provider_name="openai", model_name="gpt-4o")
        assert s.estimated_cost_per_request == 0.0
        assert s.capabilities == frozenset()

    def test_task_descriptor_defaults(self) -> None:
        d = TaskDescriptor()
        assert d.input_tokens == 0
        assert d.requires_tools is False
        assert d.capabilities == set()

    def test_context_status_defaults(self) -> None:
        s = ContextStatus()
        assert s.total_tokens == 0
        assert s.compacted is False
        assert s.warning is None
        assert s.budget_limit == 0
        assert s.budget_reserved == 0
        assert s.compaction_count == 0

    def test_context_status_budget_fields(self) -> None:
        s = ContextStatus(total_tokens=5000, budget_limit=128000, budget_reserved=2048, compaction_count=3)
        assert s.budget_limit == 128000
        assert s.budget_reserved == 2048
        assert s.compaction_count == 3

    def test_planning_context_token_fields(self) -> None:
        ctx = PlanningContext(workspace_root=Path("/x"), available_tools=[], available_tokens=32000)
        assert ctx.available_tokens == 32000
        assert ctx.reserved_output_tokens == 2048

    def test_validation_result_extended(self) -> None:
        r = ValidationResult(valid=False, errors=["bad"], parse_error=True, raw_llm_output='{"malformed": ')
        assert r.parse_error is True
        assert r.raw_llm_output.startswith('{"malformed"')

    def test_validation_retry_config_defaults(self) -> None:
        cfg = ValidationRetryConfig()
        assert cfg.max_retries == 3
        assert "errors" in cfg.retry_prompt_template

    def test_validation_retry_config_custom(self) -> None:
        cfg = ValidationRetryConfig(max_retries=5, retry_prompt_template="Fix: {errors}")
        assert cfg.max_retries == 5
        assert cfg.retry_prompt_template == "Fix: {errors}"

    def test_symbol_location_defaults(self) -> None:
        loc = SymbolLocation(symbol="foo", kind="function", file_path="/a.py", line=10)
        assert loc.column == 0

    def test_search_result_defaults(self) -> None:
        r = SearchResult(file_path="/a.py")
        assert r.line == 0

    def test_file_entry_defaults(self) -> None:
        e = FileEntry(name="foo.py", path="/foo.py", kind="file")
        assert e.size is None

    def test_framework_info_defaults(self) -> None:
        info = FrameworkInfo(name="pytest")
        assert info.version is None

    def test_dependency_graph_defaults(self) -> None:
        g = DependencyGraph(root=Path("/"), manager="pip")
        assert g.dependencies == []

    def test_dependency_defaults(self) -> None:
        d = Dependency(name="requests")
        assert d.version_spec is None
        assert d.is_optional is False

    def test_package_manager_defaults(self) -> None:
        pm = PackageManager(name="pip", config_paths=[Path("requirements.txt")])
        assert pm.lock_file is None

    def test_test_config_defaults(self) -> None:
        tc = TestConfig(framework="pytest")
        assert tc.test_pattern == "test_*.py"

    def test_entry_point_defaults(self) -> None:
        ep = EntryPoint(path=Path("main.py"), name="main")
        assert ep.kind == ""

    def test_git_context_defaults(self) -> None:
        gc = GitContext()
        assert gc.branch == ""
        assert gc.is_dirty is False
        assert gc.staged_files == []

    def test_commit_info_defaults(self) -> None:
        ci = CommitInfo()
        assert ci.hash == ""
        assert ci.date is None
        assert ci.files_changed == []

    def test_tool_call_defaults(self) -> None:
        tc = ToolCall(id="1", name="echo")
        assert tc.args == {}

    def test_tool_call_def_defaults(self) -> None:
        tcd = ToolCallDef(name="echo")
        assert tcd.args == {}


class TestEvents:
    """Verify Events are proper Event subclasses."""

    def test_all_event_types_are_events(self) -> None:
        event_types = [
            Events.SessionStart,
            Events.SessionEnd,
            Events.RuntimeStarted,
            Events.RuntimeStopped,
            Events.StateChange,
            Events.PlanCreated,
            Events.PlanApproved,
            Events.PlanRejected,
            Events.StepStarted,
            Events.StepCompleted,
            Events.StepFailed,
            Events.ExecutionComplete,
            Events.ExecutionCancelled,
            Events.ToolExecution,
            Events.PermissionRequired,
            Events.ModelCall,
            Events.ProviderFallback,
            Events.IntentClassified,
            Events.MissionProgress,
            Events.MissionPaused,
            Events.MissionResumed,
            Events.MissionComplete,
            Events.MissionFailed,
            Events.SubAgentSpawned,
            Events.IndexBuilt,
            Events.FileModified,
            Events.FactAdded,
            Events.Error,
        ]
        for et in event_types:
            instance = et()
            assert isinstance(instance, Event), f"{et.__name__} is not an Event instance"
            assert instance.id, f"{et.__name__} has no id"

    def test_session_start_event(self) -> None:
        e = Events.SessionStart(session_id="sess-1")
        assert e.session_id == "sess-1"

    def test_tool_execution_event(self) -> None:
        e = Events.ToolExecution(tool_name="echo", permission="allowed")
        assert e.tool_name == "echo"
        assert e.permission == "allowed"

    def test_error_event_defaults(self) -> None:
        e = Events.Error(module="test", exception="fail")
        assert e.recoverable is True


class TestProtocols:
    """Verify all protocol classes can be imported and instantiated."""

    def test_event_bus_protocol(self) -> None:
        p = EventBusProtocol()
        assert isinstance(p, EventBusProtocol)

    def test_state_machine_protocol(self) -> None:
        p = StateMachineProtocol()
        assert isinstance(p, StateMachineProtocol)

    def test_planner_protocol(self) -> None:
        p = PlannerProtocol()
        assert isinstance(p, PlannerProtocol)

    def test_executor_protocol(self) -> None:
        p = ExecutorProtocol()
        assert isinstance(p, ExecutorProtocol)

    def test_tool_executor_protocol(self) -> None:
        p = ToolExecutorProtocol()
        assert isinstance(p, ToolExecutorProtocol)

    def test_permission_gate_protocol(self) -> None:
        p = PermissionGateProtocol()
        assert isinstance(p, PermissionGateProtocol)

    def test_context_manager_protocol(self) -> None:
        p = ContextManagerProtocol()
        assert isinstance(p, ContextManagerProtocol)

    def test_provider_router_protocol(self) -> None:
        p = ProviderRouterProtocol()
        assert isinstance(p, ProviderRouterProtocol)

    def test_workspace_knowledge_protocol(self) -> None:
        p = WorkspaceKnowledgeProtocol()
        assert isinstance(p, WorkspaceKnowledgeProtocol)

    def test_mission_engine_protocol(self) -> None:
        p = MissionEngineProtocol()
        assert isinstance(p, MissionEngineProtocol)

    def test_intent_engine_protocol(self) -> None:
        p = IntentEngineProtocol()
        assert isinstance(p, IntentEngineProtocol)

    def test_memory_orchestrator_protocol(self) -> None:
        p = MemoryOrchestratorProtocol()
        assert isinstance(p, MemoryOrchestratorProtocol)

    def test_prompt_assembler_protocol(self) -> None:
        p = PromptAssemblerProtocol()
        assert isinstance(p, PromptAssemblerProtocol)

    def test_intent_stage(self) -> None:
        s = IntentStage()
        assert isinstance(s, IntentStage)

    def test_memory_source(self) -> None:
        s = MemorySource()
        assert isinstance(s, MemorySource)

    def test_state_transition_error(self) -> None:
        try:
            raise StateTransitionError("invalid transition")
        except StateTransitionError as e:
            assert str(e) == "invalid transition"


class TestImports:
    """Verify all runtime package imports work."""

    def test_runtime_package_import(self) -> None:
        import aios.runtime

        assert hasattr(aios.runtime, "PlannerProtocol")
        assert hasattr(aios.runtime, "Planner")
        assert hasattr(aios.runtime, "EventBusProtocol")
        assert hasattr(aios.runtime, "StateMachineProtocol")

    def test_runtime_models_import(self) -> None:
        import aios.runtime.models

        assert hasattr(aios.runtime.models, "AgentState")
        assert hasattr(aios.runtime.models, "TRANSITION_TABLE")
        assert hasattr(aios.runtime.models, "Event")

    def test_all_module_imports(self) -> None:
        """Verify every sub-module can be imported."""
        modules = [
            "aios.runtime.event_bus.base",
            "aios.runtime.state_machine.base",
            "aios.runtime.planner.base",
            "aios.runtime.executor.base",
            "aios.runtime.tool_executor.base",
            "aios.runtime.permission_gate.base",
            "aios.runtime.context_manager.base",
            "aios.runtime.provider_router.base",
            "aios.runtime.workspace_knowledge.base",
            "aios.runtime.mission_engine.base",
            "aios.runtime.intent_engine.base",
            "aios.runtime.memory_orchestrator.base",
            "aios.runtime.prompt_assembler.base",
        ]
        from importlib import import_module

        for mod_name in modules:
            mod = import_module(mod_name)
            assert mod is not None
