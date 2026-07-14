from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PLUGINS_CONFIG_DIR = Path.home() / ".aios" / "plugins"
PLUGINS_CONFIG_FILE = PLUGINS_CONFIG_DIR / "config.json"
PLUGINS_INSTALL_DIR = PLUGINS_CONFIG_DIR / "installed"


def ensure_dirs() -> None:
    PLUGINS_INSTALL_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    ensure_dirs()
    if not PLUGINS_CONFIG_FILE.exists():
        default = {"plugins": {}}
        PLUGINS_CONFIG_FILE.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    try:
        return json.loads(PLUGINS_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"plugins": {}}


def save_config(config: dict[str, Any]) -> None:
    ensure_dirs()
    PLUGINS_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_plugin_config(name: str) -> dict[str, Any]:
    config = load_config()
    return config.get("plugins", {}).get(name, {})


def set_plugin_config(name: str, cfg: dict[str, Any]) -> None:
    config = load_config()
    config.setdefault("plugins", {})[name] = cfg
    save_config(config)


def is_plugin_enabled(name: str) -> bool:
    cfg = get_plugin_config(name)
    return cfg.get("enabled", True)


def set_plugin_enabled(name: str, enabled: bool) -> None:
    cfg = get_plugin_config(name)
    cfg["enabled"] = enabled
    set_plugin_config(name, cfg)


def get_installed_plugins() -> list[dict[str, Any]]:
    ensure_dirs()
    plugins = []
    if not PLUGINS_INSTALL_DIR.exists():
        return plugins
    for child in sorted(PLUGINS_INSTALL_DIR.iterdir()):
        if child.is_dir() and (child / "plugin.py").exists():
            plugins.append({
                "name": child.name,
                "path": str(child),
                "source": _get_source(child),
            })
    return plugins


def _get_source(plugin_dir: Path) -> str:
    marker = plugin_dir / ".source"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    return f"local:{plugin_dir.name}"


def set_source(plugin_dir: Path, source: str) -> None:
    (plugin_dir / ".source").write_text(source, encoding="utf-8")
