from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.hooks.events import HookEvent, HookAction, HookContext
from aios.plugins.base import Plugin, PluginMetadata
from aios.tools.base import Tool


class ${plugin_name}Tool(Tool):
    name = "${plugin_name}"
    description = "$description"
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input text"},
        },
        "required": [],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        text = kwargs.get("input", "")
        return ToolResult(success=True, output=f"${plugin_name} processed: {text}")


class ${plugin_name}Plugin(Plugin):
    metadata = PluginMetadata(
        name="${plugin_name}",
        version="$version",
        description="$description",
        author="$author",
    )

    def get_tools(self) -> list[Tool]:
        return [${plugin_name}Tool()]

    def get_hooks(self) -> list[tuple[HookEvent, HookCallable]]:
        return []


plugin = ${plugin_name}Plugin()
