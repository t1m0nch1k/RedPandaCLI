from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[None]] | Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event: str, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Handler) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    async def emit(self, event: str, payload: Any = None) -> None:
        for handler in self._handlers.get(event, []):
            result = handler(payload)
            if asyncio.iscoroutine(result):
                await result


bus = EventBus()
