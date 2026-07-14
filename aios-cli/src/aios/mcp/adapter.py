from __future__ import annotations

import json
from typing import Any

from aios.core.models import ToolResult
from aios.mcp.client import MCPClient
from aios.tools.base import Tool


def _convert_mcp_schema_to_aios(mcp_input_schema: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    properties = mcp_input_schema.get("properties", {})
    required = mcp_input_schema.get("required", [])

    for key, prop in properties.items():
        result["properties"][key] = {
            k: v for k, v in prop.items()
        }

    result["required"] = list(required)
    return result


class MCPToolAdapter(Tool):
    def __init__(self, mcp_client: MCPClient, tool_def: dict[str, Any]) -> None:
        self._mcp_client = mcp_client
        self._tool_def = tool_def
        func = tool_def.get("function", tool_def)
        self._mcp_tool_name = func.get("name", tool_def.get("name", ""))
        self.name = f"mcp_{mcp_client.server_name}__{self._mcp_tool_name}"
        self.description = func.get("description", tool_def.get("description", ""))
        raw_params = func.get("parameters", func.get("inputSchema", {}))
        self.parameters = _convert_mcp_schema_to_aios(raw_params)

    async def run(self, **kwargs: Any) -> ToolResult:
        try:
            result = await self._mcp_client.call_tool(self._mcp_tool_name, kwargs)
            content_list = result.get("content", [])
            is_error = result.get("isError", False)

            output_parts = []
            for item in content_list:
                item_type = item.get("type", "text")
                if item_type == "text":
                    output_parts.append(item.get("text", ""))
                elif item_type == "resource":
                    output_parts.append(json.dumps(item.get("resource", {}), indent=2))
                else:
                    output_parts.append(json.dumps(item, indent=2))

            output = "\n".join(output_parts)

            if is_error:
                return ToolResult(success=False, error=output)
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, error=f"MCP tool '{self._mcp_tool_name}' failed: {e}")
