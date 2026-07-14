from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

# ── Core Enums ──────────────────────────────────────────────────────────


class ExecutionState(StrEnum):
    """Simplified execution states for the legacy ExecutionEngine UI.

    Maps to the old AgentState in cli/branding. Runtime uses the richer
    11-state AgentState for the StateMachine.
    """

    IDLE = "idle"
    THINKING = "thinking"
    TOOL = "tool"
    ERROR = "error"
    DONE = "done"


class AgentState(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    RUNNING_TOOL = "running_tool"
    OBSERVING = "observing"
    REVIEWING = "reviewing"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


TRANSITION_TABLE: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.PLANNING, AgentState.EXECUTING, AgentState.INTERRUPTED},
    AgentState.PLANNING: {
        AgentState.WAITING_APPROVAL,
        AgentState.EXECUTING,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },
    AgentState.WAITING_APPROVAL: {
        AgentState.EXECUTING,
        AgentState.REPLANNING,
        AgentState.IDLE,
        AgentState.INTERRUPTED,
    },
    AgentState.EXECUTING: {
        AgentState.RUNNING_TOOL,
        AgentState.OBSERVING,
        AgentState.REVIEWING,
        AgentState.COMPLETED,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },
    AgentState.RUNNING_TOOL: {AgentState.OBSERVING, AgentState.FAILED, AgentState.INTERRUPTED},
    AgentState.OBSERVING: {
        AgentState.EXECUTING,
        AgentState.REVIEWING,
        AgentState.REPLANNING,
        AgentState.COMPLETED,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },
    AgentState.REVIEWING: {
        AgentState.EXECUTING,
        AgentState.REPLANNING,
        AgentState.COMPLETED,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },
    AgentState.REPLANNING: {
        AgentState.WAITING_APPROVAL,
        AgentState.EXECUTING,
        AgentState.FAILED,
        AgentState.INTERRUPTED,
    },
    AgentState.COMPLETED: {AgentState.IDLE, AgentState.INTERRUPTED},
    AgentState.FAILED: {AgentState.IDLE, AgentState.INTERRUPTED},
    AgentState.INTERRUPTED: {AgentState.IDLE},
}


class Capability(StrEnum):
    CHAT = "chat"
    TOOLS = "tools"
    STREAMING = "streaming"
    VISION = "vision"
    STRUCTURED_OUTPUT = "structured_output"
    CODE_GENERATION = "code_generation"
    LONG_CONTEXT = "long_context"


class RoutingStrategy(StrEnum):
    COST_FIRST = "cost_first"
    LATENCY_FIRST = "latency_first"
    CAPABILITY_FIRST = "capability_first"
    MANUAL = "manual"


class IntentCategory(StrEnum):
    CHAT = "chat"
    CODE_TASK = "code_task"
    FILE_OPERATION = "file_op"
    QUESTION = "question"
    COMMAND = "command"
    PLAN = "plan"
    MISSION = "mission"
    CONTINUATION = "continuation"
    UNKNOWN = "unknown"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PlanStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Event System ────────────────────────────────────────────────────────

EventHandler = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Any = None


# ── Planner / Plan ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Step:
    id: str
    description: str
    tool_name: str | None = None
    args: dict[str, Any] | None = None
    dependencies: tuple[str, ...] = ()
    expected_outcome: str = ""
    timeout_s: int = 60


@dataclass
class Plan:
    id: str
    goal: str
    steps: list[Step]
    parallel_groups: list[tuple[str, ...]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: PlanStatus = PlanStatus.PENDING


@dataclass
class PlanningContext:
    workspace_root: Path
    available_tools: list[str]
    conversation_history: str = ""
    max_steps: int = 10
    user_preferences: dict[str, Any] = field(default_factory=dict)
    mission_mode: bool = False
    checkpoint_enabled: bool = False
    available_tokens: int = 0
    reserved_output_tokens: int = 2_048


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_error: bool = False
    raw_llm_output: str = ""


@dataclass
class ValidationRetryConfig:
    max_retries: int = 3
    retry_prompt_template: str = (
        "The previous plan had validation errors: {errors}\n"
        "Please fix and provide a corrected plan as JSON."
    )


# ── Executor ────────────────────────────────────────────────────────────


@dataclass
class ExecutionResult:
    conversation: Any = None
    final_content: str = ""
    iterations: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: str | None = None


@dataclass
class StepResult:
    step_id: str
    status: StepStatus = StepStatus.PENDING
    content: str = ""
    tool_results: list[Any] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    error: str | None = None


# ── Intent ──────────────────────────────────────────────────────────────


@dataclass
class Intent:
    category: IntentCategory
    confidence: float = 0.0
    raw_text: str = ""
    parsed_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentResult:
    handled: bool = False
    intent: Intent | None = None
    confidence: float = 0.0
    stage: str = ""


# ── Mission ─────────────────────────────────────────────────────────────


@dataclass
class MissionCheckpoint:
    version: int = 1
    mission_id: str = ""
    goal: str = ""
    plan: Plan | None = None
    conversation: Any = None
    current_step_index: int = 0
    completed_step_ids: list[str] = field(default_factory=list)
    status: MissionStatus = MissionStatus.CREATED
    created_at: float = field(default_factory=time.time)
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class Mission:
    id: str
    goal: str
    plan: Plan
    conversation: Any = None
    created_at: float = field(default_factory=time.time)
    status: MissionStatus = MissionStatus.CREATED
    current_step_index: int = 0
    checkpoint_path: Path | None = None
    total_steps: int = 0
    deadline: float | None = None
    failure_policy: str = "abort"


@dataclass
class MissionSummary:
    id: str
    goal: str
    status: MissionStatus
    progress: float = 0.0
    step_count: int = 0
    created_at: float = 0.0
    error: str | None = None


@dataclass
class MissionEvent:
    mission_id: str
    type: str = ""
    step_id: str | None = None
    content: str = ""
    result: Any = None
    error: str | None = None


@dataclass
class SubAgentTask:
    goal: str
    instructions: str
    allowed_tools: list[str] = field(default_factory=list)
    timeout_s: int = 120
    sub_agent_id: str = ""
    max_cost: float | None = None
    max_tool_calls: int | None = None


@dataclass
class SubAgentResult:
    success: bool = False
    summary: str = ""
    artifacts: list[dict] | None = None
    error: str | None = None


# ── Provider Router ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class RoutingConstraints:
    max_cost_per_request: float | None = None
    preferred_provider: str | None = None
    requires_streaming: bool = False
    requires_vision: bool = False
    max_context_window: int | None = None


@dataclass
class ProviderSelection:
    provider_name: str
    model_name: str
    provider: Any = None
    capabilities: frozenset[Capability] = field(default_factory=frozenset)
    estimated_cost_per_request: float = 0.0
    estimated_tokens: int = 0


@dataclass
class TaskDescriptor:
    input_tokens: int = 0
    requires_tools: bool = False
    capabilities: set[Capability] = field(default_factory=set)
    preferred_provider: str | None = None


# ── Context Manager ─────────────────────────────────────────────────────


@dataclass
class ContextStatus:
    total_tokens: int = 0
    usage_pct: float = 0.0
    compacted: bool = False
    warning: str | None = None
    budget_limit: int = 0
    budget_reserved: int = 0
    compaction_count: int = 0


# ── Workspace Knowledge ─────────────────────────────────────────────────


@dataclass
class SymbolLocation:
    symbol: str
    kind: str = ""
    file_path: str = ""
    line: int = 0
    column: int = 0


@dataclass
class SearchResult:
    file_path: str
    line: int = 0
    column: int = 0
    content: str = ""


@dataclass
class FileEntry:
    name: str
    path: str
    kind: str = ""
    size: int | None = None


@dataclass
class FrameworkInfo:
    name: str
    version: str | None = None
    detected_from: str = ""
    category: str = ""


@dataclass
class DependencyGraph:
    root: Path
    dependencies: list[Any] = field(default_factory=list)
    dev_dependencies: list[Any] = field(default_factory=list)
    manager: str = ""


@dataclass
class Dependency:
    name: str
    version_spec: str | None = None
    is_optional: bool = False


@dataclass
class PackageManager:
    name: str
    config_paths: list[Path] = field(default_factory=list)
    lock_file: Path | None = None


@dataclass
class TestConfig:
    framework: str = ""
    config_path: Path | None = None
    test_pattern: str = "test_*.py"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntryPoint:
    path: Path
    name: str
    kind: str = ""


@dataclass
class GitContext:
    branch: str = ""
    repo_root: Path | None = None
    is_dirty: bool = False
    staged_files: list[str] = field(default_factory=list)
    unstaged_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""


@dataclass
class CommitInfo:
    hash: str = ""
    author: str = ""
    date: datetime | None = None
    message: str = ""
    files_changed: list[str] = field(default_factory=list)


# ── Tool Execution ──────────────────────────────────────────────────────


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallDef:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


# ── Permission ──────────────────────────────────────────────────────────


class PermissionDecision(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PermissionAuditRecord:
    tool_name: str
    args: dict[str, Any]
    decision: PermissionDecision
    risk_level: RiskLevel
    policy_name: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    user_confirmed: bool | None = None


# ── Capability Registry ──────────────────────────────────────────────


@dataclass(frozen=True)
class ModelCapabilities:
    model_name: str
    context_window: int = 0
    max_output_tokens: int = 0
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_tools: bool = False
    supports_structured_output: bool = False
    pricing_per_1k_input: float = 0.0
    pricing_per_1k_output: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        known: dict[str, Any] = {
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "streaming": self.supports_streaming,
            "vision": self.supports_vision,
            "tools": self.supports_tools,
            "structured_output": self.supports_structured_output,
            "pricing_per_1k_input": self.pricing_per_1k_input,
            "pricing_per_1k_output": self.pricing_per_1k_output,
        }
        return known.get(name, self.extras.get(name, default))


# ── Provider Health ──────────────────────────────────────────────────


@dataclass
class HealthRecord:
    provider_name: str
    model_name: str
    success_count: int = 0
    failure_count: int = 0
    total_calls: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    timeout_count: int = 0
    rate_limit_count: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    latency_trend: float = 0.0
    degraded_since: float = 0.0
    recovery_time_ms: float = 0.0
    last_latencies: list[float] = field(default_factory=list)

    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failure_count / self.total_calls

    @property
    def healthy(self) -> bool:
        if self.consecutive_failures >= 3:
            return False
        if self.total_calls >= 10 and self.failure_rate >= 0.1:
            return False
        return True

    @property
    def degraded(self) -> bool:
        return self.degraded_since > 0

    @property
    def availability(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return 1.0 - (self.failure_count + self.timeout_count) / self.total_calls

    @property
    def timeout_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.timeout_count / self.total_calls


# ── Provider Metrics ─────────────────────────────────────────────────


@dataclass
class ProviderStats:
    provider_name: str
    model_name: str
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_request_time: float = 0.0
    token_usage_history: list[tuple[float, int, int]] = field(default_factory=list)
