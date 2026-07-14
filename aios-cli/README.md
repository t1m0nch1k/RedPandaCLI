# AIOS CLI

Первый клиент экосистемы AIOS. Провайдер-агностичный CLI-ассистент с локальным intent engine, tool registry, rule-based планировщиком и исполнителем.

## Установка

```bash
uv venv
uv pip install -e .
```

или

```bash
pip install -e . --break-system-packages
```

## Команды

| Команда | Описание |
|---|---|
| `aios` | Интро-панель |
| `aios ask "..."` | Одноразовый запрос |
| `aios chat` | Интерактивный чат |
| `aios code` | Режим кодинга |
| `aios doctor` | Диагностика окружения и провайдера |
| `aios config --show` | Показать конфиг |
| `aios config --set-provider ollama --set-model qwen3:8b` | Изменить конфиг |
| `aios history` | История разговоров |
| `aios tools` | Список инструментов |
| `aios models` | Список моделей провайдера |
| `aios version` | Версия |

## Конфигурация

`~/.aios/config.toml` создаётся автоматически при первом запуске.

## Архитектура

```
src/aios/
  core/       модели данных (Message, Conversation, Plan, ToolResult)
  events/     событийная шина
  intent/     локальный rule-based intent classifier
  planner/    построение Plan из Intent
  executor/   выполнение Plan через Tool Registry
  providers/  LLMProvider interface + Ollama/OpenAI-compatible
  tools/      Tool interface + filesystem/shell/git/openapp/clipboard/browser/environment
  templates/  JSON-описания команд
  memory/     SQLite история
  config/     TOML настройки
  logging/    структурированные логи
  cli/        Typer + Rich интерфейс
```

Intent Engine перехватывает простые команды (`open chrome`, `create folder x`, `git status`, `run <cmd>`) до похода к LLM. Всё остальное уходит в выбранного провайдера.

Providers и Tools регистрируются через реестры — новый провайдер или инструмент добавляется без изменения существующего кода (Open/Closed).

## Roadmap

- LLM-based планирование (сейчас только rule-based)
- Plugin architecture (интерфейсы готовы, реализации нет)
- Voice, Vision, Desktop UI, Computer Use, MCP, memory embeddings, автономные агенты — следующие вехи
- AIOS Desktop переиспользует `aios.core`, `aios.providers`, `aios.tools` напрямую

## Тесты

```bash
pytest tests/ --asyncio-mode=auto
```
