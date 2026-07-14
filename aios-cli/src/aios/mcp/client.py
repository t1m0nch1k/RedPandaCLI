from __future__ import annotations

import logging
from typing import Any

from aios.mcp.transport import MCPTransport, SSETransport, StdioTransport

logger = logging.getLogger(__name__)


class MCPClient:
    def __init__(self, server_name: str, transport: MCPTransport) -> None:
        self.server_name = server_name
        self.transport = transport
        self._request_id = 0
        self._initialized = False
        self._server_info: dict[str, Any] = {}
        self._server_capabilities: dict[str, Any] = {}

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        msg = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params:
            msg["params"] = params

        await self.transport.send(msg)

        while True:
            resp = await self.transport.receive()
            if resp is None:
                raise ConnectionError(f"MCP server '{self.server_name}' closed connection")

            if "id" in resp and resp.get("id") == msg["id"]:
                if "error" in resp:
                    err = resp["error"]
                    raise RuntimeError(f"MCP error {err.get('code')}: {err.get('message')}")
                return resp.get("result", {})
            elif "id" not in resp and "method" in resp:
                logger.debug(f"MCP notification from '{self.server_name}': {resp.get('method')}")

    async def initialize(self) -> None:
        result = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "aios-cli",
                "version": "0.1.0",
            },
        })
        self._server_info = result.get("serverInfo", {})
        self._server_capabilities = result.get("capabilities", {})
        self._initialized = True
        await self.transport.send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        logger.info(
            f"MCP server '{self.server_name}' initialized: "
            f"{self._server_info.get('name', '?')} v{self._server_info.get('version', '?')}"
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        result = await self._request("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        result = await self._request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return result

    async def close(self) -> None:
        if self._initialized:
            try:
                await self._request("shutdown")
            except Exception:
                pass
        await self.transport.close()
        self._initialized = False


def create_transport(config: dict[str, Any]) -> MCPTransport:
    transport_type = config.get("transport", "stdio")
    if transport_type == "sse":
        url = config.get("url", "")
        if not url:
            raise ValueError("SSE transport requires 'url' in config")
        return SSETransport(url)
    return StdioTransport(
        command=config.get("command", ""),
        args=config.get("args", []),
        env=config.get("env"),
    )
