from __future__ import annotations

from aios.config.settings import GitConfig
from aios.tools.base import Tool
from aios.tools.context_sweep import ContextSweepTool
from aios.tools.filesystem import FilesystemTool
from aios.tools.git import GitTool
from aios.tools.misc import BrowserTool, ClipboardTool, EnvironmentTool
from aios.tools.openapp import OpenAppTool
from aios.tools.shell import ShellTool
from aios.tools.task_manager import TaskManagerTool
from aios.tools.web.fetch import WebFetchTool
from aios.tools.web.search import WebSearchTool
from aios.workspace import WorkspaceContext


class ToolRegistry:
    def __init__(self, workspace: WorkspaceContext | None = None, git_config: GitConfig | None = None) -> None:
        self.workspace = workspace or WorkspaceContext.from_cwd()
        self.git_config = git_config
        self._tools: dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        git_kwargs = {"git_config": self.git_config} if self.git_config else {}
        for tool in (
            FilesystemTool(self.workspace),
            ShellTool(self.workspace),
            TaskManagerTool(self.workspace),
            ContextSweepTool(),
            GitTool(self.workspace, **git_kwargs),
            OpenAppTool(),
            ClipboardTool(),
            BrowserTool(),
            EnvironmentTool(),
            WebSearchTool(),
            WebFetchTool(),
        ):
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())
