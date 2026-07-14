from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class ContextSweepTool(Tool):
    name: str = "context_sweep"
    description: str = "Manually trigger an aggressive context cleanup and summarization of successful tool outputs. Use this when the conversation has become too long and you want to proactively clear out unnecessary tool logs to save context space."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        # The engine will intercept this tool execution or just run it. 
        # But wait, if the engine needs to intercept it, how does it know?
        # We can just return a magic string that the engine looks for, or we can just 
        # let the tool return this message, and we update the Engine to check if tool == "context_sweep".
        return ToolResult(
            success=True, 
            output="Context sweep requested. The engine will perform a context sweep immediately."
        )
