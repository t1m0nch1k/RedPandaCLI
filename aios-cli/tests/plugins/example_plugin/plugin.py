from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.hooks.events import HookAction, HookContext, HookEvent
from aios.plugins.base import Plugin, PluginMetadata
from aios.tools.base import Tool


class HelloTool(Tool):
    name = "hello"
    description = "Says hello from a plugin"
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Who to greet"},
        },
        "required": [],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        target = kwargs.get("name", "World")
        return ToolResult(success=True, output=f"Hello, {target}! (from plugin)")


class EchoHookTool(Tool):
    name = "echo_test"
    description = "Echoes input back"
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to echo"},
        },
        "required": ["text"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, output=kwargs.get("text", ""))


async def post_tool_logger(ctx: HookContext) -> HookAction:
    if ctx.tool_name and ctx.tool_result:
        pass
    return HookAction.CONTINUE


class ExamplePlugin(Plugin):
    metadata = PluginMetadata(
        name="example",
        version="1.0.0",
        description="Example plugin for testing",
        author="AIOS",
    )

    def get_tools(self) -> list[Tool]:
        return [HelloTool(), EchoHookTool()]

    def get_hooks(self) -> list[tuple[HookEvent, HookCallable]]:
        return [(HookEvent.POST_TOOL, post_tool_logger)]


plugin = ExamplePlugin()
