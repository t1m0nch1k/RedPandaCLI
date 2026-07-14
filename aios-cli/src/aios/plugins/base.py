from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Any

from aios.hooks.events import HookEvent
from aios.hooks.manager import HookCallable
from aios.tools.base import Tool


@dataclass
class PluginMetadata:
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    dependencies: list[str] = field(default_factory=list)
    min_aios_version: str = "0.1.0"


class Plugin(ABC):
    metadata: PluginMetadata = PluginMetadata()

    def __init__(self) -> None:
        self._enabled: bool = True
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_config(self, config: dict[str, Any]) -> None:
        self._config = config

    def get_config(self) -> dict[str, Any]:
        return self._config

    def get_config_schema(self) -> dict[str, Any] | None:
        return None

    async def on_load(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    def get_tools(self) -> list[Tool]:
        return []

    def get_hooks(self) -> list[tuple[HookEvent, HookCallable]]:
        return []

    def get_cli_commands(self) -> list[dict[str, Any]]:
        return []
