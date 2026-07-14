from __future__ import annotations

import os
import webbrowser
from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class ClipboardTool(Tool):
    name = "clipboard"
    description = "Read or write the system clipboard"

    async def run(self, **kwargs: Any) -> ToolResult:
        try:
            import pyperclip
        except ImportError:
            return ToolResult(success=False, error="pyperclip not installed")

        action = kwargs.get("action", "read")
        if action == "write":
            pyperclip.copy(kwargs.get("text", ""))
            return ToolResult(success=True, output="Copied to clipboard")
        return ToolResult(success=True, output=pyperclip.paste())


class BrowserTool(Tool):
    name = "browser"
    description = "Open a URL in the default browser"

    async def run(self, **kwargs: Any) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(success=False, error="No url provided")
        opened = webbrowser.open(url)
        return ToolResult(success=opened, output=f"Opened {url}" if opened else "")


class EnvironmentTool(Tool):
    name = "environment"
    description = "Read environment variables"

    async def run(self, **kwargs: Any) -> ToolResult:
        key = kwargs.get("key", "")
        if not key:
            return ToolResult(success=True, data=dict(os.environ))
        value = os.environ.get(key)
        if value is None:
            return ToolResult(success=False, error=f"{key} is not set")
        return ToolResult(success=True, output=value)
