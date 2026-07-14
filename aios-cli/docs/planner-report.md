# Planner Implementation Report — Phase 3.1

## Architecture Changes

- **New file:** `src/aios/runtime/planner/planner.py` — concrete `Planner` class implementing `PlannerProtocol`
- **Modified:** `src/aios/runtime/planner/__init__.py` — exports `Planner` and `_detect_circular_dependencies`
- **Modified:** `src/aios/runtime/__init__.py` — exports `Planner` from top-level `aios.runtime`
- **No changes to** `planner/base.py` — protocol is unchanged, concrete class extends it

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `src/aios/runtime/planner/planner.py` | 295 | Concrete Planner implementation |
| `tests/test_planner_unit.py` | 555 | 55 unit tests across 8 test classes |
| `tests/test_planner_integration.py` | 370 | 15 integration tests across 6 test classes |

## Files Modified

| File | Change |
|------|--------|
| `src/aios/runtime/planner/__init__.py` | Added `Planner` and `_detect_circular_dependencies` exports |
| `src/aios/runtime/__init__.py` | Added `Planner` import and `__all__` entry |
| `tests/test_runtime_protocols.py` | Added `Planner` import + top-level availability assertion |

## Planner Execution Flow

```
plan(request, context)
│
├─ _get_workspace_context()   ← auto-queries WK (ADR-022)
│
├─ Build PLAN_PROMPT
│  ├─ Available tools (from context)
│  ├─ Workspace context (frameworks, deps, entry points, git)
│  ├─ Conversation history
│  ├─ User preferences
│  └─ User request
│
├─ LLM call → raw JSON
├─ _parse_llm_response()      ← strips markdown fences, parses JSON
├─ _build_plan()              ← Step objects + UUID plan id
├─ validate()                 ← 6 validators
│
├─ [RETRY LOOP] if invalid or unparseable (ValidationRetryConfig)
│
└─ Return Plan


replan(plan, feedback, context)
│
├─ _get_remaining_steps()
├─ Build REPLAN_PROMPT (remaining steps + feedback)
├─ Same LLM → parse → validate → retry loop
└─ Return revised Plan


validate(plan)
│
├─ 1. Check for empty steps
├─ 2. Check for duplicate step IDs
├─ 3. Check dependencies reference valid step IDs
├─ 4. Detect circular dependencies (DFS cycle detection)
├─ 5. Check for missing descriptions
├─ 6. Warn on missing expected outcomes
└─ Return ValidationResult


Additional methods on concrete Planner:
├─ estimate_cost(plan)        ← $0.01/tool step, $0.005/LLM step
├─ estimate_complexity(plan)  ← simple|moderate|complex
├─ serialize(plan) → dict     ← Plan → serializable dict
├─ deserialize(dict) → Plan   ← dict → Plan (roundtrip safe)
```

## Responsibilities Covered

| Responsibility | Implementation |
|---------------|---------------|
| Generate structured execution plans | `plan()` with LLM + PLAN_PROMPT |
| Produce a dependency graph of Steps | `Step.dependencies` tuple + `parallel_groups` |
| Validate generated plans | `validate()` — 6 checks |
| Detect impossible/circular dependencies | `_detect_circular_dependencies()` — DFS |
| Estimate execution cost | `estimate_cost()` — per-step pricing |
| Support partial replanning | `replan()` keeps remaining steps |
| Support plan serialization/deserialization | `serialize()` / `deserialize()` — JSON roundtrip |
| Support validation retries | `ValidationRetryConfig` — retry loop with prompt template |
| Integrate with PlanningContext | Full prompt injection (tools, history, preferences, tokens) |
| Request WorkspaceKnowledge | Auto-queries on every `plan()` + `replan()` (ADR-022) |

## Non-Responsibilities (Enforced)

| Boundary | How |
|----------|-----|
| Never execute tools | Planner only produces Plans — no tool execution code |
| Never call providers directly | LLM accessed via injected `llm_chat` callable |
| Never depend on CLI/TUI | No imports from `aios.cli` — tested without CLI dependency |

## Test Results

- **Total tests:** 407 (337 existing + 70 new)
- **Passing:** 407 (100%)
- **New unit tests:** 55 — covers parsing, cycle detection, plan generation, validation (all 6 checks), replanning, retries, serialization/deserialization, cost estimation, complexity estimation, constructor, edge cases
- **New integration tests:** 15 — full flow, complex dependency chains, parallel groups, replan full flow, WorkspaceKnowledge injection, WK fallback on error, diamond dependency, multiple simultaneous errors, large plans (15/20 steps), zero-tool context, zero-retry config
- **Regression:** 0

## Readiness for MissionEngine

| Prerequisite | Status |
|-------------|--------|
| `PlannerProtocol` implemented | ✅ `Planner` is production-ready |
| `plan()` returns valid `Plan` with `Step` objects | ✅ Full validation, retry, WK integration |
| `replan()` supports mid-execution revision | ✅ Feedback + remaining steps + retry |
| `Plan` serialization for checkpoint persistence | ✅ `serialize()` / `deserialize()` |
| Cost/complexity estimates for mission budgeting | ✅ `estimate_cost()` / `estimate_complexity()` |
| WorkspaceKnowledge integration (ADR-022) | ✅ Auto-queries frameworks, deps, entry points, git |
| Validation retry (ValidationRetryConfig) | ✅ Configurable max_retries + prompt template |
| No dependency on CLI/TUI | ✅ Verified |
| No tool execution in Planner | ✅ Verified |

**MissionEngine can consume Planner as its planning engine on day one of Phase 3.4.**

## Remaining Work Before Reflection (Phase 3.3)

- Reflection protocol + implementation (Executor concern per ADR-020)
- WorkspaceKnowledge P0 methods (list_directory, search_text, file_context)
