from __future__ import annotations

from pathlib import Path

import pytest
from aios.core.models import ToolResult
from aios.hooks.events import HookAction, HookContext, HookEvent
from aios.hooks.manager import HookManager
from aios.plugins.base import Plugin, PluginMetadata
from aios.plugins.config import PLUGINS_CONFIG_DIR, load_config, save_config
from aios.plugins.loader import load_plugin_from_dir
from aios.plugins.registry import PluginRegistry
from aios.tools.base import Tool
from aios.tools.registry import ToolRegistry


class DummyTool(Tool):
    name = "dummy"
    description = "Dummy test tool"
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, **kwargs):
        return ToolResult(success=True, output="dummy")


async def dummy_hook(ctx: HookContext) -> HookAction:
    return HookAction.CONTINUE


class TestPlugin(Plugin):
    metadata = PluginMetadata(
        name="test-plugin",
        version="1.0.0",
        description="Test plugin",
        author="test",
    )

    def get_tools(self):
        return [DummyTool()]

    def get_hooks(self):
        return [(HookEvent.POST_TOOL, dummy_hook)]


@pytest.fixture(autouse=True)
def clean_config():
    saved = ""
    cfg_file = PLUGINS_CONFIG_DIR / "config.json"
    if cfg_file.exists():
        saved = cfg_file.read_text()
    yield
    if saved:
        cfg_file.write_text(saved)
    elif cfg_file.exists():
        cfg_file.unlink()


@pytest.mark.asyncio
async def test_plugin_base():
    p = TestPlugin()
    assert p.name == "test-plugin"
    assert p.metadata.version == "1.0.0"
    assert p.enabled is True
    assert len(p.get_tools()) == 1
    assert len(p.get_hooks()) == 1
    assert p.get_config() == {}

    result = await p.get_tools()[0].run()
    assert result.success
    assert result.output == "dummy"


@pytest.mark.asyncio
async def test_plugin_registry_register():
    tool_registry = ToolRegistry()
    hook_manager = HookManager()
    registry = PluginRegistry(tool_registry, hook_manager)

    p = TestPlugin()
    await registry._register_plugin(p)

    assert registry.get_plugin("test-plugin") is p
    assert tool_registry.get("dummy") is not None
    assert len(hook_manager._hooks[HookEvent.POST_TOOL]) > 0


@pytest.mark.asyncio
async def test_plugin_registry_unload():
    tool_registry = ToolRegistry()
    hook_manager = HookManager()
    registry = PluginRegistry(tool_registry, hook_manager)

    p = TestPlugin()
    await registry._register_plugin(p)
    assert registry.get_plugin("test-plugin") is not None

    result = await registry.unload("test-plugin")
    assert result is True
    p = registry.get_plugin("test-plugin")
    assert p is not None
    assert p.enabled is False


@pytest.mark.asyncio
async def test_plugin_registry_enable_disable():
    tool_registry = ToolRegistry()
    hook_manager = HookManager()
    registry = PluginRegistry(tool_registry, hook_manager)

    p = TestPlugin()
    await registry._register_plugin(p)

    await registry.disable("test-plugin")
    p = registry.get_plugin("test-plugin")
    assert p is not None, "Plugin should remain in registry after disable"
    assert p.enabled is False

    await registry.enable("test-plugin")
    p = registry.get_plugin("test-plugin")
    assert p is not None
    assert p.enabled is True


@pytest.mark.asyncio
async def test_load_example_plugin_from_dir():
    test_dir = Path(__file__).parent / "plugins" / "example_plugin"
    assert test_dir.exists(), f"Example plugin dir not found: {test_dir}"

    plugin = load_plugin_from_dir(test_dir)
    assert plugin is not None, "Failed to load example plugin"
    assert plugin.name == "example"
    assert plugin.metadata.version == "1.0.0"

    tools = plugin.get_tools()
    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "hello" in tool_names
    assert "echo_test" in tool_names

    hello = next(t for t in tools if t.name == "hello")
    result = await hello.run(name="Test")
    assert result.success
    assert "Hello, Test!" in result.output

    hooks = plugin.get_hooks()
    assert len(hooks) == 1
    assert hooks[0][0] == HookEvent.POST_TOOL


@pytest.mark.asyncio
async def test_plugin_config():
    save_config({"plugins": {"test-p": {"enabled": True, "setting": 42}}})
    cfg = load_config()
    assert cfg["plugins"]["test-p"]["enabled"] is True
    assert cfg["plugins"]["test-p"]["setting"] == 42

    from aios.plugins.config import get_plugin_config, is_plugin_enabled, set_plugin_config, set_plugin_enabled
    assert is_plugin_enabled("test-p") is True
    set_plugin_enabled("test-p", False)
    assert is_plugin_enabled("test-p") is False
    set_plugin_config("other", {"foo": "bar"})
    assert get_plugin_config("other")["foo"] == "bar"


@pytest.mark.asyncio
async def test_catalog():
    from aios.plugins.catalog import find_in_catalog, get_catalog_entries, get_catalog_names
    entries = get_catalog_entries()
    assert len(entries) > 0

    entry = find_in_catalog("web-search")
    assert entry is not None
    assert entry["name"] == "web-search"
    assert "repo" in entry

    assert find_in_catalog("nonexistent") is None
    names = get_catalog_names()
    assert "web-search" in names
