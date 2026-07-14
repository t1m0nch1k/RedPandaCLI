from __future__ import annotations

import asyncio
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool
from aios.workspace import WorkspaceContext


class ShellTool(Tool):
    name = "shell"
    description = "Run a shell command"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to run from the workspace root"},
        },
        "required": ["command"],
    }

    def __init__(self, workspace: WorkspaceContext | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()

    async def run(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        if not command:
            return ToolResult(success=False, error="No command provided")

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.workspace.root),
        )
        stdout, stderr = await proc.communicate()
        return ToolResult(
            success=proc.returncode == 0,
            output=stdout.decode(errors="ignore"),
            error=stderr.decode(errors="ignore"),
        )
