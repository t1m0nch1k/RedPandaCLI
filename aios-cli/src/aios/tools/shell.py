from __future__ import annotations

import asyncio
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool
from aios.workspace import WorkspaceContext


import os

MAX_OUTPUT_BYTES = 50_000


class ShellTool(Tool):
    name = "shell"
    description = "Run a shell command with security timeouts and non-interactive safeguards"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Command to run from the workspace root"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
        },
        "required": ["command"],
    }

    def __init__(self, workspace: WorkspaceContext | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()

    async def run(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = float(kwargs.get("timeout", 60.0))
        if not command:
            return ToolResult(success=False, error="No command provided")

        env = dict(os.environ)
        env["CI"] = "true"
        env["DEBIAN_FRONTEND"] = "noninteractive"

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace.root),
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            out_str = stdout.decode(errors="ignore")
            err_str = stderr.decode(errors="ignore")

            if len(out_str) > MAX_OUTPUT_BYTES:
                out_str = out_str[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"

            return ToolResult(
                success=proc.returncode == 0,
                output=out_str,
                error=err_str,
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                pass
            return ToolResult(
                success=False,
                error=f"Command execution timed out after {timeout} seconds.",
            )
