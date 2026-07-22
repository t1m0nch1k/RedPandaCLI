"""Регистрация глобальных хоткеев через библиотеку ``keyboard``.

``keyboard`` ловит нажатия на низовом уровне (Windows: SetWindowsHookEx) и
срабатывает в своём worker-потоке. Чтобы Qt-окно создавалось/показывалось в
главном (GUI) потоке, колбэк хоткея испускает Qt-сигнал.

API:
    hk = HotkeyManager()
    hk.register("ctrl+alt+space", on_main_window)
    hk.register("alt+space", on_overlay)
    hk.unregister_all()   # перерегистрация при settings.updated
"""

from __future__ import annotations

import logging
from collections.abc import Callable

log = logging.getLogger("aios.overlay.hotkeys")


class HotkeyManager:
    """Управление глобальными хоткеями."""

    def __init__(self) -> None:
        self._registered: list[str] = []
        self._callbacks: dict[str, Callable[[], None]] = {}

    def register(self, combo: str, callback: Callable[[], None]) -> bool:
        """Зарегистрировать хоткей. Возвращает True при успехе."""
        try:
            import keyboard
        except ImportError:
            log.error("Библиотека 'keyboard' не установлена: pip install keyboard")
            return False

        combo = (combo or "").strip().lower()
        if not combo:
            log.warning("Пустой хоткей проигнорирован")
            return False

        # Снимаем прежнюю регистрацию этого же комбо, если было
        try:
            keyboard.remove_hotkey(combo)
        except (KeyError, ValueError):
            pass
        except Exception:  # noqa: BLE001
            pass

        try:
            keyboard.add_hotkey(combo, callback, suppress=False)
            self._registered.append(combo)
            self._callbacks[combo] = callback
            log.info("Хоткей зарегистрирован: %s", combo)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Не удалось зарегистрировать хоткей %r: %s", combo, exc)
            return False

    def unregister_all(self) -> None:
        """Снять все зарегистрированные хоткеи (для перерегистрации)."""
        try:
            import keyboard
        except ImportError:
            self._registered.clear()
            self._callbacks.clear()
            return

        for combo in list(self._registered):
            try:
                keyboard.remove_hotkey(combo)
            except (KeyError, ValueError):
                pass
            except Exception:  # noqa: BLE001
                pass
        log.info("Снято хоткеев: %d", len(self._registered))
        self._registered.clear()
        self._callbacks.clear()

    def reregister_all(self) -> None:
        """Перерегистрировать текущие колбэки (после смены комбо в settings)."""
        callbacks = dict(self._callbacks)
        self.unregister_all()
        for combo, cb in callbacks.items():
            self.register(combo, cb)
