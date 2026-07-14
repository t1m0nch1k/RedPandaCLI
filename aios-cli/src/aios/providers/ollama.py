from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from aios.core.models import Message, Role, StreamChunk
from aios.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def _payload(self, messages: list[Message], temperature: float) -> dict:
        msgs_payload = []
        for m in messages:
            msg_dict = {"role": m.role.value, "content": m.content}
            if m.role == Role.ASSISTANT and m.metadata.get("tool_calls"):
                msg_dict["tool_calls"] = m.metadata["tool_calls"]
            if m.role == Role.TOOL:
                # Ollama tool responses require the name of the tool, and sometimes tool_call_id
                if "name" in m.metadata:
                    msg_dict["name"] = m.metadata["name"]
                if "tool_call_id" in m.metadata:
                    msg_dict["tool_call_id"] = m.metadata["tool_call_id"]
            msgs_payload.append(msg_dict)
            
        return {
            "model": self.model,
            "messages": msgs_payload,
            "options": {
                "temperature": temperature,
                "num_predict": -1,
                "num_ctx": 32768,
            },
        }

    async def stream(
        self, messages: list[Message], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature)
        payload["stream"] = True
        client = await self.get_client()
        async with client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as resp:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
                if chunk.get("done"):
                    break

    async def complete(
        self, messages: list[Message], temperature: float = 0.2
    ) -> str:
        payload = self._payload(messages, temperature)
        payload["stream"] = False
        client = await self.get_client()
        resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    async def list_models(self) -> list[str]:
        client = await self.get_client()
        resp = await client.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        payload = self._payload(messages, temperature)
        if tools:
            payload["tools"] = tools

        client = await self.get_client()
        resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {})

    async def stream_chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> AsyncIterator[StreamChunk]:
        payload = self._payload(messages, temperature)
        payload["stream"] = True
        if tools:
            payload["tools"] = tools

        client = await self.get_client()
        async with client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                content = msg.get("content", "")
                if content:
                    yield StreamChunk(type="content", content=content)
                if chunk.get("done"):
                    tool_calls = msg.get("tool_calls")
                    if tool_calls:
                        result = []
                        for tc in tool_calls:
                            result.append({
                                "id": tc.get("id", f"call_{len(result)}"),
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": json.dumps(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], dict) else tc["function"]["arguments"],
                                },
                            })
                        yield StreamChunk(type="tool_call", tool_calls=result)
                    yield StreamChunk(type="done")
                    break
