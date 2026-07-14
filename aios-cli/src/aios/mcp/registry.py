from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from aios.mcp.adapter import MCPToolAdapter
from aios.mcp.client import MCPClient, create_transport
from aios.tools.base import Tool
from aios.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).parent / "catalog.json"


class MCPRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}
        self._server_configs: dict[str, dict[str, Any]] = {}

    @property
    def connected_servers(self) -> list[str]:
        return list(self._clients.keys())

    def configure(self, servers: list[dict[str, Any]]) -> None:
        for cfg in servers:
            name = cfg.get("name", "")
            if not name:
                continue
            self._server_configs[name] = cfg

    async def connect(self, name: str) -> list[Tool]:
        cfg = self._server_configs.get(name)
        if not cfg:
            raise ValueError(f"MCP server '{name}' not configured")

        transport = create_transport(cfg)
        client = MCPClient(name, transport)
        await transport.connect()

        try:
            tools_defs = await client.list_tools()
        except Exception:
            await transport.close()
            raise

        self._clients[name] = client
        tools = [MCPToolAdapter(client, t) for t in tools_defs]
        logger.info(f"MCP '{name}': {len(tools)} tool(s) registered")
        return tools

    async def connect_all(self) -> list[Tool]:
        all_tools: list[Tool] = []
        for name in list(self._server_configs.keys()):
            if name in self._clients:
                continue
            try:
                tools = await self.connect(name)
                all_tools.extend(tools)
            except Exception as e:
                logger.warning(f"MCP '{name}': failed to connect: {e}")
        return all_tools

    async def disconnect(self, name: str) -> None:
        client = self._clients.pop(name, None)
        if client:
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"MCP '{name}': shutdown error: {e}")

    async def disconnect_all(self) -> None:
        for name in list(self._clients.keys()):
            await self.disconnect(name)

    async def register_with_registry(self, tool_registry: ToolRegistry) -> None:
        tools = await self.connect_all()
        for tool in tools:
            tool_registry.register(tool)

    @staticmethod
    def list_catalog_servers() -> list[dict[str, Any]]:
        if not CATALOG_PATH.exists():
            return []
        try:
            with open(CATALOG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("servers", [])
        except (json.JSONDecodeError, OSError):
            return []
