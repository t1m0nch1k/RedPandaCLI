"""OverlayApp — связывает конфиг, хоткеи, IPC и окно оверлея.

Потоки выполнения:
  • Главный поток — PySide6 GUI event-loop (QApplication.exec).
  • Фоновый поток — OverlayIPC (asyncio WS-клиент к ядру).
  • keyboard — свой worker-поток; колбэк хоткея испускает Qt-сигнал,
    который обрабатывается в главном потоке (правило Qt: виджеты
    создаются/трогаются только в GUI-потоке).

Хоткей 1 (main_window) → focus_aios_window().
Хоткей 2 (overlay)      → screenshot → показ OverlayWindow → при отправке
                          vision.analyze_image → chat.send с screen_analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication

from . import screenshot as screenshot_mod
from .config import OverlayConfig, load_config
from .focus_window import focus_aios_window
from .hotkeys import HotkeyManager
from .ipc_client import OverlayIPC
from .overlay_window import CursorPreviewOverlay, OverlayWindow
from .screenshot import capture_png

log = logging.getLogger("aios.overlay.app")


class _SignalBridge(QObject):
    """Мост сигналов из фоновых потоков (keyboard, IPC) в GUI-поток."""

    trigger_main_window = Signal()
    trigger_overlay = Signal()
    settings_changed = Signal(dict)
    answer_received = Signal(str)
    cursor_preview_signal = Signal(dict)


class OverlayApp:
    """Главный класс оверлей-демона."""

    def __init__(self, config: OverlayConfig | None = None) -> None:
        self.config = config or load_config()
        self._qt_app: QApplication | None = None
        self._window: OverlayWindow | None = None
        self._bridge = _SignalBridge()
        self._hotkeys = HotkeyManager()
        self._ipc: OverlayIPC | None = None
        self._last_screenshot_png: bytes = b""
        self._last_screenshot_b64: str = ""
        # Вопрос пользователя, ждущий завершения vision.analyze_image
        self._pending_question: str = ""
        self._cursor_preview: CursorPreviewOverlay | None = None

    # ------------------------------------------------------------- lifecycle

    def run(self) -> int:
        """Запустить демон. Возвращает exit code."""
        self._qt_app = QApplication.instance() or QApplication([])
        self._qt_app.setQuitOnLastWindowClosed(False)  # демон живёт без окон

        self._window = OverlayWindow(on_submit=self._handle_submit)

        self._ipc = OverlayIPC(
            host=self.config.ipc.host,
            port=self.config.ipc.port,
            on_settings_updated=lambda payload: self._bridge.settings_changed.emit(payload),
            on_reply=self._on_ipc_reply,
            on_cursor_preview=lambda payload: self._bridge.cursor_preview_signal.emit(payload),
        )
        self._ipc.start()

        # Сигналы обрабатываются в GUI-потоке
        self._bridge.trigger_main_window.connect(self._do_focus_main)
        self._bridge.trigger_overlay.connect(self._do_show_overlay)
        self._bridge.settings_changed.connect(self._do_reload_hotkeys)
        self._bridge.answer_received.connect(self._do_show_answer)
        self._bridge.cursor_preview_signal.connect(self._do_cursor_preview)

        self._register_hotkeys()

        log.info(
            "AIOS Overlay запущен. Хоткеи: main=%s overlay=%s | ядро: ws://%s:%d",
            self.config.hotkeys.main_window,
            self.config.hotkeys.overlay,
            self.config.ipc.host,
            self.config.ipc.port,
        )

        return self._qt_app.exec()

    def stop(self) -> None:
        """Остановить демон."""
        self._hotkeys.unregister_all()
        if self._ipc:
            self._ipc.stop()

    # ------------------------------------------------------------- хоткеи

    def _register_hotkeys(self) -> None:
        """Зарегистрировать оба хоткея из текущего конфига."""
        self._hotkeys.register(
            self.config.hotkeys.main_window,
            lambda: self._bridge.trigger_main_window.emit(),
        )
        self._hotkeys.register(
            self.config.hotkeys.overlay,
            lambda: self._bridge.trigger_overlay.emit(),
        )

    @Slot(dict)
    def _do_reload_hotkeys(self, payload: dict[str, Any]) -> None:
        """Перерегистрировать хоткеи при settings.updated."""
        new_cfg = load_config(self.config.settings_dir)
        changed = (
            new_cfg.hotkeys.main_window != self.config.hotkeys.main_window
            or new_cfg.hotkeys.overlay != self.config.hotkeys.overlay
        )
        self.config = new_cfg

        if self._ipc and (
            self._ipc.host != new_cfg.ipc.host or self._ipc.port != new_cfg.ipc.port
        ):
            log.info("IPC-адрес изменился — потребуется рестарт демона для применения")

        if changed:
            log.info(
                "Хоткеи изменились — перерегистрация: main=%s overlay=%s",
                new_cfg.hotkeys.main_window,
                new_cfg.hotkeys.overlay,
            )
            self._hotkeys.unregister_all()
            self._register_hotkeys()

    # ------------------------------------------------------------- действия

    @Slot()
    def _do_focus_main(self) -> None:
        """Хоткей 1: сфокусировать/показать главное Tauri-окно."""
        if not focus_aios_window():
            log.warning("Не удалось сфокусировать главное окно")

    @Slot()
    def _do_show_overlay(self) -> None:
        """Хоткей 2: снять скриншот и показать оверлей."""
        try:
            self._last_screenshot_png = capture_png()
            self._last_screenshot_b64 = screenshot_mod.capture_base64()
        except Exception:  # noqa: BLE001
            log.exception("Не удалось снять скриншот")
            self._last_screenshot_png = b""
            self._last_screenshot_b64 = ""

        if self._window is None:
            return
        self._window.show_with_screenshot(self._last_screenshot_png)

    def _handle_submit(self, text: str) -> None:
        """Пользователь нажал Ask в оверлее (вызывается из GUI-потока)."""
        if not self._ipc:
            if self._window:
                self._window.append_answer("IPC-клиент не запущен.")
            return

        if self._window:
            self._window.set_thinking()

        if self._last_screenshot_b64:
            # Сохраняем вопрос — он уйдёт в chat.send после получения analysis.
            self._pending_question = text
            self._ipc.call_from_gui(
                "vision.analyze_image",
                {"image_base64": self._last_screenshot_b64},
            )
        else:
            # Без скриншота — просто текстовый запрос.
            self._ipc.call_from_gui("chat.send", {"text": text, "stream": True})

    def _on_ipc_reply(self, method: str, result: dict[str, Any]) -> None:
        """Колбэк из IPC-потока — диспетчеризуем по method."""
        if method == "vision.analyze_image":
            screen_analysis = {
                "summary": result.get("summary", ""),
                "windows": result.get("windows", []),
                "text": result.get("text", []),
            }
            text = self._pending_question
            self._pending_question = ""
            if text and self._ipc:
                self._ipc.call_from_gui(
                    "chat.send",
                    {
                        "text": text,
                        "stream": True,
                        "context": {"screen_analysis": screen_analysis},
                    },
                )
        elif method == "chat.send":
            # При подтверждении запуска от сервера ("started") не сбрасываем плашку, а ждём события chat.done / chat.error
            if isinstance(result, dict) and result.get("status") == "started":
                return
            reply = ""
            if isinstance(result, dict):
                reply = result.get("reply") or str(result.get("error") or "")
            if reply:
                self._bridge.answer_received.emit(reply)
        elif method == "chat.done":
            reply = result.get("reply", "") if isinstance(result, dict) else str(result)
            self._bridge.answer_received.emit(reply)
        elif method == "chat.error":
            err = result.get("error", "Error") if isinstance(result, dict) else str(result)
            self._bridge.answer_received.emit(f"Ошибка: {err}")

    @Slot(str)
    def _do_show_answer(self, reply: str) -> None:
        if self._window:
            self._window.append_answer(reply or "(пустой ответ)")

    # --------------------------------------------------------- cursor preview

    @Slot(dict)
    def _do_cursor_preview(self, payload: dict[str, Any]) -> None:
        """Показать CursorPreviewOverlay при cursor.preview от ядра."""
        if self._cursor_preview is not None:
            self._cursor_preview.close()
            self._cursor_preview = None

        action = payload.get("action", "")
        params = payload.get("params", {})
        delay = payload.get("delay", 1.5)
        action_id = payload.get("action_id", "")

        target = self._resolve_cursor_target(action, params)
        if target is None:
            return

        self._cursor_preview = CursorPreviewOverlay(
            action_id=action_id,
            target_x=target[0],
            target_y=target[1],
            on_cancel=self._send_cursor_cancel,
            delay=delay,
        )

    def _send_cursor_cancel(self, action_id: str) -> None:
        """Отправить cursor.cancel в ядро."""
        if self._ipc:
            self._ipc.call_from_gui("cursor.cancel", {"action_id": action_id})

    @staticmethod
    def _resolve_cursor_target(action: str, params: dict[str, Any]) -> tuple[int, int] | None:
        """Извлечь (x, y) для предпросмотра из параметров действия."""
        if action == "move_mouse":
            return (int(params["x"]), int(params["y"]))
        if action == "click":
            x = params.get("x")
            y = params.get("y")
            if x is not None and y is not None:
                return (int(x), int(y))
            return None  # клик в текущей позиции — не показываем
        if action == "drag":
            return (int(params["to_x"]), int(params["to_y"]))
        if action == "scroll":
            x = params.get("x")
            y = params.get("y")
            if x is not None and y is not None:
                return (int(x), int(y))
            return None
        return None
