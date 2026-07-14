# AIOS Desktop — Анализ архитектуры Antigravity SDK + паттерны CrabCode

> **Источник Runtime**: https://github.com/google-antigravity/antigravity-sdk-python  
> **Статус**: Репозиторий склонирован и проанализирован  
> **Принцип**: AIOS — Runtime First, Mission First, Provider Agnostic.  
> CrabCode — только источник UI/UX решений для Desktop.

---

## 1. Архитектура Desktop

### Что даёт Antigravity (Runtime)

Antigravity SDK имеет трёхуровневую архитектуру, которая **идеально ложится** на AIOS Runtime:

```
Agent (L1 — Simplified API)
  └── Conversation (L2 — Stateful Session)
        └── Connection (L3 — Transport)
              └── Harness (Go backend via WebSocket + Protobuf)
```

**Что берём:**
- `Agent` → `aios/cli/` entry point (CLI)
- `Conversation` → `aios/runtime/session.py` — управление историей, compaction, turn tracking
- `Connection` → `aios/runtime/transport.py` — абстракция транспорта (WebSocket, HTTP, local)
- `ConnectionStrategy` → `aios/runtime/strategies/` — фабрика стратегий подключения

### Предлагаемая схема AIOS Desktop

```
Electron Main Process
  └── Runtime Bridge (IPC)
        └── AIOS Runtime (Python — наследует Agent + Conversation + Connection)
              ├── Planner
              ├── Executor
              ├── Mission
              └── Workspace
                    └── Renderer (React)
                          ├── Editor (Monaco)
                          ├── Terminal (xterm.js + node-pty)
                          ├── Explorer
                          ├── Mission Center
                          ├── Runtime Inspector
                          └── Panels (Documentation, Timeline, Activity)
```

### Ключевое отличие от CrabCode
- Агент НЕ живёт в Desktop. Агент = AIOS Runtime.
- Runtime Bridge = прослойка (IPC), которая делает Desktop просто клиентом.

---

## 2. Hook System (из Antigravity — ключевое для Runtime)

Antigravity предоставляет **зрелую систему хуков**, которую нужно перенести в AIOS Runtime целиком.

```python
# Иерархия хуков (hooks.py):
HookContext → SessionContext → TurnContext → OperationContext

# Типы хуков:
InspectHook[T]    — read-only, non-blocking (observability)
DecideHook[T]     — read-only, blocking (policy decisions)
TransformHook[T,R] — modifying, blocking (data transformation)

# Конкретные точки расширения:
OnSessionStartHook     # Старт сессии
OnSessionEndHook       # Завершение сессии
PreTurnHook            # Перед отправкой промпта
PostTurnHook           # После получения ответа
PreToolCallDecideHook  # Допуск к выполнению тула
PostToolCallHook       # После выполнения тула
OnToolErrorHook        # Ошибка тула (кастомизация сообщения)
OnInteractionHook      # Запрос пользователю (AskQuestion)
OnCompactionHook       # Компакция контекста
```

**Что берём:**
- Всю иерархию контекстов (Session → Turn → Operation)
- Все точки расширения (8 типов хуков)
- Механизм декораторов (`@pre_turn`, `@post_tool_call`, etc.)
- **Новое для AIOS**: добавить `OnMissionUpdateHook`, `OnPlannerStepHook`

---

## 3. Policy System (из Antigravity — безопасность)

```python
# policy.py — декларативная система разрешений
Policy(tool="*", decision=APPROVE | DENY | ASK_USER, when=predicate, ask_user=handler)

# Примеры политик:
policy.allow_all()
policy.deny_all()
policy.allow("view_file")
policy.deny("run_command", when=lambda args: "rm" in args.get("CommandLine", ""))
policy.ask_user("run_command", handler=my_approval_fn)
policy.workspace_only(["/home/project"])  # ограничение файловых тулов
policy.safe_defaults(handler)
policy.confirm_run_command(handler)
```

**Что берём:**
- Приоритетную модель (Specific Deny > Specific Ask > Specific Allow > Wildcard Deny > ...)
- Предикаты на аргументы тула (условные политики)
- MCP-политики (`server/*` и `server/tool`)
- Fail-Closed при ошибках
- **Новое для AIOS**: Permission Dashboard (Trusted / Strict / YOLO)

---

## 4. Tool System (из Antigravity)

```python
# tool_runner.py
ToolRunner:
  - register(tool, name?)
  - unregister(name)
  - execute(tool_name, **kwargs)
  - process_tool_calls([ToolCall]) -> [ToolResult]
  - get_public_callable(name)  # скрывает injectable параметры

ToolWithSchema(fn, input_schema)  # явная JSON Schema

# Автоматическая инъекция ToolContext:
def my_tool(query: str, ctx: ToolContext) -> str:
    ctx.conversation.send(...)  # доступ к conversation из тула
```

**Что берём:**
- `ToolRunner` как in-process executor
- `ToolWithSchema` для тулов с явной схемой
- Автоинъекцию `ToolContext` через сигнатуру функции
- `process_tool_calls` — batch-выполнение через `asyncio.gather`
- Sync/async тулы (`asyncio.to_thread` для синхронных)
- **Новое для AIOS**: Agent Activity Panel (читает, ищет, планирует, редактирует, тестирует)

---

## 5. Step Model (из Antigravity — основа Timeline)

```python
class Step(pydantic.BaseModel):
    id: str
    step_index: int
    type: StepType           # TEXT_RESPONSE | TOOL_CALL | SYSTEM_MESSAGE | COMPACTION | FINISH | THINKING
    source: StepSource       # SYSTEM | USER | MODEL
    target: StepTarget       # USER | ENVIRONMENT
    status: StepStatus       # ACTIVE | DONE | WAITING_FOR_USER | ERROR | CANCELED
    content: str
    content_delta: str       # реального времени
    thinking: str
    thinking_delta: str      # потоковое thinking
    tool_calls: list[ToolCall]
    error: str
    is_complete_response: bool
    structured_output: Any
    usage_metadata: UsageMetadata  # токены на шаг
```

**Что берём:**
- Полностью модель `Step` — основа Timeline, Mission Dashboard, Runtime Inspector
- `content_delta` и `thinking_delta` для стриминга в реальном времени
- `usage_metadata` на каждый шаг (токены = стоимость)
- **Новое для AIOS**: Timeline UI (Planner → Executor → Tool → Reflection → Commit)

---

## 6. MCP Integration (из Antigravity)

```python
# types.py
McpStdioServer(command="node", args=["server.js"], env={}, enabled_tools=[...])
McpStreamableHttpServer(url="http://...", headers={}, timeout=30.0)

# local_connection.py — преобразует MCP серверы в protobuf и передаёт Go harness
```

**Что берём:**
- Конфигурацию MCP-серверов (stdio + Streamable HTTP)
- Фильтрацию тулов (`enabled_tools` / `disabled_tools`)
- Политики безопасности для MCP (`policy.allow(mcp_server, mcp_tools=["tool1"])`)
- **Принцип**: Desktop никогда не работает с MCP напрямую. Desktop → Runtime → Tool Registry → MCP

---

## 7. Provider System (из Antigravity)

```python
# models.py
class ModelTarget:
    name: str
    endpoint: ModelEndpoint  # GeminiAPIEndpoint | VertexEndpoint
    types: list[ModelType]

class GeminiAPIEndpoint:
    base_url: str
    api_key: str
    http_headers: dict
    options: GeminiModelOptions  # thinking_level

class CapabilitiesConfig:
    enable_subagents: bool
    enabled_tools: list[BuiltinTools]  # allowlist
    disabled_tools: list[BuiltinTools]  # denylist
    compaction_threshold: int
```

**Что берём:**
- `ModelTarget` + `ModelEndpoint` для provider-agnostic конфигурации
- `CapabilitiesConfig` — разделение enabled_tools / disabled_tools
- `enable_subagents` для делегирования
- **Новое для AIOS**: Provider Dashboard (стоимость, задержка, контекст, Vision, Tool Calling, доступность)

---

## 8. Trigger System (из Antigravity)

```python
# triggers.py
class Trigger:
    ...

every(seconds=300)           # периодический триггер
on_file_change("**/*.py")    # файловый вотчер

# trigger_runner.py — запускает триггеры в фоне
TriggerRunner(triggers=[...], connection=...)
```

**Что берём:**
- Механизм фоновых триггеров (cron, file watcher)
- Интеграцию с EventBus (триггер → `send_trigger_notification`)
- **Новое для AIOS**: Mission-триггеры (авторестарт миссии, auto-plan)

---

## 9. EventBus / Streaming (из Antigravity)

```python
# ChatResponse — потоковый ответ:
class ChatResponse:
    async def __aiter__(self) -> AsyncIterator[str]:     # текст
    @property
    def thoughts(self) -> AsyncIterator[str]:             # thinking
    @property
    def tool_calls(self) -> AsyncIterator[ToolCall]:      # тулы
    @property
    def chunks(self) -> AsyncIterator[StreamChunk | ToolCall | ToolResult]:
    async def resolve(self) -> list:                       # полный буфер

# StreamChunk — семантические чанки:
class Thought(StreamChunk):  # thinking delta
class Text(StreamChunk):     # text delta
```

**Что берём:**
- Концепцию `ChatResponse` как общего стрима (текст + мысли + тулы)
- Буферизацию с множественными курсорами (несколько потребителей одного стрима)
- **Новое для AIOS**: EventBus Monitor (ProviderSelected → ToolStarted → PermissionGranted → ToolFinished → MissionUpdated)

---

## 10. Conversation Management (из Antigravity)

```python
class Conversation:
    # Свойства:
    history: list[Step]          # вся история
    turn_count: int              # количество раундов
    compaction_indices: list[int] # где был compaction
    is_idle: bool
    conversation_id: str
    total_usage: UsageMetadata   # токены всей сессии

    # Методы:
    chat(prompt) -> ChatResponse  # send + receive_chunks
    send(prompt)
    receive_steps() -> AsyncIterator[Step]
    receive_chunks() -> AsyncIterator[StreamChunk | ToolCall]
    cancel()
    clear_history()
    wait_for_idle()
    wait_for_wakeup(timeout)
    disconnect()
```

**Что берём:**
- Полностью модель `Conversation`
- `turn_start_indices` + `compaction_indices` для навигации по истории
- `clear_history()` для long-running сессий
- **Новое для AIOS**: Session Checkpoints, Mission History, Workspace Cache

---

## 11. AIOS Runtime Bridge (новое, на основе Antigravity Connection)

```python
# Аналог Connection из antigravity:
class RuntimeConnection(abc.ABC):
    async def send(prompt, **kwargs)
    def receive_steps() -> AsyncIterator[Step]
    async def disconnect()
    async def cancel()
    async def wait_for_idle()
    async def send_trigger_notification(content)
    
    @property
    def is_idle -> bool
    @property
    def conversation_id -> str
```

**Desktop ↔ Runtime Bridge:**
```
Electron (IPC Main)
  │
  ├── runtime.connect(config)     → запускает Python процесс Runtime
  ├── runtime.send(prompt)         → отправляет промпт
  ├── runtime.on('step', cb)       → стримит шаги в Renderer
  ├── runtime.on('thought', cb)    → стримит thinking
  ├── runtime.on('tool_call', cb)  → стримит тулы
  ├── runtime.cancel()             → отменяет текущий turn
  ├── runtime.disconnect()         → завершает сессию
  │
  └── runtime.query('mission.status') → статус миссии
```

---

## 12. Структура проекта AIOS (рекомендуемая)

```
aios/
├── apps/
│   ├── desktop/
│   │   ├── main/           # Electron Main Process
│   │   │   ├── ipc/        # Runtime Bridge
│   │   │   ├── windows/    # BrowserWindow management
│   │   │   └── menu/       # Native menus
│   │   ├── renderer/       # React app
│   │   │   ├── components/ # UI components
│   │   │   ├── panels/     # Mission, Timeline, Inspector, etc.
│   │   │   ├── editor/     # Monaco wrapper
│   │   │   ├── terminal/   # xterm.js + node-pty
│   │   │   └── theme/      # Theme system
│   │   └── preload/        # Electron preload scripts
│   ├── cli/                # Существующий CLI (Typer)
│   └── server/             # API-сервер для remote-клиентов
│
├── runtime/                 # AIOS Runtime (ядро из Antigravity)
│   ├── session.py          # Conversation + History
│   ├── transport.py        # Connection abstraction
│   ├── strategies/         # ConnectionStrategy implementations
│   ├── planner/            # Планировщик
│   ├── executor/           # Исполнитель
│   ├── mission/            # Mission Manager
│   ├── workspace/          # Workspace Knowledge
│   ├── tools/              # Tool Registry
│   ├── hooks/              # Hook system (из Antigravity)
│   ├── policies/           # Policy system (из Antigravity)
│   ├── providers/          # Provider agnostic interface
│   ├── mcp/                # MCP integration
│   ├── memory/             # SQLite + embeddings
│   ├── events/             # EventBus
│   ├── config/             # TOML config
│   └── types/              # Pydantic models
│
├── computer/               # Computer Use (Mouse, Keyboard, OCR, etc.)
│
└── shared/                 # Shared types и утилиты
    ├── types/              # Pydantic модели (Step, Mission, Plan, etc.)
    └── utils/              # Общие утилиты
```

---

## 13. UI Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│  Explorer  │  Editor (Monaco)            │  Mission Center  │
│  ┌───────┐ │  ┌────────────────────────┐ │  ┌────────────┐ │
│  │ src/  │ │  │  // code               │ │  │ Current    │ │
│  │ ├─ app│ │  │  import { foo }        │ │  │ Goal       │ │
│  │ ├─ comp│ │  │                       │ │  │ Step       │ │
│  │ └─ ... │ │  └────────────────────────┘ │  │ Planner    │ │
│  │        │ │  ┌────────────────────────┐ │  │ Reflection│ │
│  │ Git    │ │  │  Terminal (xterm.js)   │ │  │ Timeline  │ │
│  │ status │ │  │  PS C:\project>        │ │  └────────────┘ │
│  │ A   fi │ │  │  npm run dev           │ │                 │
│  │ M   ba │ │  └────────────────────────┘ │  Agent Activity │
│  └───────┘ │                              │  ┌────────────┐ │
│            │                              │  │ Read: 3 fi │ │
│            │                              │  │ Plan: done │ │
│            │                              │  │ Edit: 2 fi │ │
│            │                              │  └────────────┘ │
├────────────┼──────────────────────────────┼─────────────────┤
│ Status Bar │ Runtime Inspector │ Problems │ Git │ Models    │
└────────────┴──────────────────────────────┴─────────────────┘
```

### Вкладки (всегда доступны):
| Панель | Назначение |
|--------|-----------|
| **Explorer** | Файловое дерево + Git status + иконки технолгий |
| **Editor** | Monaco с интеграцией Runtime (AI Suggestions, Mission Step) |
| **Mission Center** | Current Goal, Step, Planner Notes, Reflection, Timeline |
| **Terminal** | xterm.js + node-pty + интеграция с Runtime (история команд) |
| **Agent Activity** | Read, Search, Plan, Edit, Test, Reflect, Done |
| **Timeline** | Planner → Executor → Tool → Reflection → Commit |
| **Runtime Inspector** | Статус всех компонентов Runtime |
| **EventBus Monitor** | Все события в реальном времени |
| **Workspace Dashboard** | Framework, Test count, Coverage, Docker, CI |
| **Provider Dashboard** | Модели, стоимость, задержка, контекст, статус |
| **Mission Dashboard** | Прогресс, ETA, Budget, Tokens, Workers |
| **Computer Runtime** | Mouse, Keyboard, OCR, Processes, Clipboard |
| **Documentation Panel** | GitHub, RFC, StackOverflow, DeepWiki (встроенный браузер) |
| **Settings** | API Keys, Providers, Routing, Mission, Workspace, Permissions, Memory |

---

## 14. Theme System

```css
/* Токены из Antigravity (можно расширить): */
:root {
  --c-void: #08080a;
  --c-slab: #0f0f13;
  --c-surface: #16161c;
  --c-ember: #e05a30;
  /* ... */
}
```

**Темы AIOS:**
- **Dark** (существующая, основа)
- **Light** (инвертированная)
- **Cyberpunk** (#00ff41 неон, #ff00ff акценты)
- **Minimal** (минимум цвета, только шрифты)
- **Fox** (оранжево-рыжая, #ff7f3f)

---

## 15. Локальное хранение

**Из CrabCode (взять):**
- API Keys
- Providers
- Workspace Settings

**Новое для AIOS:**
- Mission History
- Session Checkpoints
- Workspace Cache
- Routing Cache
- Memory (векторная БД)

---

## 16. Что НЕ брать из CrabCode

| ❌ Не брать | ✅ Взамен |
|------------|-----------|
| Agent как часть Desktop | Agent живёт в AIOS Runtime |
| Жёсткая связь UI и логики | UI → Runtime Bridge → Runtime |
| Провайдеры внутри Electron | Провайдеры только в Runtime |
| Монолитный чат | Mission Center |
| Desktop-зависимые компоненты в Runtime | Runtime изолирован |
| Собственный терминал | node-pty (как в CrabCode) |

---

## Итог: лучшие решения из Antigravity для AIOS

| Компонент | Берём из Antigravity |
|-----------|---------------------|
| Архитектура | Agent → Conversation → Connection (3 уровня) |
| Session | Conversation с history, compaction, turn tracking |
| Хуки | 8 типов: Session, Turn, Tool, Interaction, Compaction |
| Политики | Декларативные: allow/deny/ask_user с предикатами |
| Тулы | ToolRunner, ToolWithSchema, ToolContext injection |
| Степы | Step модель — основа Timeline и Inspector |
| MCP | Stdio + HTTP, фильтрация, политики |
| Провайдеры | ModelTarget, CapabilitiesConfig, Provider Agnostic |
| Триггеры | Фоновые задачи (every, on_file_change) |
| Стриминг | ChatResponse — текст + мысли + тулы одновременно |
| Типы | Pydantic V2 на всех границах |
| Безопасность | Workspace-only, Fail-Closed, priority policies |
