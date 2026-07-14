from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from aios.core.models import ToolResult


class Tool(ABC):
    name: str = "base_tool"
    description: str = ""
    parameters: dict[str, Any] = {}

    @abstractmethod
    async def run(self, **kwargs: Any) -> ToolResult:
        ...

    async def run_timed(self, **kwargs: Any) -> ToolResult:
        start = time.perf_counter()
        try:
            result = await self.run(**kwargs)
        except Exception as exc:
            result = ToolResult(success=False, error=str(exc))
        result.duration_ms = (time.perf_counter() - start) * 1000
        return result
