from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

from aios.plugins.provider_plugin import ProviderPlugin

logger = logging.getLogger(__name__)

PROVIDER_PLUGIN_DIR = Path.home() / ".aios" / "providers"

BUILTIN_PROVIDER_DIRS: list[Path] = []


def discover_builtin_provider_plugins() -> list[Path]:
    dirs = []
    for d in BUILTIN_PROVIDER_DIRS:
        if d.exists():
            for child in sorted(d.iterdir()):
                if child.is_dir() and (child / "plugin.py").exists():
                    dirs.append(child)
    return dirs


def discover_installed_provider_plugins() -> list[Path]:
    dirs = []
    if PROVIDER_PLUGIN_DIR.exists():
        for child in sorted(PROVIDER_PLUGIN_DIR.iterdir()):
            if child.is_dir() and (child / "plugin.py").exists():
                dirs.append(child)
    return dirs


def discover_all_provider_plugins() -> list[Path]:
    seen: set[Path] = set()
    dirs = []

    for d in discover_builtin_provider_plugins():
        if d not in seen:
            dirs.append(d)
            seen.add(d)

    for d in discover_installed_provider_plugins():
        if d not in seen:
            dirs.append(d)
            seen.add(d)

    return dirs


def _find_provider_plugin_class(mod: object) -> type[ProviderPlugin] | None:
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        obj = getattr(mod, attr_name)
        if isinstance(obj, type) and issubclass(obj, ProviderPlugin) and obj is not ProviderPlugin:
            return obj
    return None


def load_provider_plugin_from_dir(plugin_dir: Path) -> ProviderPlugin | None:
    plugin_file = plugin_dir / "plugin.py"
    if not plugin_file.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            f"aios_providers_plugins.{plugin_dir.name}.plugin",
            plugin_file,
        )
        if not spec or not spec.loader:
            logger.error("Failed to create spec for provider plugin %s", plugin_dir.name)
            return None

        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)

        cls = _find_provider_plugin_class(mod)
        if cls is None:
            logger.warning("No ProviderPlugin subclass found in %s", plugin_dir)
            return None

        instance: ProviderPlugin = cls()
        logger.info("Loaded provider plugin: %s v%s", instance.name, instance.metadata.version)
        return instance

    except Exception as e:
        logger.error("Failed to load provider plugin from %s: %s", plugin_dir, e)
        return None


def load_all_provider_plugins() -> list[ProviderPlugin]:
    loaded: list[ProviderPlugin] = []
    for plugin_dir in discover_all_provider_plugins():
        plugin = load_provider_plugin_from_dir(plugin_dir)
        if plugin is not None:
            loaded.append(plugin)
    return loaded


def discover_and_register_provider_plugins() -> list[str]:
    from aios.providers.registry import register_provider

    registered: list[str] = []
    for plugin in load_all_provider_plugins():
        name = plugin.metadata.name
        cls = plugin.get_provider_class()
        register_provider(name, cls)
        registered.append(name)
        logger.info("Registered provider plugin: %s", name)
    return registered


def install_provider_plugin_from_git(url: str, name: str | None = None) -> Path | None:
    import subprocess

    if name is None:
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]

    target = PROVIDER_PLUGIN_DIR / name
    if target.exists():
        logger.warning("Provider plugin '%s' already installed at %s", name, target)
        return target

    PROVIDER_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "clone", url, str(target)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr)
            return None

        logger.info("Installed provider plugin '%s' from %s", name, url)
        return target

    except FileNotFoundError:
        logger.error("git not found. Install git to use provider plugin install from URLs.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("git clone timed out.")
        return None


def install_provider_plugin_from_path(path: str) -> Path | None:
    import shutil

    src = Path(path).expanduser().resolve()
    if not src.exists():
        logger.error("Provider plugin path does not exist: %s", src)
        return None

    name = src.name
    target = PROVIDER_PLUGIN_DIR / name

    if target.exists():
        logger.warning("Provider plugin '%s' already installed at %s", name, target)
        return target

    PROVIDER_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    logger.info("Installed provider plugin '%s' from %s", name, src)
    return target
