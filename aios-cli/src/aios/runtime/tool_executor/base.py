from __future__ import annotations

from typing import Any

from aios.runtime.models import ToolCall, ToolCallDef


class ToolProtocol:
    """A callable tool that can be registered and executed by the ToolExecutor."""

    @property
    def name(self) -> str:
        """Return the tool name."""

    @property
    def description(self) -> str:
        """Return the tool description."""

    @property
    def parameters(self) -> dict[str, Any]:
        """Return the JSON schema for tool parameters."""

    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""


class ToolExecutorProtocol:
    """
    Executes tool calls with permission gating, timing, and result
    truncation. Owns the tool registry.
    """

    async def execute(
        self,
        tool_call: ToolCall,
        tool_name: str,
        args: dict[str, Any],
        conversation: Any,
    ) -> Any:
        """Single tool call: permission check, confirmation, execution, post-hook."""

    async def execute_batch(
        self,
        tool_calls: list[ToolCallDef],
        conversation: Any,
    ) -> list[Any]:
        """Execute multiple tool calls. Respects ordering if any tool call is flagged as sequential."""

    def register_tool(self, tool: ToolProtocol) -> None:
        """Register a tool."""

    def register_mcp_tools(self, tools: list[ToolProtocol]) -> None:
        """Register tools from MCP."""

    def get_tool(self, name: str) -> ToolProtocol | None:
        """Get a tool by name."""

    def list_tools(self) -> list[ToolProtocol]:
        """List all registered tools."""
