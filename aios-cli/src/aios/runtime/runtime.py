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
        self._permission_gate = None
        self._provider_router = None
        self._mission_engine = None
        self._workspace_knowledge = None
        self._memory_orchestrator = None
        self._prompt_assembler = None
        self._intent_engine = None
        
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
            from aios.hooks.manager import HookManager
            from aios.permissions.manager import PermissionManager
            from aios.permissions.profiles import get_strict_policy, get_trusted_policy, get_yolo_policy_fixed
            
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

            from aios.runtime.permission_gate.gate import PermissionGate
            self._permission_gate = PermissionGate(event_bus=self._event_bus)
            if self._config.confirmation_callback:
                self._permission_gate.set_confirmation_callback(self._config.confirmation_callback)

            from aios.runtime.capability_registry.registry import CapabilityRegistry
            from aios.runtime.provider_health.health import ProviderHealth
            from aios.runtime.provider_metrics.metrics import ProviderMetrics
            from aios.runtime.provider_router.router import ProviderRouter

            self._provider_router = ProviderRouter(
                capability_registry=CapabilityRegistry(),
                provider_health=ProviderHealth(event_bus=self._event_bus),
                provider_metrics=ProviderMetrics(event_bus=self._event_bus),
                event_bus=self._event_bus,
            )

            from aios.runtime.workspace_knowledge.engine import WorkspaceKnowledgeEngine
            from aios.tools.workspace_search import WorkspaceSearchTool
            
            self._workspace_knowledge = WorkspaceKnowledgeEngine(self._config.workspace_root or Path.cwd())
            self._config.tool_registry.register(WorkspaceSearchTool(self._workspace_knowledge))
            
            from aios.memory.orchestrator import MemoryOrchestrator
            from aios.runtime.prompt_assembler.default import DefaultPromptAssembler
            
            self._memory_orchestrator = MemoryOrchestrator(self._config.workspace_root)
            self._prompt_assembler = DefaultPromptAssembler(self._memory_orchestrator)
            
            from aios.tools.memory_tool import MemoryTool
            self._config.tool_registry.register(MemoryTool(self._memory_orchestrator.long_term))

            from aios.calendar.engine import CalendarEngine
            from aios.tools.calendar_tool import CalendarTool
            
            calendar_db_path = Path.home() / ".aios" / "calendar.db"
            self._calendar_engine = CalendarEngine(calendar_db_path)
            self._config.tool_registry.register(CalendarTool(self._calendar_engine))

            from aios.timer.engine import TimerEngine
            from aios.tools.timer_tool import TimerTool
            
            self._timer_engine = TimerEngine()
            self._config.tool_registry.register(TimerTool(self._timer_engine))

            from aios.runtime.mission_engine.engine import MissionEngine
            self._mission_engine = MissionEngine(
                planner=self._planner,
                executor=self._executor,
                context_manager=self._context_manager,
                event_bus=self._event_bus,
                max_iterations_per_step=self._config.max_iterations,
            )
            
            from aios.runtime.intent_engine.engine import IntentEngine
            self._intent_engine = IntentEngine(llm_chat=self._config.provider.complete)

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
        raise RuntimeError("ToolExecutor is not available in this release")

    @property
    def permission_gate(self) -> Any:
        if not self._permission_gate:
            raise RuntimeError("PermissionGate not initialized")
        return self._permission_gate

    @property
    def context_manager(self) -> Any:
        if not self._context_manager:
            raise RuntimeError("ContextManager requires a provider to be configured")
        return self._context_manager

    @property
    def provider_router(self) -> Any:
        if not self._provider_router:
            raise RuntimeError("ProviderRouter not initialized")
        return self._provider_router

    @property
    def workspace_knowledge(self) -> Any:
        if not self._workspace_knowledge:
            raise RuntimeError("WorkspaceKnowledge not initialized")
        return self._workspace_knowledge

    @property
    def mission_engine(self) -> Any:
        if not self._mission_engine:
            raise RuntimeError("MissionEngine not initialized")
        return self._mission_engine

    @property
    def intent_engine(self) -> Any:
        if not self._intent_engine:
            raise RuntimeError("IntentEngine not initialized")
        return self._intent_engine

    @property
    def memory_orchestrator(self) -> Any:
        if not self._memory_orchestrator:
            raise RuntimeError("MemoryOrchestrator not initialized")
        return self._memory_orchestrator

    @property
    def prompt_assembler(self) -> Any:
        if not self._prompt_assembler:
            raise RuntimeError("PromptAssembler not initialized")
        return self._prompt_assembler

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
        raise RuntimeError("execute_plan is not available in this release")

    async def run_mission(
        self,
        goal: str,
        conversation: Any,
    ) -> AsyncIterator[Any]:
        """Decompose goal into a plan, execute each step. Yields progress events."""
        if not self._mission_engine:
            raise RuntimeError("MissionEngine not initialized")
        
        mission = await self._mission_engine.create_mission(goal, conversation)
        async for event in self._mission_engine.execute_mission(mission):
            yield event

    async def classify_intent(self, text: str) -> Intent:
        """Classify user input into an intent category."""
        if not self._intent_engine:
            raise RuntimeError("IntentEngine not initialized")
        return await self._intent_engine.classify_intent(text)

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
