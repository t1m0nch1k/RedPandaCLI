# Architecture Stabilization Report

## Summary

- **Date:** 2026-07-10
- **Phase:** Stabilization (Priority 0 + Priority 1)
- **Next:** Runtime v2.1 intelligence features (Planner, MissionEngine, WorkspaceKnowledge)

## Priority 0 — Fix R1 Dependency Violations

| Violation | File | Fix |
|-----------|------|-----|
| `executor/engine.py` imported `AgentState` from `cli.branding` (R1: executor must not import from CLI) | `executor/engine.py` | Replaced with `runtime.models.ExecutionState` |
| `executor/coding_agent.py` imported `AgentState` from `cli.branding` (same R1 violation) | `executor/coding_agent.py` | Replaced with `runtime.models.ExecutionState` |
| `cli/main.py` used `AgentState.TOOL` from the old chain | `cli/main.py` | Updated to `ExecutionState.TOOL` via `runtime.models` |

### Solution Pattern
- `ExecutionState` (5-state: IDLE, THINKING, TOOL, ERROR, DONE) lives in `runtime/models.py`
- `cli/branding.py` re-exports it as `AgentState` for CLI/TUI backward compat
- New code imports `ExecutionState` from `runtime.models`; old TUI code imports `AgentState` from `cli.branding`

## Priority 1 — Infrastructure Stubs

| Schema | File | Fields Added |
|--------|------|-------------|
| `PlanningContext` | `runtime/models.py` | `available_tokens`, `reserved_output_tokens` |
| `ValidationResult` | `runtime/models.py` | `parse_error`, `raw_llm_output` |
| `ValidationRetryConfig` | `runtime/models.py` | `max_retries`, `retry_prompt_template` |
| `MissionCheckpoint` | `runtime/models.py` | Full checkpoint dataclass (version, goal, plan, conversation, step index, artifacts) |
| `Mission` | `runtime/models.py` | `deadline`, `failure_policy` |
| `SubAgentTask` | `runtime/models.py` | `max_cost`, `max_tool_calls` |
| `ContextStatus` | `runtime/models.py` | `budget_limit`, `budget_reserved`, `compaction_count` |
| `CompactionStrategy` | `context_manager/base.py` | Full protocol + `ContextManagerProtocol` ref docs |
| `ValidationRetryConfig` | `planner/base.py` | Import |

## Test Coverage

- **Total tests:** 337
- **Passing:** 337 (100%)
- **New tests:** 12 (ExecutionState, MissionCheckpoint, deadline support, SubAgentTask limits, ContextStatus budget, PlanningContext tokens, ValidationResult extended, ValidationRetryConfig, CompactionStrategy protocol)
- **Regression:** None

## Remaining Debt (deferred to intelligence phases)

1. No `PlannerProtocol` implementation (only the protocol stub exists)
2. No `MissionEngineProtocol` implementation (only the protocol stub exists)
3. No `WorkspaceKnowledgeProtocol` implementation (only the protocol stub exists)
4. No `CompactionStrategy` implementations (only protocol defined)
5. No real `ContextManagerProtocol` implementation (only the existing `ConcreteContextManager`)
6. `StateMachine` and `EventBus` are real implementations; other protocols are stubs

## Readiness for Runtime v2.1 Intelligence Features

- **Architecture:** Frozen (23 ADRs locked, no further review changes without new ADRs)
- **R1 violations:** 0 (fixed)
- **Infrastructure schemas:** Ready (all plan fields, checkpoint schema, budget limits, retry configs in place)
- **Test framework:** Ready (337 tests, all passing)
- **Lint/format:** Not yet verified (no lint/format command found — ask user)
