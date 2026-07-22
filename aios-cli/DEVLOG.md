# AIOS CLI — Development Log
# Лог разработки ядра Runtime и интеграции с TUI

---

## 2026-07-20

### Фаза 4: Memory / Prompting
- ✅ Реализован `MemoryOrchestrator` (`src/aios/memory/orchestrator.py`)
- ✅ Реализован `DefaultPromptAssembler` (`src/aios/runtime/prompt_assembler/default.py`)
- ✅ Рефакторинг `ExecutionEngine` для использования `PromptAssembler`

### Фаза 7: IntentEngine
- ✅ Реализован `IntentEngine` (`src/aios/runtime/intent_engine/engine.py`)
- ✅ Эвристическая + LLM-классификация (CHAT, CODE_TASK, MISSION, COMMAND)
- ✅ Интеграция в `Runtime`

### Фаза 8: WorkspaceKnowledge
- ✅ Реализован `WorkspaceKnowledgeEngine` (`src/aios/runtime/workspace_knowledge/engine.py`)
- ✅ AST-индексация символов Python
- ✅ `WorkspaceSearchTool` для поиска по кодовой базе

### Фаза 9: MissionEngine
- ✅ Реализован `MissionEngine` (`src/aios/runtime/mission_engine/engine.py`)
- ✅ Чекпоинтинг миссий в `~/.aios/missions/`
- ✅ Pause/Resume/Cancel
- ✅ Spawn Sub-Agent с изолированным `ExecutionEngine`

### Интеграция TUI
- ✅ Удалены текстовые команды `aios chat` и `aios code` из `main.py`
- ✅ Удалены `_build_prompt_session()`, `_run_agent_loop()`, `StateHandler`
- ✅ TUI (`app.py`) переведён на `Runtime` вместо `Agent`/`CodingAgent`
- ✅ Удалён ручной переключатель режимов (Ctrl+M), mode = auto
- ✅ `IntentEngine` автоматически маршрутизирует запросы

### Аудит и багфиксы
- 🐛 `default.py`: `Plan`, `Step` не существуют в `core.models` → убран импорт
- 🐛 `models.py`: У `Intent` не было поля `reasoning` → добавлено
- 🐛 `intent_engine/engine.py`: Строки `"code"` вместо enum `IntentCategory.CODE_TASK` → исправлено
- 🐛 `intent_engine/engine.py`: Категория `"system"` не существует → заменена на `IntentCategory.COMMAND`
- 🐛 `intent_engine/engine.py`: `max_tokens` не поддерживается `provider.complete()` → убрано
- 🐛 `intent_engine/engine.py`: `response.get("content")` на строке (не dict) → `response.strip()`
- 🐛 `mission_engine/engine.py`: `mission.plan.steps` без null-check → добавлена проверка
- 🐛 `default.py`: `model_dump_json()` на `@dataclass` → `json.dumps(asdict(...))`
- 🐛 `app.py`: Двойной `run_worker(exclusive=True)` вызывал повторные запуски → `await` напрямую
- 🐛 `engine.py`: `assembled_messages` собирался 1 раз до цикла → перенесён внутрь цикла
- 🐛 `app.py`: Убрано системное сообщение "Intent: code_task" для пользователя

---

## Архитектура (текущая)

```
aios (команда) → TUI (app.py) → Runtime
                                    ├── IntentEngine      (маршрутизация)
                                    ├── ExecutionEngine    (выполнение)
                                    ├── MissionEngine      (автономные задачи)
                                    ├── PromptAssembler    (сборка промптов)
                                    ├── MemoryOrchestrator (память)
                                    ├── WorkspaceKnowledge (знание кодовой базы)
                                    ├── Planner            (планирование)
                                    ├── PermissionGate     (разрешения)
                                    └── ProviderRouter     (роутинг провайдеров)
```

## Следующие шаги
- [ ] Модули VISION и HANDS для десктопа
- [ ] Тестирование полного пайплайна: запрос → intent → tools → ответ
- [ ] Улучшение MissionEngine: прогресс-бар в TUI
