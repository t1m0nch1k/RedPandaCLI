from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from aios.runtime.event_bus.base import EventBusProtocol
from aios.runtime.models import Event, EventHandler

logger = logging.getLogger(__name__)


class EventBus(EventBusProtocol):
    """
    In-memory typed pub/sub for runtime-internal communication.

    Events are dispatched synchronously within the event loop.
    Subscriber errors are logged but never propagated — the emit()
    caller is never affected by a misbehaving subscriber.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._all_handlers: list[EventHandler] = []
        self._lock = asyncio.Lock()

    async def emit(self, event: Event) -> None:
        async with self._lock:
            handlers = list(self._handlers.get(type(event), []))
            all_handlers = list(self._all_handlers)

        for handler in handlers:
            try:
                result = handler(event)
                if isinstance(result, Awaitable):
                    await result
            except Exception:
                logger.exception("Event handler failed for %s", type(event).__name__)

        for handler in all_handlers:
            try:
                result = handler(event)
                if isinstance(result, Awaitable):
                    await result
            except Exception:
                logger.exception("Global event handler failed for %s", type(event).__name__)

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> Callable[[], None]:
        self._handlers[event_type].append(handler)

        def unregister() -> None:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

        return unregister

    def subscribe_all(
        self,
        handler: EventHandler,
    ) -> Callable[[], None]:
        self._all_handlers.append(handler)

        def unregister() -> None:
            if handler in self._all_handlers:
                self._all_handlers.remove(handler)

        return unregister
