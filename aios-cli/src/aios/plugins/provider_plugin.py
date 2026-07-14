from __future__ import annotations

from abc import abstractmethod
from typing import Any

from aios.plugins.base import Plugin
from aios.providers.base import LLMProvider


class ProviderPlugin(Plugin):
    @abstractmethod
    def get_provider_class(self) -> type[LLMProvider]:
        ...

    async def on_load(self) -> None:
        from aios.providers.registry import register_provider

        cls = self.get_provider_class()
        register_provider(self.metadata.name, cls)

    def get_tools(self) -> list[Any]:
        return []

    def get_hooks(self) -> list[Any]:
        return []
