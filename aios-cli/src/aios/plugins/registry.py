from __future__ import annotations

import logging
from typing import Any

from aios.hooks.manager import HookManager
from aios.plugins.base import Plugin
from aios.plugins.config import get_installed_plugins, is_plugin_enabled, set_plugin_enabled
from aios.plugins.loader import load_all_plugins, load_plugin_from_dir
from aios.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(self, tool_registry: ToolRegistry | None = None, hook_manager: HookManager | None = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._tool_registry = tool_registry
        self._hook_manager = hook_manager

    def set_tool_registry(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry

    def set_hook_manager(self, hook_manager: HookManager) -> None:
        self._hook_manager = hook_manager

    def get_plugin(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def list_installed(self) -> list[dict[str, Any]]:
        return get_installed_plugins()

    async def load(self, name: str) -> Plugin | None:
        if name in self._plugins:
            return self._plugins[name]

        from aios.plugins.loader import LOCAL_PLUGIN_DIRS
        for base in LOCAL_PLUGIN_DIRS:
            plugin_dir = base / name
            if plugin_dir.exists() and (plugin_dir / "plugin.py").exists():
                return await self._load_from_dir(plugin_dir)

        logger.warning("Plugin '%s' not found in any plugin directory", name)
        return None

    async def load_all(self) -> list[Plugin]:
        loaded = load_all_plugins()
        for plugin in loaded:
            await self._register_plugin(plugin)
        return loaded

    async def load_from_dir(self, plugin_dir) -> Plugin | None:
        return await self._load_from_dir(plugin_dir)

    async def _load_from_dir(self, plugin_dir) -> Plugin | None:
        plugin = load_plugin_from_dir(plugin_dir)
        if plugin is None:
            return None
        await self._register_plugin(plugin)
        return plugin

    async def _register_plugin(self, plugin: Plugin) -> None:
        name = plugin.name
        if not name:
            logger.warning("Plugin has no name, skipping")
            return

        if not is_plugin_enabled(name):
            plugin.set_enabled(False)
            self._plugins[name] = plugin
            logger.info("Plugin '%s' is disabled, skipping registration", name)
            return

        try:
            await plugin.on_load()
        except Exception as e:
            logger.error("Plugin '%s' on_load failed: %s", name, e)

        if self._tool_registry and plugin.enabled:
            for tool in plugin.get_tools():
                self._tool_registry.register(tool)
                logger.debug("Plugin '%s' registered tool: %s", name, tool.name)

        if self._hook_manager and plugin.enabled:
            for event, callback in plugin.get_hooks():
                self._hook_manager.register(event, callback)
                logger.debug("Plugin '%s' registered hook on: %s", name, event.name)

        self._plugins[name] = plugin
        logger.info("Registered plugin: %s v%s", name, plugin.metadata.version)

    async def unload(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin is None:
            return False

        plugin.set_enabled(False)
        set_plugin_enabled(name, False)

        try:
            await plugin.on_unload()
        except Exception as e:
            logger.error("Plugin '%s' on_unload failed: %s", name, e)

        if self._tool_registry:
            for tool in plugin.get_tools():
                self._tool_registry._tools.pop(tool.name, None)

        logger.info("Unloaded plugin: %s", name)
        return True

    async def enable(self, name: str) -> bool:
        plugin = self._plugins.get(name)
        if plugin is None:
            plugin = await self.load(name)
            if plugin is None:
                logger.warning("Plugin '%s' not found, cannot enable", name)
                return False

        if not plugin.enabled:
            plugin.set_enabled(True)
            set_plugin_enabled(name, True)

            if self._tool_registry:
                for tool in plugin.get_tools():
                    self._tool_registry.register(tool)

            if self._hook_manager:
                for event, callback in plugin.get_hooks():
                    self._hook_manager.register(event, callback)

            logger.info("Enabled plugin: %s", name)

        return True

    async def disable(self, name: str) -> bool:
        return await self.unload(name)

    async def reload(self, name: str) -> bool:
        await self.unload(name)
        plugin = await self.load(name)
        return plugin is not None
