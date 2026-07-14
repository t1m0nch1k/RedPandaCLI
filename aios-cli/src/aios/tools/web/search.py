from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web using DuckDuckGo. Returns up to 10 results with title, url, and snippet."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (1-10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(success=False, error="No query provided")
        max_results = min(int(kwargs.get("max_results", 5)), 10)

        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(query, max_results=max_results)):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })

            if not results:
                return ToolResult(success=True, output="No results found.")

            formatted = "\n\n".join(
                f"{i+1}. [{r['title']}]({r['url']})\n   {r['snippet']}"
                for i, r in enumerate(results)
            )
            return ToolResult(success=True, output=formatted, data={"results": results})
        except ImportError:
            return ToolResult(success=False, error="duckduckgo_search not installed")
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {e}")
