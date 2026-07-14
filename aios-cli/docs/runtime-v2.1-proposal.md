# Runtime v2.1 — Intelligence Layer & Computer Runtime

## Executive Summary

Runtime infrastructure (Phase 0–2) is complete: EventBus, StateMachine, ProviderRouter,
PermissionGate, CapabilityRegistry, ProviderHealth, ProviderMetrics. The next priority is
the **intelligence layer** — the components that make AIOS understand, plan, execute,
reflect, and adapt.

This proposal covers two tracks:

1. **Runtime v2.1** — Five intelligence modules (IntentEngine, Planner, Reflection,
   MissionEngine, WorkspaceKnowledge). Implements the core agent loop with planning,
   execution, evaluation, and replanning.

2. **Computer Runtime** — A new platform-independent subsystem for OS-level operations
   (windows, mouse, keyboard, clipboard, screen, OCR, accessibility, processes,
   notifications, audio). Independent from Runtime, usable by CLI, Desktop, Voice,
   and future Computer Agent.

---

## Track 1: Runtime v2.1 — Intelligence Layer

### Goal

Make AIOS capable of the full cognitive cycle:

```
Input → Classify → Plan → Execute → Observe → Reflect → (Replan | Complete)
```

No existing code is modified. Each module is implemented behind its protocol and wired
into the Runtime facade.

---

### 1.1 IntentEngine — Full Pipeline Implementation

**Current state:** Protocol stub with `classify()`, `register_stage()`, `remove_stage()`,
`list_stages()`. No implementation.

**Proposed implementation:** `src/aios/runtime/intent_engine/engine.py`

#### Stages

| Priority | Stage | Responsibility | Never touches LLM? |
|----------|-------|---------------|-------------------|
| 10 | `RuleEngine` | Pattern matching (regex, prefix, keywords) | ✅ Yes |
| 20 | `LocalClassifier` | Shell commands, file ops, git ops heuristics | ✅ Yes |
| 30 | `PlannerStage` | Detect multi-step requests → delegate to Planner | ⚠️ Only if needed |
| 40 | `LLMStage` | Ambiguous/free-form → classify with LLM | ❌ Yes (last resort) |

#### RuleEngine Design

Patterns are registered declaratively:

```python
@dataclass(frozen=True)
class IntentPattern:
    name: str
    category: IntentCategory
    patterns: list[str]         # regex patterns, matched via re.search
    extract: dict[str, str] | None = None  # named groups → parsed_args

BUILTIN_PATTERNS = [
    IntentPattern("status", IntentCategory.COMMAND, [
        r"^(git\s+)?status$", r"^(what'?s the )?status$",
    ]),
    IntentPattern("open_vscode", IntentCategory.COMMAND, [
        r"^open\s+(vs\s?code|vscode)$", r"^launch\s+(vs\?code|vscode)$",
    ]),
    IntentPattern("read_file", IntentCategory.FILE_OPERATION, [
        r"^(read|show|cat)\s+(file\s+)?(?P<path>.+)$",
    ]),
    IntentPattern("search_code", IntentCategory.QUESTION, [
        r"^(find|search|grep)\s+(for\s+)?(?P<query>.+)$",
    ]),
]
```

Custom patterns are pluggable at runtime — no code changes needed.

#### LocalClassifier Design

Heuristic-based classification without an LLM:

```python
class LocalClassifier:
    async def can_handle(self, text: str, conversation=None) -> bool:
        return True  # Always attempts classification first

    async def handle(self, text: str, conversation=None) -> IntentResult:
        # 1. Check shell command keywords
        # 2. Check file operation patterns
        # 3. Check git idioms
        # 4. Check project-specific keywords (via WorkspaceKnowledge)
        # 5. Detect question patterns (what, why, how, does, is, are)
        # 6. Detect mission patterns (long-running goal description)
        # 7. Fallthrough: return unhandled → next stage
```

#### LLMStage Design

Only invoked when all faster stages pass. Uses a lightweight classification prompt:

```python
class LLMStage:
    PROMPT = """Classify the following user request into exactly one category.
Categories: {categories}
Request: {text}
Respond with only the category name and confidence (0.0-1.0) in JSON."""

    async def handle(self, text, conversation) -> IntentResult:
        messages = [{"role": "system", "content": self.PROMPT}]
        response = await self._llm.chat(messages)
        return self._parse_response(response)
```

#### Wiring in Runtime

```python
class Runtime:
    async def chat(self, message: str) -> str:
        intent = await self._intent_engine.classify(message)
        if intent.category in (IntentCategory.COMMAND, IntentCategory.FILE_OPERATION):
            return await self._execute_direct(intent)
        elif intent.category in (IntentCategory.PLAN, IntentCategory.MISSION):
            return await self._plan_and_execute(intent)
        else:
            return await self._executor.run(message)
```

---

### 1.2 Planner — Plan Generation & Validation

**Current state:** Protocol stub with `plan()`, `replan()`, `validate()`. No implementation.

**Proposed implementation:** `src/aios/runtime/planner/planner.py`

#### Design

Planner calls the LLM with a structured prompt that includes:

- The user's goal
- Available tools (from ToolExecutor)
- Workspace context (from WorkspaceKnowledge)
- Conversation history
- Constraints (max steps, preferred approach)

The LLM returns a JSON plan that is parsed into a `Plan` with `Step` objects.

```python
PLAN_PROMPT = """You are a planning agent. Given a user request, produce a
step-by-step plan using the available tools.

AVAILABLE TOOLS:
{tools}

WORKSPACE CONTEXT:
{workspace_context}

USER REQUEST: {request}

Respond with a JSON plan:
{{
  "steps": [
    {{
      "id": "step-1",
      "description": "Human-readable step description",
      "tool_name": "tool_name or null for LLM-only",
      "args": {{}} or null,
      "dependencies": [],
      "expected_outcome": "What success looks like"
    }}
  ],
  "parallel_groups": [["step-1", "step-2"]]
}}"""
```

#### Validation

```python
async def validate(self, plan: Plan) -> ValidationResult:
    errors = []
    # 1. All step IDs unique
    # 2. Tool references exist in available tools
    # 3. No circular dependencies
    # 4. Dependencies reference valid step IDs
    # 5. No ambiguity in expected_outcome
    # 6. Step count within max_steps
    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

#### Replanning

```python
async def replan(self, plan: Plan, feedback: str) -> Plan:
    # Take remaining (unexecuted) steps
    # Feed them + feedback + execution results back to LLM
    # Return revised Plan with adjusted steps
```

#### Integration with WorkspaceKnowledge

Planner queries WorkspaceKnowledge before generating a plan:

```python
class Planner:
    async def plan(self, request, context) -> Plan:
        frameworks = await self._workspace.detect_frameworks()
        deps = await self._workspace.dependency_graph()
        entry_points = await self._workspace.entry_points()
        git = await self._workspace.git_context()

        ws_context = self._build_context(frameworks, deps, entry_points, git)
        return await self._llm_plan(request, context, ws_context)
```

---

### 1.3 Reflection / Replanning — Evaluate & Adapt

**New architectural component.** Not present in original Phase 0 protocols.

**Proposed implementation:** Built into Executor as a reflection loop, with a dedicated
reflection prompt.

#### Reflection Protocol

```python
class ReflectionProtocol(Protocol):
    """
    Evaluates execution results and decides whether to continue,
    replan, or abort.
    """

    async def evaluate(
        self,
        plan: Plan | None,
        step: Step | None,
        result: StepResult | ExecutionResult,
    ) -> ReflectionDecision:
        """
        Evaluate the outcome of a step or full execution.
        Returns a decision with reasoning.
        """

    async def suggest_replan(
        self,
        plan: Plan,
        failed_step: Step,
        error: str,
    ) -> Plan:
        """Generate a revised plan from the failure point."""


@dataclass
class ReflectionDecision:
    action: Literal["continue", "replan", "complete", "abort"]
    reasoning: str
    confidence: float = 0.0
    modified_plan: Plan | None = None
```

#### Reflection Prompt

```python
REFLECTION_PROMPT = """Evaluate the executed step and its result.

GOAL: {goal}
STEP: {step_description}
EXPECTED: {expected_outcome}
ACTUAL: {actual_result}
ERROR: {error}

Does the result match the expected outcome?
- "continue" — proceed to next step
- "replan" — the approach is wrong, need a different plan
- "complete" — goal is achieved early
- "abort" — unrecoverable error

Respond with JSON: {{"action": "...", "reasoning": "..."}}"""
```

#### Executor Integration

The Executor agent loop becomes:

```python
class Executor:
    async def _execute_with_reflection(self, plan: Plan):
        for step in plan.steps:
            result = await self._execute_step(step)
            decision = await self._reflection.evaluate(plan, step, result)

            if decision.action == "replan":
                new_plan = await self._planner.replan(plan, decision.reasoning)
                return await self._execute_with_reflection(new_plan)
            elif decision.action == "abort":
                raise ExecutionError(decision.reasoning)
            elif decision.action == "complete":
                return ExecutionResult(success=True)
```

---

### 1.4 MissionEngine — Autonomous Mission Execution

**Current state:** Protocol stub with full lifecycle methods. No implementation.

**Proposed implementation:** `src/aios/runtime/mission_engine/engine.py`

#### Design

MissionEngine orchestrates the full cycle:

```
create_mission → execute_mission (step loop with checkpoints)
                → pause_mission (EventBus-driven)
                → resume_mission (from checkpoint)
                → cancel_mission (immediate)
                → request_replan (on step failure)
```

#### Implementation Plan

```
src/aios/runtime/mission_engine/
├── engine.py         # MissionEngine implementation
├── checkpoint.py     # Checkpoint persistence (JSON/msgpack)
└── store.py          # In-memory mission store with optional file persistence
```

#### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Checkpoint format | JSON (extendable to msgpack) | Human-readable for debugging |
| Checkpoint timing | After every completed step | Minimizes rework on resume |
| Sub-agent spawning | New Runtime instance with isolated state | ADR-013, already designed |
| Mission store | In-memory dict + optional file persistence | No DB dependency |
| Pause trigger | EventBus `MissionPauseCommand` | CLI-independent (ADR-016) |
| Failure policy | Configurable: abort | retry | replan | User chooses at mission creation |

#### Integration with WorkspaceKnowledge

MissionEngine needs workspace awareness to decompose goals:

```python
async def create_mission(self, goal, conversation):
    context = await self._build_planning_context()
    plan = await self._planner.plan(goal, context)
    mission = Mission(id=uuid(), goal=goal, plan=plan, ...)
    await self._store.save(mission)
    return mission

async def _build_planning_context(self) -> PlanningContext:
    return PlanningContext(
        workspace_root=...,   # From Runtime config
        available_tools=await self._tool_executor.list_tools(),
        mission_mode=True,
        checkpoint_enabled=True,
    )
```

---

### 1.5 WorkspaceKnowledge — Full Implementation

**Current state:** Protocol stub with 15+ methods. No implementation.

**Proposed implementation files:**

```
src/aios/runtime/workspace_knowledge/
├── engine.py         # WorkspaceKnowledge implementation (facade)
├── indexer.py        # Symbol indexer (ctags / tree-sitter)
├── repo_map.py       # Repository map generator
├── detector.py       # Framework & package manager detection
├── git_reader.py     # Git context provider
└── entry_points.py   # Entry point discovery
```

#### Implementation Priority

| Method | Priority | Implementation approach |
|--------|----------|------------------------|
| `list_directory` | P0 | Simple `Path.iterdir()` |
| `search_text` | P0 | `rg` (ripgrep) subprocess, fallback to pure Python |
| `file_context` | P0 | `Path.read_text()` with line slicing |
| `framework_detection` | P1 | Config file heuristics (pyproject.toml, package.json, Cargo.toml) |
| `dependency_graph` | P1 | Parse manifest files |
| `package_managers` | P1 | Detect by config file presence |
| `test_config` | P1 | Check for pytest.ini, vitest.config, jest.config |
| `entry_points` | P1 | main.py, app.py, cli.py, console_scripts |
| `git_context` | P1 | `git` subprocess calls |
| `git_history` | P1 | `git log` subprocess |
| `repo_map` | P2 | File tree + key symbols, token-bounded |
| `query_symbol` | P2 | ctags index or tree-sitter query |
| `build_index` | P2 | Background indexer for symbol database |

#### Runtime Integration

```python
class Runtime:
    async def start(self):
        self._running = True
        await self._event_bus.emit(Events.RuntimeStarted(...))
        asyncio.create_task(self._workspace.build_index())  # background
```

WorkspaceKnowledge feeds into:
- **Planner** — framework/dep/git context enriches plan prompts
- **Executor** — file context and search during tool execution
- **IntentEngine** — project-specific keywords improve classification

---

### 1.6 Implementation Phases — Runtime v2.1

| Phase | Modules | Duration | Depends on |
|-------|---------|----------|------------|
| v2.1-A | WorkspaceKnowledge (P0 methods) | 3 days | Phase 2 |
| v2.1-B | IntentEngine (RuleEngine + LocalClassifier) | 2 days | Phase 2, v2.1-A |
| v2.1-C | Planner (plan + validate) | 3 days | Phase 2, v2.1-A |
| v2.1-D | Reflection (evaluate + replan) | 2 days | v2.1-C |
| v2.1-E | MissionEngine | 4 days | v2.1-C, v2.1-D |
| v2.1-F | IntentEngine (LLMStage) + Executor wiring | 2 days | v2.1-B, v2.1-C |
| v2.1-G | WorkspaceKnowledge (P1–P2 methods) | 4 days | v2.1-A |

**Total estimated duration:** 20 days

| Phase | Tests added | Cumulative tests |
|-------|-------------|-----------------|
| v2.1-A | 60 | 387 |
| v2.1-B | 40 | 427 |
| v2.1-C | 50 | 477 |
| v2.1-D | 35 | 512 |
| v2.1-E | 60 | 572 |
| v2.1-F | 30 | 602 |
| v2.1-G | 40 | 642 |

---

## Track 2: Computer Runtime

### 2.1 What Is Computer Runtime?

Computer Runtime is a **platform-independent abstraction layer** for operating system
operations. It exposes a unified API for:

- Windows (list, focus, move, resize, minimize, close)
- Mouse (move, click, double-click, right-click, drag, scroll)
- Keyboard (type, hotkey, key-down, key-up)
- Clipboard (get-text, set-text, get-image, set-image)
- Screen capture (region, full-screen, per-window)
- OCR (screen region → text, with bounding boxes)
- Accessibility tree (query UI elements by role, label, state)
- Processes (list, launch, terminate, wait-for-exit, env)
- Notifications (os-native, custom payloads)
- Audio (record, playback, volume, list-devices)

### 2.2 Architectural Principles

| Principle | Rationale |
|-----------|-----------|
| **Platform-independent API** | One API surface for Windows, macOS, Linux |
| **Zero Runtime dependency** | Computer Runtime is a standalone package; Runtime optionally imports it |
| **Pluggable backends** | Each platform has its own backend; backends are selected at init |
| **Protocol-driven** | Like Runtime, all contracts are Protocols |
| **No LLM coupling** | Computer Runtime does not know about LLMs, agents, or missions |
| **Async-first** | All I/O operations are async, non-blocking |
| **Graceful degradation** | Unsupported operations return clean errors, not crashes |

### 2.3 Package Structure

```
src/aios/computer_runtime/
├── __init__.py                   # Public API re-exports
├── base.py                       # Top-level ComputerRuntime protocol
├── models.py                     # Dataclasses: Screen, Window, Point, Rect, etc.
│
├── platform/                     # Backend implementations
│   ├── __init__.py
│   ├── windows_backend.py        # Win32 API via ctypes
│   ├── macos_backend.py          # Quartz / CGEvent via ctypes
│   └── linux_backend.py          # X11 / Wayland via python-xlib
│
├── windows/                      # Window management
│   ├── base.py                   # WindowController protocol
│   └── models.py                 # WindowInfo, WindowState enums
│
├── mouse/                        # Mouse control
│   ├── base.py
│   └── models.py                 # Button, ScrollDirection
│
├── keyboard/                     # Keyboard input
│   ├── base.py
│   └── models.py                 # Key, Modifier, Hotkey
│
├── clipboard/                    # Clipboard access
│   ├── base.py
│   └── models.py                 # ClipboardContent
│
├── screen/                       # Screen capture
│   ├── base.py
│   └── models.py                 # ScreenRegion, CapturedImage
│
├── ocr/                          # OCR
│   ├── base.py
│   ├── models.py                 # OCRResult, TextRegion
│   └── engines/
│       ├── tesseract_engine.py   # Tesseract-based
│       └── windows_microsoft_ocr.py  # Windows.Media.Ocr
│
├── accessibility/                # Accessibility tree
│   ├── base.py
│   └── models.py                 # UIElement, AccessibleRole
│
├── processes/                    # Process management
│   ├── base.py
│   └── models.py                 # ProcessInfo, ProcessEvent
│
├── notification/                 # OS notifications
│   ├── base.py
│   └── models.py                 # Notification, NotificationAction
│
└── audio/                        # Audio I/O
    ├── base.py
    └── models.py                 # AudioDevice, AudioStream
```

### 2.4 Unified ComputerRuntime Facade

```python
# src/aios/computer_runtime/base.py

class ComputerRuntimeProtocol(Protocol):
    @property
    def windows(self) -> WindowController: ...
    @property
    def mouse(self) -> MouseController: ...
    @property
    def keyboard(self) -> KeyboardController: ...
    @property
    def clipboard(self) -> ClipboardController: ...
    @property
    def screen(self) -> ScreenCapture: ...
    @property
    def ocr(self) -> OCREngine: ...
    @property
    def accessibility(self) -> AccessibilityTree: ...
    @property
    def processes(self) -> ProcessManager: ...
    @property
    def notifications(self) -> NotificationService: ...
    @property
    def audio(self) -> AudioService: ...


class ComputerRuntime(ComputerRuntimeProtocol):
    """
    Platform-independent facade for OS-level operations.

    Backends are auto-detected from sys.platform at construction time.
    Consumers never import platform-specific code.
    """

    def __init__(self, platform_override: str | None = None):
        platform = platform_override or sys.platform
        self._backend = self._load_backend(platform)
        self._windows = self._backend.create_windows()
        self._mouse = self._backend.create_mouse()
        self._keyboard = self._backend.create_keyboard()
        self._clipboard = self._backend.create_clipboard()
        self._screen = self._backend.create_screen_capture()
        self._ocr = self._create_ocr(platform)
        self._accessibility = self._backend.create_accessibility()
        self._processes = self._backend.create_process_manager()
        self._notifications = self._backend.create_notification_service()
        self._audio = self._backend.create_audio()

    @property
    def windows(self) -> WindowController:
        return self._windows
    # ... similar for all properties
```

### 2.5 Example: WindowController Protocol

```python
# src/aios/computer_runtime/windows/base.py

class WindowController(Protocol):
    async def list_windows(self) -> list[WindowInfo]: ...
    async def get_active_window(self) -> WindowInfo | None: ...
    async def focus_window(self, window_id: str) -> None: ...
    async def move_window(self, window_id: str, x: int, y: int) -> None: ...
    async def resize_window(self, window_id: str, w: int, h: int) -> None: ...
    async def minimize_window(self, window_id: str) -> None: ...
    async def close_window(self, window_id: str) -> None: ...


@dataclass
class WindowInfo:
    id: str
    title: str
    process_name: str
    bounds: Rect
    is_visible: bool
    is_focused: bool
```

### 2.6 Integration with Runtime (Without Coupling)

Computer Runtime and Runtime are **separate packages** with zero mutual imports.
Integration happens at the application layer, not the architecture layer.

#### Option A: ComputerRuntime as a Runtime Plugin

ComputerRuntime is registered as a tool in ToolExecutor:

```python
# Application layer only — never in Runtime or ComputerRuntime
computer = ComputerRuntime()
tool_executor.register_tool(ComputerRuntimeTool("computer", computer))
```

The Runtime never knows about ComputerRuntime. The ToolExecutor treats
computer operations as regular tool calls — the same as any other tool.

#### Option B: ComputerRuntime as a Protocol Implementation

Runtime modules that need OS access receive a `ComputerRuntimeProtocol` via
constructor injection — exactly like all other Runtime modules receive protocols:

```python
class Executor:
    def __init__(
        self,
        provider_router: ProviderRouterProtocol,
        tool_executor: ToolExecutorProtocol,
        computer_runtime: ComputerRuntimeProtocol | None = None,  # optional
    ):
        self._computer = computer_runtime
```

This is **optional** — Executor works perfectly without ComputerRuntime.
When present, the reflection cycle can use screen capture + OCR to verify
visual output. When absent, reflection relies on tool result text.

#### Option C: EventBus Bridge

Computer Runtime can optionally emit events to an EventBus:

```python
# Application wiring
bus = EventBus()
computer = ComputerRuntime(event_bus=bus)
runtime = Runtime(event_bus=bus, ...)
```

This enables cross-layer observability without direct coupling:
- Screen capture events → Desktop UI for display
- Process events → MissionEngine for dependency tracking
- Clipboard events → Executor for context awareness

#### Recommended: Option A + C

| Option | Use | When |
|--------|-----|------|
| **A** (Tool registration) | ComputerAgent can use computer tools in plan steps | Default |
| **C** (EventBus bridge) | Desktop UI shows screen capture, process list, clipboard | Optional enhancement |

Runtime architecture remains pure — zero ComputerRuntime imports. The bridge
is purely at the EventBus level (ADR-016).

---

### 2.7 Computer Runtime Sub-Agent Use Case

A future Computer Agent mission might look like:

```
Goal: "Fill out the login form on the website"

Plan:
1. Open browser (processes.launch)
2. Focus browser window (windows.focus_window)
3. Capture screen to verify (screen.capture + ocr.extract)
4. Type URL in address bar (keyboard.type)
5. Press Enter (keyboard.hotkey)
6. Wait for page load, capture screen
7. Locate username field via accessibility tree
8. Type credentials (keyboard.type)
9. Click login button (mouse.click)
10. Verify login success via screen capture + OCR
```

Each step is a tool call to ComputerRuntime's unified API. The Planner,
Executor, and Reflection loop handle ComputerRuntime tools exactly like
filesystem or shell tools — zero special-casing.

### 2.8 Graceful Degradation Design

Not all platforms support all operations:

```python
class WindowsBackend:
    async def list_windows(self) -> list[WindowInfo]:
        return self._enum_windows_via_win32()

    @property
    def supports(self) -> set[str]:
        return {"windows", "mouse", "keyboard", "clipboard",
                "screen", "accessibility", "processes",
                "notifications", "audio"}  # OCR via Windows.Media.Ocr


class LinuxBackend:
    @property
    def supports(self) -> set[str]:
        return {"mouse", "keyboard", "clipboard", "screen",
                "processes", "notifications", "audio"}
        # windows, accessibility: partial/unavailable without compositor


# ComputerRuntime exposes capability check:
computer = ComputerRuntime()
if "ocr" in computer.supports:
    text = await computer.ocr.extract(region)
else:
    text = await fallback_ocr(region)  # or raise CapabilityError
```

---

### 2.9 Implementation Roadmap — Computer Runtime

| Phase | Scope | Backend Targets | Duration |
|-------|-------|----------------|----------|
| CR-P0 | Core facade + models | Windows only | 5 days |
| CR-P1 | clipboard, mouse, keyboard | Windows + macOS | 4 days |
| CR-P2 | screen capture, windows, processes | Windows + macOS | 5 days |
| CR-P3 | notifications, audio | Windows + macOS | 3 days |
| CR-P4 | OCR (Tesseract + Windows.Media.Ocr) | Cross-platform | 3 days |
| CR-P5 | accessibility tree | Windows (UI Automation) | 4 days |
| CR-P6 | Linux backend (X11/Wayland) | Linux | 5 days |
| CR-P7 | Integration tests + docs | All | 3 days |

**Total estimated duration:** 32 days (can parallelize with Runtime v2.1)

---

## 3. Architectural Decision Records

### ADR-020: Reflection Is Executor Concern, Not Standalone Module

**Status:** Proposed

**Context:** Reflection evaluates execution results and decides next action. It could
be a standalone module or embedded in the Executor.

**Decision:** Reflection is a **protocol implemented within Executor**, not a standalone
module. The `ReflectionProtocol` exists as a clear interface, but the implementation is
part of the Executor's think → act → observe loop. This avoids circular dependencies
(Executor would need to call Reflector, which might need to call Executor for replanning).

**Consequences:**
- Positive: Executor owns the full agent loop — no cross-module orchestration needed
- Positive: Reflection can be mocked independently via `ReflectionProtocol`
- Negative: Executor is slightly larger (one additional concern in the loop)

### ADR-021: ComputerRuntime Is Never Imported by Runtime

**Status:** Proposed

**Context:** Computer Runtime provides platform-level operations that Runtime modules
might find useful (Executor for screen capture, Planner for process detection). Direct
imports would create coupling.

**Decision:** The `aios.runtime` package must never import from `aios.computer_runtime`.
Integration happens at the application layer via:
1. Tool registration (ComputerRuntime operations → ToolExecutor tools)
2. Optional constructor injection of `ComputerRuntimeProtocol`
3. EventBus bridge for observability

**Consequences:**
- Positive: Runtime remains pure — zero platform-specific code
- Positive: ComputerRuntime can be developed and tested independently
- Positive: Runtime tests never need ComputerRuntime fixtures
- Negative: Application wiring is slightly more verbose

### ADR-022: Planner Stages Feed WorkspaceKnowledge to LLM

**Status:** Proposed

**Context:** The LLM produces better plans when it understands the project context
(frameworks, dependencies, entry points, git state). Without this context, plans are
generic and often wrong.

**Decision:** Planner queries WorkspaceKnowledge before every `plan()` call and injects
the context into the LLM prompt. This is automatic — the caller does not supply
workspace context manually. WorkspaceKnowledge may still be building its index (P2
methods are async and may return partial results).

**Consequences:**
- Positive: Plans are project-aware by default
- Positive: Workspace knowledge improves over time as the index builds
- Negative: First plan() call may be slower if index is still building
- Negative: Planner becomes dependent on WorkspaceKnowledge protocol (acceptable —
  both are Runtime modules with clear interfaces)

### ADR-023: IntentEngine RuleEngine Is a Chain of Responsibility

**Status:** Proposed

**Context:** RuleEngine must support custom patterns without modifying core code.
A simple list of patterns with `re.search` is not extensible enough — some patterns
need context (conversation history, workspace state).

**Decision:** RuleEngine uses the **Chain of Responsibility** pattern. Each rule is
an `IntentStage` implementation. Built-in rules are registered by default. Custom
rules use the same `register_stage()` API as IntentEngine stages. The chain terminates
at the first rule that returns `handled=True`.

**Consequences:**
- Positive: Custom rules are first-class — same API as ML and LLM stages
- Positive: Rules can access workspace context, conversation history, settings
- Positive: No special-casing for "simple pattern" vs "complex rule"
- Negative: Rule registration is slightly more verbose than a pattern list (mitigated
  by `IntentPattern` helper that converts regex → stage)

---

## 4. Future Compatibility — Computer Agent

The combination of Runtime v2.1 (intelligence) + Computer Runtime (platform) enables
a **Computer Agent** that:

1. Receives a high-level goal ("Set up the Django project")
2. IntentEngine classifies it as MISSION
3. Planner generates steps using workspace knowledge
4. Executor executes steps, using ComputerRuntime tools when needed
5. Reflection evaluates each step (including screen capture + OCR for verification)
6. MissionEngine manages checkpoints, pause/resume, and progress reporting
7. All decisions emit structured events for the Desktop UI timeline

The architecture supports this without any single component knowing about
the full pipeline. Each component has a clear, narrow responsibility.
