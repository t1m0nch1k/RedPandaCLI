from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MCPTransport(ABC):
    @abstractmethod
    async def send(self, message: dict) -> None:
        ...

    @abstractmethod
    async def receive(self) -> dict | None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class StdioTransport(MCPTransport):
    def __init__(self, command: str, args: list[str], env: dict[str, str] | None = None) -> None:
        self.command = command
        self.args = args
        self.env = env
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._buffer = ""

    async def connect(self) -> None:
        full_env = None
        if self.env:
            full_env = dict(self.env)
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )
        self._reader = self._process.stdout

    async def send(self, message: dict) -> None:
        if not self._process or not self._process.stdin:
            raise RuntimeError("Transport not connected")
        line = json.dumps(message) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

    async def receive(self) -> dict | None:
        if not self._reader:
            return None
        while True:
            if "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning(f"MCP invalid JSON: {line}")
                        continue
            chunk = await self._reader.readline()
            if not chunk:
                return None
            self._buffer += chunk.decode("utf-8")

    async def close(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except (TimeoutError, ProcessLookupError):
                try:
                    self._process.kill()
                    await self._process.wait()
                except ProcessLookupError:
                    pass
            self._process = None
            self._reader = None


class SSETransport(MCPTransport):
    def __init__(self, url: str) -> None:
        self.url = url
        self._client: httpx.AsyncClient | None = None
        self._session_id: str | None = None
        self._message_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running = False

    async def connect(self) -> None:
        import httpx
        self._client = httpx.AsyncClient(timeout=30)
        self._running = True
        asyncio.create_task(self._sse_loop())

    async def _sse_loop(self) -> None:
        try:
            async with self._client.stream(
                "GET",
                self.url,
                headers={"Accept": "text/event-stream"},
            ) as resp:
                buffer = ""
                async for chunk in resp.aiter_bytes():
                    buffer += chunk.decode("utf-8")
                    while "\n\n" in buffer:
                        event_block, buffer = buffer.split("\n\n", 1)
                        self._handle_sse_event(event_block)
        except Exception as e:
            logger.error(f"MCP SSE connection error: {e}")
        finally:
            self._running = False

    def _handle_sse_event(self, block: str) -> None:
        event_type = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()

        if event_type == "endpoint" and data:
            self._session_id = data
            return

        if data:
            try:
                msg = json.loads(data)
                self._message_queue.put_nowait(msg)
            except json.JSONDecodeError:
                pass

    async def send(self, message: dict) -> None:
        if not self._client:
            raise RuntimeError("Transport not connected")
        session_url = self.url
        if self._session_id:
            session_url = self._session_id
        resp = await self._client.post(
            session_url,
            json=message,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            await self._message_queue.put(data)

    async def receive(self) -> dict | None:
        try:
            return await asyncio.wait_for(self._message_queue.get(), timeout=30)
        except TimeoutError:
            return None

    async def close(self) -> None:
        self._running = False
        if self._client:
            await self._client.aclose()
            self._client = None
