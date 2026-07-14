from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from aios.plugins.base import Plugin
from aios.plugins.config import PLUGINS_INSTALL_DIR

logger = logging.getLogger(__name__)

PLUGIN_MODULE_NAME = "plugin"
PLUGIN_ENTRY_ATTR = "plugin"
PLUGIN_CLASS_SUFFIX = "Plugin"

LOCAL_PLUGIN_DIRS = [
    Path.cwd() / "plugins",
    Path.home() / ".aios" / "plugins" / "installed",
]


def discover_plugin_dirs() -> list[Path]:
    dirs = []
    for d in LOCAL_PLUGIN_DIRS:
        if d.exists():
            for child in sorted(d.iterdir()):
                if child.is_dir() and (child / f"{PLUGIN_MODULE_NAME}.py").exists():
                    dirs.append(child)
    return dirs


def load_plugin_from_dir(plugin_dir: Path) -> Plugin | None:
    plugin_file = plugin_dir / f"{PLUGIN_MODULE_NAME}.py"
    if not plugin_file.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            f"aios_plugins.{plugin_dir.name}.{PLUGIN_MODULE_NAME}",
            plugin_file,
        )
        if not spec or not spec.loader:
            logger.error("Failed to create spec for %s", plugin_dir.name)
            return None

        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)

        plugin_class = _find_plugin_class(mod, plugin_dir.name)
        if plugin_class is None:
            return None

        instance = plugin_class()
        logger.info("Loaded plugin: %s v%s", instance.name, instance.metadata.version)
        return instance

    except Exception as e:
        logger.error("Failed to load plugin from %s: %s", plugin_dir, e)
        return None


def _find_plugin_class(mod: object, hint: str) -> type[Plugin] | None:
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        obj = getattr(mod, attr_name)
        if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
            return obj

    return None


def load_all_plugins() -> list[Plugin]:
    loaded: list[Plugin] = []
    for plugin_dir in discover_plugin_dirs():
        plugin = load_plugin_from_dir(plugin_dir)
        if plugin is not None:
            loaded.append(plugin)
    return loaded


def install_from_git(url: str, name: str | None = None) -> Path | None:
    import subprocess

    if name is None:
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

    target = PLUGINS_INSTALL_DIR / name
    if target.exists():
        logger.warning("Plugin '%s' already installed at %s", name, target)
        return target

    PLUGINS_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr)
            return None

        from aios.plugins.config import set_source
        set_source(target, url)
        logger.info("Installed plugin '%s' from %s", name, url)
        return target

    except FileNotFoundError:
        logger.error("git not found. Install git to use plugin install from URLs.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("git clone timed out.")
        return None


def install_from_path(path: str) -> Path | None:
    src = Path(path).expanduser().resolve()
    if not src.exists():
        logger.error("Plugin path does not exist: %s", src)
        return None

    name = src.name
    target = PLUGINS_INSTALL_DIR / name

    if target.exists():
        logger.warning("Plugin '%s' already installed at %s", name, target)
        return target

    import shutil
    shutil.copytree(src, target)
    from aios.plugins.config import set_source
    set_source(target, str(src))
    logger.info("Installed plugin '%s' from %s", name, src)
    return target
