from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import httpx

from aios.core.models import Message, StreamChunk


class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, base_url: str, api_key: str = "", model: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def stream(
        self, messages: list[Message], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def complete(
        self, messages: list[Message], temperature: float = 0.2
    ) -> str:
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        ...

    async def has_model(self, model: str) -> bool:
        try:
            models = await self.list_models()
            return any(candidate == model or candidate.startswith(f"{model}:") for candidate in models)
        except Exception:
            return False

    async def health_check(self) -> bool:
        try:
            await self.list_models()
            return True
        except Exception:
            return False

    @abstractmethod
    async def chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    async def stream_chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> AsyncIterator[StreamChunk]:
        ...
