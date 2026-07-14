from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aios.runtime.event_bus.base import EventBusProtocol, Events
from aios.runtime.event_bus.bus import EventBus
from aios.runtime.models import ExecutionResult, Intent, Plan
from aios.runtime.state_machine.base import StateMachineProtocol
from aios.runtime.state_machine.machine import StateMachine

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConfig:
    """Configuration for constructing a Runtime instance."""

    workspace_root: Path | None = None
    system_prompt: str | None = None
    permission_profile: str = "trusted"
    confirmation_callback: Any = None
    state_callback: Any = None
    max_iterations: int = 25
    token_limit: int = 128_000
    plugins_enabled: bool = False
    mcp_enabled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    
    # Dependencies required by core engines
    provider: Any | None = None
    tool_registry: Any | None = None


class Runtime:
    """
    Single entry point for all AIOS Runtime operations.

    Owns the lifecycle of all Runtime modules. Presentation layers
    (CLI, TUI, API, Desktop, Voice) construct a Runtime via
    RuntimeConfig and call its methods. Runtime wires sub-module
    dependencies on construction.

    Runtime is not yet wired into the existing CLI/TUI. This class
    is a pure addition — zero impact on existing code.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config
        self._event_bus: EventBusProtocol = EventBus()
        self._state_machine: StateMachineProtocol = StateMachine(event_bus=self._event_bus)

        self._initialized = False
        
        # Instantiate core modules
        self._context_manager = None
        self._planner = None
        self._executor = None
        
        if self._config.provider:
            from aios.context.manager import ContextManager
            self._context_manager = ContextManager(
                model_name=self._config.provider.model,
                token_limit=self._config.token_limit
            )
            
            from aios.runtime.planner.planner import Planner
            self._planner = Planner(
                llm_chat=self._config.provider.complete,
            )
            
        if self._config.provider and self._config.tool_registry:
            from aios.executor.engine import ExecutionEngine
            from aios.permissions.manager import PermissionManager
            from aios.permissions.profiles import get_trusted_policy, get_strict_policy, get_yolo_policy_fixed
            from aios.hooks.manager import HookManager
            
            policy = get_trusted_policy()
            if self._config.permission_profile == "strict":
                policy = get_strict_policy()
            elif self._config.permission_profile == "yolo":
                policy = get_yolo_policy_fixed()
                
            self._executor = ExecutionEngine(
                provider=self._config.provider,
                tool_registry=self._config.tool_registry,
                permission_manager=PermissionManager(policy),
                hook_manager=HookManager(),
                system_prompt=self._config.system_prompt,
                workspace_root=self._config.workspace_root,
                confirmation_callback=self._config.confirmation_callback,
                state_callback=self._config.state_callback,
                mcp_servers=[] if not self._config.mcp_enabled else None,
            )
            # Share the context manager
            if self._context_manager:
                self._executor.context_manager = self._context_manager


    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Initialize all sub-modules."""
        if self._initialized:
            return
        self._initialized = True
        await self._event_bus.emit(Events.RuntimeStarted(source="runtime", config_snapshot=self._snapshot_config()))
        logger.info("Runtime started")

    async def stop(self) -> None:
        """Tear down all sub-modules."""
        if not self._initialized:
            return
        self._initialized = False
        await self._event_bus.emit(Events.RuntimeStopped(source="runtime", reason="shutdown"))
        logger.info("Runtime stopped")

    async def __aenter__(self) -> Runtime:
        await self.start()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()

    # ── Module access (dependency injection ready) ─────────────────────

    @property
    def event_bus(self) -> EventBusProtocol:
        return self._event_bus

    @property
    def state_machine(self) -> StateMachineProtocol:
        return self._state_machine

    @property
    def planner(self) -> Any:
        if not self._planner:
            raise RuntimeError("Planner requires a provider to be configured")
        return self._planner

    @property
    def executor(self) -> Any:
        if not self._executor:
            raise RuntimeError("Executor requires provider and tool_registry to be configured")
        return self._executor

    @property
    def tool_executor(self) -> Any:
        raise NotImplementedError("ToolExecutor not yet implemented — see Phase 3")

    @property
    def permission_gate(self) -> Any:
        raise NotImplementedError("PermissionGate not yet implemented — see Phase 2")

    @property
    def context_manager(self) -> Any:
        if not self._context_manager:
            raise RuntimeError("ContextManager requires a provider to be configured")
        return self._context_manager

    @property
    def provider_router(self) -> Any:
        raise NotImplementedError("ProviderRouter not yet implemented — see Phase 2")

    @property
    def workspace_knowledge(self) -> Any:
        raise NotImplementedError("WorkspaceKnowledge not yet implemented — see Phase 8")

    @property
    def mission_engine(self) -> Any:
        raise NotImplementedError("MissionEngine not yet implemented — see Phase 9")

    @property
    def intent_engine(self) -> Any:
        raise NotImplementedError("IntentEngine not yet implemented — see Phase 7")

    @property
    def memory_orchestrator(self) -> Any:
        raise NotImplementedError("MemoryOrchestrator not yet implemented — see Phase 4")

    @property
    def prompt_assembler(self) -> Any:
        raise NotImplementedError("PromptAssembler not yet implemented — see Phase 4")

    # ── High-level operations ──────────────────────────────────────────

    async def chat(
        self,
        conversation: Any,
        stream_callback: Any | None = None,
    ) -> str:
        """
        Single-turn or multi-turn chat. No planning — the executor
        runs the agent loop until the LLM provides a final answer.
        """
        if not self._executor:
            raise RuntimeError("chat() requires Executor — provider and tool_registry must be configured")
        return await self._executor.run(
            conversation=conversation, 
            max_iterations=self._config.max_iterations, 
            stream_callback=stream_callback
        )

    async def execute_plan(
        self,
        plan: Plan,
        conversation: Any,
        stream_callback: Any | None = None,
    ) -> ExecutionResult:
        """Execute a pre-defined Plan. Used after Planner.plan() + user review."""
        raise NotImplementedError("execute_plan() requires MissionEngine — see Phase 9")

    async def run_mission(
        self,
        goal: str,
        conversation: Any,
    ) -> AsyncIterator[Any]:
        """Decompose goal into a plan, execute each step. Yields progress events."""
        from aios.runtime.models import PlanningContext, PlanStatus
        from aios.core.models import Role
        
        if not self._planner or not self._executor:
            raise RuntimeError("Planner and Executor required for run_mission")
            
        context = PlanningContext(
            workspace_root=self._config.workspace_root or Path.cwd(),
            available_tools=[t.name for t in self._config.tool_registry.list()],
            conversation_history="",  # Ideally serialize the conversation here
        )
        
        yield {"event": "planning", "goal": goal}
        
        # 1. Plan
        plan = await self._planner.plan(goal, context)
        if plan.status == PlanStatus.FAILED:
            yield {"event": "error", "message": "Planning failed."}
            return
            
        yield {"event": "plan_created", "plan": plan}
        
        # 2. Execute
        for step in plan.steps:
            yield {"event": "step_started", "step": step}
            
            # Focus the LLM on this specific step
            step_instruction = (
                f"Execute the following step: {step.description}\n"
                f"Expected outcome: {step.expected_outcome}\n"
                f"Target tool: {step.tool_name or 'LLM only'}\n"
                f"Please focus only on this step. When done, output a final answer summarizing the result."
            )
            conversation.add(Role.USER, step_instruction)
            
            # Execute
            result = await self._executor.run(
                conversation=conversation, 
                max_iterations=self._config.max_iterations
            )
            
            yield {"event": "step_completed", "step": step, "result": result}
            
        yield {"event": "mission_completed", "plan": plan}

    async def classify_intent(self, text: str) -> Intent:
        """Classify user input into an intent category."""
        raise NotImplementedError("classify_intent() requires IntentEngine — see Phase 7")

    # ── Internal helpers ───────────────────────────────────────────────

    def _snapshot_config(self) -> dict[str, Any]:
        return {
            "workspace_root": str(self._config.workspace_root) if self._config.workspace_root else None,
            "permission_profile": self._config.permission_profile,
            "max_iterations": self._config.max_iterations,
            "token_limit": self._config.token_limit,
            "plugins_enabled": self._config.plugins_enabled,
            "mcp_enabled": self._config.mcp_enabled,
        }
