from __future__ import annotations

from typing import Any

from aios.core.models import ToolResult
from aios.tools.base import Tool


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch a URL and return its content as cleaned markdown. Useful for reading documentation, articles, or API responses."
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "max_tokens": {
                "type": "integer",
                "description": "Maximum tokens to return (approximate, default 4000)",
                "default": 4000,
            },
        },
        "required": ["url"],
    }

    async def run(self, **kwargs: Any) -> ToolResult:
        url = kwargs.get("url", "")
        if not url:
            return ToolResult(success=False, error="No url provided")
        max_tokens = int(kwargs.get("max_tokens", 4000))

        try:
            import httpx

            client = httpx.AsyncClient(timeout=30, follow_redirects=True)
            try:
                resp = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; AIOS-CLI/1.0)",
                        "Accept": "text/html,text/plain,*/*",
                    },
                )
                resp.raise_for_status()
                html = resp.text
            finally:
                await client.aclose()

            import html2text

            converter = html2text.HTML2Text()
            converter.body_width = 0
            converter.ignore_links = False
            converter.ignore_images = True
            converter.ignore_emphasis = False
            markdown = converter.handle(html)

            lines = [l for l in markdown.split("\n") if l.strip()]
            markdown = "\n".join(lines)

            estimated = len(markdown) // 3
            if estimated > max_tokens:
                markdown = markdown[: max_tokens * 3]
                markdown += "\n\n[... Content truncated. Use a smaller URL or specify a higher max_tokens ...]"

            return ToolResult(
                success=True,
                output=markdown,
                data={"url": url, "source": "web"},
            )
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}")
        except httpx.RequestError as e:
            return ToolResult(success=False, error=f"Request failed: {e}")
        except ImportError as e:
            return ToolResult(success=False, error=f"Missing dependency: {e}")
        except Exception as e:
            return ToolResult(success=False, error=f"Fetch failed: {e}")
