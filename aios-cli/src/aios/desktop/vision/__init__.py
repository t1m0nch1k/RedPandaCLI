"""AIOS Vision — захват и анализ экрана."""

from __future__ import annotations

from typing import Any

from .capture import capture_screen_png
from .module import BasicVision


def create_vision(config: dict[str, Any] | None = None) -> BasicVision:
    """Фабрика Vision-плагина по конфигу settings/vision."""
    vision = BasicVision()
    if config:
        vision.configure(config)
    return vision


__all__ = ["BasicVision", "capture_screen_png", "create_vision"]
