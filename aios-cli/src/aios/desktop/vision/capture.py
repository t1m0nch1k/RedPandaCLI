"""Захват скриншота экрана через mss (кроссплатформенно)."""

from __future__ import annotations

import asyncio
import io
import logging

log = logging.getLogger("aios.vision.capture")


def _capture_sync(monitor_index: int = 1) -> bytes:
    import mss
    from PIL import Image

    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


async def capture_screen_png(monitor_index: int = 1) -> bytes:
    """Снять скриншот основного монитора, вернуть PNG-байты."""
    png = await asyncio.to_thread(_capture_sync, monitor_index)
    log.info("Скриншот снят: %d байт", len(png))
    return png
