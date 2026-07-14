from __future__ import annotations

import asyncio
import platform
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class OpenAppTool(Tool):
    name = "open_app"
    description = "Open an application by name"

    async def run(self, **kwargs: Any) -> ToolResult:
        app = kwargs.get("app", "")
        if not app:
            return ToolResult(success=False, error="No app provided")

        system = platform.system()
        if system == "Darwin":
            cmd = f"open -a '{app}'"
        elif system == "Windows":
            cmd = f"start {app}"
        else:
            cmd = f"nohup {app} >/dev/null 2>&1 &"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        success = proc.returncode == 0
        return ToolResult(
            success=success,
            output=f"Launched {app}" if success else "",
            error=stderr.decode(errors="ignore") if not success else "",
        )
