"""BasicVision — базовый Vision-плагин.

MVP-версия: перечисляет открытые окна через pygetwindow и
(опционально) извлекает текст с экрана через pytesseract.
Заменяется на модель компьютерного зрения (например, OmniParser)
без изменения остального кода.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("aios.vision")

@dataclass
class HealthStatus:
    ok: bool
    detail: str

@dataclass
class ScreenAnalysis:
    windows: list[dict[str, Any]]
    buttons: list[dict[str, Any]]
    text: list[dict[str, Any]]

    def model_dump(self) -> dict[str, Any]:
        return {
            "windows": self.windows,
            "buttons": self.buttons,
            "text": self.text,
        }

class BasicVision:
    """Простейший анализ экрана: список окон + OCR (если доступен)."""

    name = "basic-vision"

    def __init__(self, enable_ocr: bool = False) -> None:
        self._enable_ocr = enable_ocr

    def capabilities(self) -> dict[str, Any]:
        return {"windows": True, "ocr": self._enable_ocr, "buttons": False}

    def configure(self, config: dict[str, Any]) -> None:
        self._enable_ocr = bool(config.get("enable_ocr", self._enable_ocr))

    async def health_check(self) -> HealthStatus:
        try:
            import pygetwindow  # noqa: F401

            return HealthStatus(ok=True, detail="basic-vision готов")
        except ImportError:
            return HealthStatus(
                ok=False, detail="pygetwindow не установлен: pip install pygetwindow"
            )

    async def analyze(self, image_png: bytes) -> ScreenAnalysis:
        windows = await asyncio.to_thread(self._list_windows)
        text: list[dict[str, Any]] = []
        if self._enable_ocr:
            text = await asyncio.to_thread(self._ocr, image_png)
        return ScreenAnalysis(windows=windows, buttons=[], text=text)

    # ------------------------------------------------------------------ impl

    @staticmethod
    def _list_windows() -> list[dict[str, Any]]:
        try:
            import pygetwindow as gw

            result = []
            for w in gw.getAllWindows():
                if not w.title:
                    continue
                result.append(
                    {
                        "title": w.title,
                        "left": w.left,
                        "top": w.top,
                        "width": w.width,
                        "height": w.height,
                        "active": bool(getattr(w, "isActive", False)),
                    }
                )
            return result
        except Exception as exc:  # pygetwindow может падать на Linux/Wayland
            log.warning("Не удалось получить список окон: %s", exc)
            return []

    @staticmethod
    def _ocr(image_png: bytes) -> list[dict[str, Any]]:
        try:
            import io

            import pytesseract
            from PIL import Image

            img = Image.open(io.BytesIO(image_png))
            raw = pytesseract.image_to_data(
                img, lang="rus+eng", output_type=pytesseract.Output.DICT
            )
            items = []
            for i, txt in enumerate(raw["text"]):
                txt = txt.strip()
                if not txt:
                    continue
                items.append(
                    {
                        "text": txt,
                        "left": raw["left"][i],
                        "top": raw["top"][i],
                        "width": raw["width"][i],
                        "height": raw["height"][i],
                    }
                )
            return items
        except Exception as exc:
            log.warning("OCR недоступен: %s", exc)
            return []
