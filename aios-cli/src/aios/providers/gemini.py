from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from aios.core.models import Message, Role, StreamChunk
from aios.providers.base import LLMProvider

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _to_contents(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        system = None
        contents = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                system = msg.content
                continue
            if msg.role == Role.TOOL:
                parts = _tool_result_parts(msg.content)
                if parts:
                    if getattr(msg, "images", None):
                        for img in msg.images:
                            parts.append({"inlineData": {"mimeType": "image/png", "data": img}})
                    contents.append({
                        "role": "function",
                        "parts": parts
                    })
                else:
                    name = msg.metadata.get("name", "unknown")
                    fallback_parts = [{"functionResponse": {"name": name, "response": {"response": msg.content}}}]
                    if getattr(msg, "images", None):
                        for img in msg.images:
                            fallback_parts.append({"inlineData": {"mimeType": "image/png", "data": img}})
                    contents.append({
                        "role": "function",
                        "parts": fallback_parts
                    })
                continue
            gemini_role = "model" if msg.role == Role.ASSISTANT else "user"
            
            parts = []
            if msg.content:
                parts.append({"text": msg.content})
                
            if getattr(msg, "images", None):
                for img in msg.images:
                    parts.append({"inlineData": {"mimeType": "image/png", "data": img}})
                
            if msg.role == Role.ASSISTANT and msg.metadata.get("tool_calls"):
                for tc in msg.metadata["tool_calls"]:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        import json
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    parts.append({
                        "functionCall": {
                            "name": tc["function"]["name"],
                            "args": args
                        }
                    })
                    
            if not parts:
                parts.append({"text": ""})
                
            contents.append({"role": gemini_role, "parts": parts})
        return system, contents

    def _payload(
        self, messages: list[Message], temperature: float, tools: list[dict] | None = None
    ) -> dict:
        system, contents = self._to_contents(messages)
        body: dict = {"contents": contents, "generationConfig": {"temperature": temperature}}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            body["tools"] = [_to_gemini_tools(tools)]
        return body

    async def _post(self, path: str, body: dict) -> dict:
        client = await self.get_client()
        resp = await client.post(f"{GEMINI_BASE}/{path}", json=body, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def _stream(self, path: str, body: dict) -> AsyncIterator[dict]:
        client = await self.get_client()
        async with client.stream(
            "POST", f"{GEMINI_BASE}/{path}", json=body, headers=self._headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                yield json.loads(data)

    async def stream(self, messages: list[Message], temperature: float = 0.2) -> AsyncIterator[str]:
        body = self._payload(messages, temperature)
        async for chunk in self._stream(f"models/{self.model}:streamGenerateContent?alt=sse", body):
            for c in chunk.get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    if "text" in p:
                        yield p["text"]

    async def complete(self, messages: list[Message], temperature: float = 0.2) -> str:
        body = self._payload(messages, temperature)
        data = await self._post(f"models/{self.model}:generateContent", body)
        parts = _candidate_parts(data)
        return "".join(p.get("text", "") for p in parts)

    async def list_models(self) -> list[str]:
        client = await self.get_client()
        resp = await client.get(f"{GEMINI_BASE}/models", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return [m["name"].replace("models/", "", 1) for m in data.get("models", [])]

    async def chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> dict[str, Any]:
        body = self._payload(messages, temperature, tools)
        data = await self._post(f"models/{self.model}:generateContent", body)
        parts = _candidate_parts(data)
        text = "".join(p.get("text", "") for p in parts)
        tcs = _extract_function_calls(parts)
        return {"content": text or None, "tool_calls": tcs or None}

    async def stream_chat(
        self, messages: list[Message], temperature: float = 0.2, tools: list[dict] | None = None
    ) -> AsyncIterator[StreamChunk]:
        body = self._payload(messages, temperature, tools)
        tool_call_list: list[dict] = []
        tool_call_idx = 0
        async for chunk in self._stream(f"models/{self.model}:streamGenerateContent?alt=sse", body):
            for c in chunk.get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    if "text" in p:
                        yield StreamChunk(type="content", content=p["text"])
                    if "functionCall" in p:
                        fc = p["functionCall"]
                        tool_call_list.append({
                            "id": f"call_{tool_call_idx}",
                            "function": {"name": fc.get("name", ""), "arguments": fc.get("args", {})},
                        })
                        tool_call_idx += 1

                # We accumulate tools and yield them when the stream ends.
                pass

        if tool_call_list:
            yield StreamChunk(
                type="tool_call",
                tool_calls=tool_call_list,
            )
            tool_call_list.clear()

        yield StreamChunk(type="done")


GEMINI_TOOL_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
}


def _to_gemini_tools(tools: list[dict]) -> dict:
    fds = []
    for t in tools:
        func = t.get("function", {})
        params = func.get("parameters", {})
        fds.append({
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "parameters": _to_gemini_schema(params),
        })
    return {"functionDeclarations": fds}


def _to_gemini_schema(schema: dict) -> dict:
    result = {"type": GEMINI_TOOL_TYPE_MAP.get(schema.get("type", "object"), "OBJECT")}
    if "description" in schema:
        result["description"] = schema["description"]
    props = schema.get("properties", {})
    if props:
        result["properties"] = {k: _to_gemini_schema(v) for k, v in props.items()}
    required = schema.get("required", [])
    if required:
        result["required"] = required
    return result


def _candidate_parts(data: dict) -> list[dict]:
    candidates = data.get("candidates", [])
    if not candidates:
        return []
    return candidates[0].get("content", {}).get("parts", [])


def _extract_function_calls(parts: list[dict]) -> list[dict] | None:
    tcs = []
    for p in parts:
        if "functionCall" in p:
            fc = p["functionCall"]
            tcs.append({
                "id": fc.get("name", "unknown"),
                "type": "function",
                "function": {
                    "name": fc.get("name", ""),
                    "arguments": json.dumps(fc.get("args", {})),
                },
            })
    return tcs or None


def _tool_result_parts(content: str) -> list[dict]:
    # Parse "Tool <name> result: <content>" format
    import re
    match = re.match(r"Tool\s+(\S+)\s+result:\s*(.*)", content)
    if match:
        name, result = match.groups()
        return [{
            "functionResponse": {
                "name": name,
                "response": {"response": result}
            }
        }]
    # Fallback for unstructured text
    return [{
        "functionResponse": {
            "name": "unknown",
            "response": {"response": content}
        }
    }]
