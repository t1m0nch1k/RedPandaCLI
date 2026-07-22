"""Загрузка конфигурации для оверлей-демона.

Читает settings/default.json (+ local.override.json) и извлекает секции ``hotkeys``
и ``ipc``. Логика deep_merge повторяет core/src/aios_core/config.py, чтобы не
зависеть от пакета ядра.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# repo_root = .../aios-platform   (modules/overlay -> .. -> ..)
REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_DIR = REPO_ROOT / "settings"


class HotkeysConfig:
    """Дефолты совпадают с core/src/aios_core/config.py:HotkeysConfig."""

    __slots__ = ("main_window", "overlay")

    def __init__(self, main_window: str = "ctrl+alt+space", overlay: str = "alt+space") -> None:
        self.main_window = main_window
        self.overlay = overlay


class IPCConfig:
    __slots__ = ("host", "port")

    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port


class OverlayConfig:
    __slots__ = ("hotkeys", "ipc", "settings_dir")

    def __init__(
        self,
        hotkeys: HotkeysConfig | None = None,
        ipc: IPCConfig | None = None,
        settings_dir: Path | None = None,
    ) -> None:
        self.hotkeys = hotkeys or HotkeysConfig()
        self.ipc = ipc or IPCConfig()
        self.settings_dir = settings_dir or SETTINGS_DIR


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_raw(settings_dir: Path | None = None) -> dict[str, Any]:
    """Загрузить конфиг как dict (default.json + local.override.json)."""
    settings_dir = settings_dir or SETTINGS_DIR
    config: dict[str, Any] = {}

    default_path = settings_dir / "default.json"
    if default_path.exists():
        config = json.loads(default_path.read_text(encoding="utf-8"))

    override_path = settings_dir / "local.override.json"
    if override_path.exists():
        override = json.loads(override_path.read_text(encoding="utf-8"))
        config = _deep_merge(config, override)

    return config


def load_config(settings_dir: Path | None = None) -> OverlayConfig:
    """Построить OverlayConfig из settings/default.json."""
    raw = load_raw(settings_dir)
    hk = raw.get("hotkeys", {})
    ipc = raw.get("ipc", {})
    return OverlayConfig(
        hotkeys=HotkeysConfig(
            main_window=hk.get("main_window", "ctrl+alt+space"),
            overlay=hk.get("overlay", "alt+space"),
        ),
        ipc=IPCConfig(
            host=ipc.get("host", "127.0.0.1"),
            port=int(ipc.get("port", 8765)),
        ),
        settings_dir=settings_dir or SETTINGS_DIR,
    )
