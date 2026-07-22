"""Захват скриншота экрана перед открытием оверлея.

Кроссплатформенно через mss (как в modules/vision/aios_vision/capture.py).
Возвращает PNG-байты + base64-строку для передачи в ядро.
"""

from __future__ import annotations

import base64
import io
import logging

log = logging.getLogger("aios.overlay.screenshot")


def capture_png(monitor_index: int = 1) -> bytes:
    """Снять скриншот основного монитора, вернуть PNG-байты (синхронно)."""
    import mss
    from PIL import Image

    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png = buf.getvalue()
    log.info("Скриншот снят: %d байт", len(png))
    return png


def capture_base64(monitor_index: int = 1) -> str:
    """Снять скриншот, вернуть base64-строку."""
    return base64.b64encode(capture_png(monitor_index)).decode("ascii")
