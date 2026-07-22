from typing import Any

from aios.core.models import ToolResult
from aios.runtime.workspace_knowledge.engine import WorkspaceKnowledgeEngine
from aios.tools.base import Tool


class WorkspaceSearchTool(Tool):
    name = "workspace_search"
    description = (
        "Search the Python project's codebase for a specific symbol (class, function, or method name). "
        "Returns the file path, line number, and docstring of matching symbols."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The exact or partial name of the class, function, or method to search for.",
            }
        },
        "required": ["query"],
    }

    def __init__(self, knowledge_engine: WorkspaceKnowledgeEngine) -> None:
        self.engine = knowledge_engine

    async def run(self, query: str, **kwargs: Any) -> ToolResult:
        try:
            result = self.engine.search(query)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
