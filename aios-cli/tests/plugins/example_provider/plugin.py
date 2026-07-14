from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from aios.core.models import Message, StreamChunk
from aios.plugins.base import PluginMetadata
from aios.plugins.provider_plugin import ProviderPlugin
from aios.providers.base import LLMProvider


class EchoProvider(LLMProvider):
    name = "echo"

    async def stream(self, messages: list[Message], temperature: float = 0.2) -> AsyncIterator[str]:
        yield "echo: " + messages[-1].content

    async def complete(self, messages: list[Message], temperature: float = 0.2) -> str:
        return "echo: " + messages[-1].content

    async def list_models(self) -> list[str]:
        return ["echo-model"]

    async def chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        return {"content": "echo: " + messages[-1].content, "tool_calls": None}

    async def stream_chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(type="content", content="echo: " + messages[-1].content)


class ExampleProviderPlugin(ProviderPlugin):
    metadata = PluginMetadata(
        name="echo",
        version="0.1.0",
        description="A minimal example provider plugin that echoes back messages",
        author="AIOS Community",
    )

    def get_provider_class(self) -> type[LLMProvider]:
        return EchoProvider
