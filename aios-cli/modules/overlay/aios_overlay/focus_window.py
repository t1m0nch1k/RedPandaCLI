"""Фокус/показ главного Tauri-окна приложения по заголовку через Win32.

Окно Tauri имеет title "AIOS" (frontend/src-tauri/tauri.conf.json:15). Когда окно
свёрнуто в tray (CloseRequested → window.hide()), Win32 ShowWindow(SW_RESTORE)
сначала покажет его, затем SetForegroundWindow поднимет наверх.

Windows-only; на других ОС — no-op с предупреждением.
"""

from __future__ import annotations

import logging
import sys

log = logging.getLogger("aios.overlay.focus")

# Заголовок главного окна (frontend/src-tauri/tauri.conf.json: title)
AIOS_WINDOW_TITLE = "AIOS"

# Win32 константы
SW_RESTORE = 9
SW_SHOW = 5


def focus_aios_window(title: str = AIOS_WINDOW_TITLE) -> bool:
    """Найти окно по заголовку и вывести его на передний план.

    Возвращает True, если окно найдено и активировано.
    """
    if sys.platform != "win32":
        log.warning("focus_window поддерживается только на Windows (текущая ОС: %s)", sys.platform)
        return False

    import ctypes

    user32 = ctypes.windll.user32

    hwnd = user32.FindWindowW(None, title)
    if not hwnd:
        # Fallback: перечислить окна и найти частичное совпадение по заголовку
        hwnd = _find_window_by_partial_title(title)
        if not hwnd:
            log.warning("Окно AIOS не найдено (title=%r). Tauri-приложение запущено?", title)
            return False

    # Восстановить, если свёрнуто (из tray окно спрятано — покажем)
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)

    user32.ShowWindow(hwnd, SW_SHOW)

    # SetForegroundWindow требует трюк с Alt-ключом, чтобы обойти ограничение
    # переднего плана Windows. Реализуем через ALLOW_SET_FOREGROUND.
    _bring_to_foreground(user32, hwnd)
    log.info("Фокус установлен на окно AIOS (hwnd=%s)", hwnd)
    return True


def _find_window_by_partial_title(partial: str) -> int:
    """EnumWindows: найти top-level окно, чей заголовок содержит partial."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd: int, _lparam: int) -> bool:
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if partial.lower() in buf.value.lower():
            # Только visible top-level окна
            if user32.IsWindowVisible(hwnd):
                found.append(hwnd)
                return False  # остановить перечисление
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return found[0] if found else 0


def _bring_to_foreground(user32: ctypes.WinDLL, hwnd: int) -> None:
    """SetForegroundWindow с обходом блокировки переднего плана."""

    # Трюк: симулируем отпускание/нажатие Alt, чтобы разблокировать
    # ограничение SetForegroundWindow (Windows разрешает смену fg только
    # если текущая нить не имеет фокуса ввода).
    ALT = 0x12
    user32.keybd_event(ALT, 0, 0, 0)          # key down
    user32.keybd_event(ALT, 0, 0x0002, 0)     # key up (KEYEVENTF_KEYUP)
    user32.SetForegroundWindow(hwnd)
