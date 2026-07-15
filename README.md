<div align="center">
  <img src="img/mascot.png" alt="AIOS Mascot" width="150" />
  <h1>🐼 RedPandaCLI (AIOS CLI)</h1>
  <p><b>Провайдер-агностичный AI Co-Pilot для терминала</b></p>
  
  [![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)](https://github.com/t1m0nch1k/RedPandaCLI)
  [![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
</div>

---

**RedPandaCLI** (AIOS CLI) — это мощный AI-ассистент для вашего терминала. Он работает более чем с 30+ LLM-провайдерами, пишет код, помогает управлять Git, анализирует логи и запускает команды. Ваша территория — ваши правила!

## ✨ Особенности проекта

* 🚀 **Провайдер-агностичность:** Подключайте OpenAI, Anthropic, Gemini, Ollama, или любые OpenAI-совместимые API.
* 🛡️ **Надежная архитектура:** В основе — трёхуровневая архитектура (Agent -> Conversation -> Connection) с развитой системой хуков и политик безопасности (Policy System).
* 💻 **Глубокая интеграция:** Чтение файлов, анализ директорий и выполнение команд терминала с вашего разрешения.
* 🧩 **Extensible (Плагины):** Возможность легкого добавления кастомных тулов и провайдеров через плагины.

## 📦 Установка

Склонируйте репозиторий и установите пакет:

```bash
git clone https://github.com/t1m0nch1k/RedPandaCLI.git
cd RedPandaCLI

# Установка CLI
pip install -e aios-cli
```

## 🚀 Быстрый старт

Запустите ассистента в терминале (после настройки ключей API):

```bash
aios --help
```

*Для работы веб-интерфейса презентации (Landing page):*
Просто откройте файл `index.html` в вашем браузере.

## 🧠 Под капотом

Проект построен по принципу **Runtime First, Mission First, Provider Agnostic**. Включает в себя:
* **Hook System:** Гибкие хуки на старт сессии, отправку промпта, ответы моделей и выполнение тулов.
* **Permission Gate:** Декларативная система разрешений (`policy.allow_all()`, `policy.ask_user()` и др.), обеспечивающая безопасность при выполнении системных команд.

## 🤝 Контрибьюции

Пулл-реквесты (PR) приветствуются! Если у вас есть идеи по улучшению или вы нашли баг — пожалуйста, откройте *Issue*.

---
<div align="center">
  <i>Разработано для тех, кто ценит свой терминал и время.</i>
</div>
