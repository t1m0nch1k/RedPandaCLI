from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
import httpx

from aios.core.models import Message, Role, StreamChunk
from aios.providers.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _payload(self, messages: list[Message], temperature: float) -> dict:
        msgs_payload = []
        for m in messages:
            msg_dict = {"role": m.role.value, "content": m.content}
            if m.role == Role.ASSISTANT and m.metadata.get("tool_calls"):
                msg_dict["tool_calls"] = m.metadata["tool_calls"]
            if m.role == Role.TOOL:
                msg_dict["tool_call_id"] = m.metadata.get("tool_call_id", m.metadata.get("name", "unknown"))
                if "name" in m.metadata:
                    msg_dict["name"] = m.metadata["name"]
            msgs_payload.append(msg_dict)
            
        return {
            "model": self.model,
            "messages": msgs_payload,
            "temperature": temperature,
            "max_tokens": 8192,
        }

    async def stream(
        self, messages: list[Message], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature)
        payload["stream"] = True
        client = await self.get_client()
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
        ) as resp:
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                import logging
                logging.getLogger(__name__).error(f"HTTP stream error: {e.response.status_code} - {await resp.aread()}")
                raise
                
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content")
                if delta:
                    yield delta

    async def _make_request_with_retry(self, client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
        import asyncio
        import httpx
        
        max_retries = 10
        base_delay = 2.0
        for attempt in range(max_retries):
            resp = await client.request(method, url, **kwargs)
            try:
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503, 500, 502, 504) and attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), 30.0)
                    print(f"Retrying after {delay}s due to HTTP {e.response.status_code}...")
                    await asyncio.sleep(delay)
                    continue
                raise

    async def complete(
        self, messages: list[Message], temperature: float = 0.2
    ) -> str:
        payload = self._payload(messages, temperature)
        client = await self.get_client()
        resp = await self._make_request_with_retry(
            client,
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def list_models(self) -> list[str]:
        client = await self.get_client()
        resp = await self._make_request_with_retry(
            client,
            "GET",
            f"{self.base_url}/models",
            headers=self._headers(),
        )
        data = resp.json()
        return [m["id"] for m in data.get("data", [])]

    async def chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        payload = self._payload(messages, temperature)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        client = await self.get_client()
        resp = await self._make_request_with_retry(
            client,
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
        )
        return resp.json()["choices"][0]["message"]

    async def stream_chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> AsyncIterator[StreamChunk]:
        payload = self._payload(messages, temperature)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": False}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        client = await self.get_client()
        tool_call_accums: dict[int, dict[str, str]] = {}
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
        ) as resp:
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                import logging
                logging.getLogger(__name__).error(f"HTTP stream error: {e.response.status_code} - {await resp.aread()}")
                raise
                
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break

                chunk = json.loads(data)
                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                content = delta.get("content")
                if content:
                    yield StreamChunk(type="content", content=content)

                tcd = delta.get("tool_calls")
                if tcd:
                    for tc in tcd:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_accums:
                            tool_call_accums[idx] = {"id": "", "name": "", "arguments": ""}
                        if "id" in tc:
                            tool_call_accums[idx]["id"] = tc["id"]
                        func = tc.get("function", {})
                        if "name" in func:
                            tool_call_accums[idx]["name"] += func["name"]
                        if "arguments" in func:
                            tool_call_accums[idx]["arguments"] += func["arguments"]

                # We accumulate tools and yield them when the stream ends.
                # Some providers don't reliably set finish_reason="tool_calls", so we check at the end.
                pass

        if tool_call_accums:
            result = []
            for idx in sorted(tool_call_accums.keys()):
                acc = tool_call_accums[idx]
                result.append({
                    "id": acc["id"] or f"call_{idx}",
                    "type": "function",
                    "function": {
                        "name": acc["name"],
                        "arguments": acc["arguments"],
                    },
                })
            yield StreamChunk(type="tool_call", tool_calls=result)
            tool_call_accums.clear()

        yield StreamChunk(type="done")
