"""AIOS Overlay — глобальные хоткеи и компактный оверлей в стиле Perplexity Computer.

Отдельный процесс (не плагин ядра). Подключается к ядру как WS-клиент
к ws://127.0.0.1:8765. Запуск:

    python -m aios_overlay

Хоткеи читаются из settings/default.json (секция ``hotkeys``), перерегистрируются
по событию ``settings.updated`` без рестарта демона.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
