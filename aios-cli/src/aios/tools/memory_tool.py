from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class MemoryTool(Tool):
    name = "memory_tool"
    description = (
        "Interact with your long-term memory. Use this to store important facts "
        "about the user or the project, search for past events, or list recent memories."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["store", "search", "list", "forget"],
                "description": "The action to perform",
            },
            "content": {
                "type": "string",
                "description": "The text content to store (required for 'store')",
            },
            "category": {
                "type": "string",
                "enum": ["fact", "event", "preference", "insight"],
                "description": "Category of the memory (used for 'store')",
            },
            "importance": {
                "type": "integer",
                "description": "Importance from 1 to 10 (used for 'store')",
                "minimum": 1,
                "maximum": 10,
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags associated with the memory (used for 'store')",
            },
            "query": {
                "type": "string",
                "description": "Search query (required for 'search')",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return for search/list",
                "default": 10,
            },
            "memory_id": {
                "type": "integer",
                "description": "The ID of the memory to forget (required for 'forget')",
            },
        },
        "required": ["action"],
    }

    def __init__(self, memory_engine: Any):
        super().__init__()
        self.memory_engine = memory_engine

    async def run(
        self,
        action: str,
        content: str = "",
        category: str = "fact",
        importance: int = 5,
        tags: list[str] | None = None,
        query: str = "",
        limit: int = 10,
        memory_id: int = 0,
        **kwargs: Any,
    ) -> ToolResult:
        if action == "store":
            if not content:
                return ToolResult(success=False, error="content is required for store action")
            new_id = self.memory_engine.store(content, category, importance, tags)
            return ToolResult(success=True, output=f"Stored memory with ID {new_id}")
            
        elif action == "search":
            if not query:
                return ToolResult(success=False, error="query is required for search action")
            results = self.memory_engine.recall(query, limit=limit)
            return ToolResult(success=True, output=self._format_results(results))
            
        elif action == "list":
            results = self.memory_engine.recall_recent(limit=limit)
            return ToolResult(success=True, output=self._format_results(results))
            
        elif action == "forget":
            if not memory_id:
                return ToolResult(success=False, error="memory_id is required for forget action")
            success = self.memory_engine.forget(memory_id)
            if success:
                return ToolResult(success=True, output=f"Memory {memory_id} forgotten.")
            else:
                return ToolResult(success=False, error=f"Memory {memory_id} not found.")
                
        return ToolResult(success=False, error=f"Unknown action {action}")

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        if not results:
            return "No memories found."
        
        lines = []
        for r in results:
            lines.append(f"[{r['id']}] {r['created_at']} ({r['category']}, imp:{r['importance']})")
            lines.append(f"Content: {r['content']}")
            if r.get('metadata'):
                lines.append(f"Meta: {r['metadata']}")
            lines.append("---")
        return "\n".join(lines)
