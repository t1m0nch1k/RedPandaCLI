from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
from aios.core.models import Message, Role
from aios.providers.gemini import GeminiProvider, _extract_function_calls, _to_gemini_tools, _tool_result_parts


class TestToolResultParts:
    def test_parse_tool_result(self):
        parts = _tool_result_parts("Tool echo result: hello world")
        assert len(parts) == 1
        assert parts[0]["functionResponse"]["name"] == "echo"
        assert parts[0]["functionResponse"]["response"]["response"] == "hello world"

    def test_parse_unknown_format(self):
        parts = _tool_result_parts("unstructured text")
        assert len(parts) == 1
        assert parts[0]["functionResponse"]["name"] == "unknown"


class TestToGeminiTools:
    def test_converts_openai_tools_to_gemini(self):
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name"},
                        },
                        "required": ["city"],
                    },
                },
            }
        ]
        result = _to_gemini_tools(openai_tools)
        fds = result["functionDeclarations"]
        assert len(fds) == 1
        assert fds[0]["name"] == "get_weather"
        assert fds[0]["parameters"]["type"] == "OBJECT"
        assert fds[0]["parameters"]["properties"]["city"]["type"] == "STRING"


class TestExtractFunctionCalls:
    def test_extracts_function_call(self):
        parts = [{"functionCall": {"name": "get_weather", "args": {"city": "Tokyo"}}}]
        tcs = _extract_function_calls(parts)
        assert tcs is not None
        assert len(tcs) == 1
        assert tcs[0]["function"]["name"] == "get_weather"
        assert json.loads(tcs[0]["function"]["arguments"]) == {"city": "Tokyo"}

    def test_empty_parts(self):
        assert _extract_function_calls([]) is None

    def test_text_only_parts(self):
        parts = [{"text": "hello"}]
        assert _extract_function_calls(parts) is None


class TestGeminiProvider:
    def test_init(self):
        p = GeminiProvider(base_url="", model="gemini-2.0-flash", api_key="test-key")
        assert p.model == "gemini-2.0-flash"
        assert p.api_key == "test-key"

    def test_headers(self):
        p = GeminiProvider(base_url="", model="test", api_key="abc")
        headers = p._headers()
        assert headers["x-goog-api-key"] == "abc"
        assert headers["Content-Type"] == "application/json"

    def test_to_contents_with_system(self):
        p = GeminiProvider(base_url="", model="test", api_key="k")
        msgs = [
            Message(role=Role.SYSTEM, content="You are a bot"),
            Message(role=Role.USER, content="hi"),
            Message(role=Role.ASSISTANT, content="hello there"),
        ]
        system, contents = p._to_contents(msgs)
        assert system == "You are a bot"
        assert len(contents) == 2
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "hi"
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["text"] == "hello there"

    def test_to_contents_with_tool_result(self):
        p = GeminiProvider(base_url="", model="test", api_key="k")
        msgs = [
            Message(role=Role.USER, content="weather?"),
            Message(role=Role.ASSISTANT, content="checking..."),
            Message(role=Role.TOOL, content="Tool get_weather result: Sunny"),
        ]
        system, contents = p._to_contents(msgs)
        assert len(contents) == 3
        assert contents[2]["role"] == "function"
        assert contents[2]["parts"][0]["functionResponse"]["name"] == "get_weather"

    def test_payload_with_tools(self):
        p = GeminiProvider(base_url="", model="gemini-2.0-flash", api_key="k")
        msgs = [Message(role=Role.USER, content="hi")]
        body = p._payload(msgs, 0.5, tools=[{"function": {"name": "test", "description": "Test tool"}}])
        assert "tools" in body
        assert body["generationConfig"]["temperature"] == 0.5
        assert body["contents"][0]["parts"][0]["text"] == "hi"

    def test_list_models_parses(self):
        p = GeminiProvider(base_url="", model="test", api_key="k")
        mock_get_resp = AsyncMock(spec=httpx.Response)
        mock_get_resp.json.return_value = {
            "models": [
                {"name": "models/gemini-2.0-flash"},
                {"name": "models/gemini-2.5-pro"},
            ]
        }
        mock_get_resp.raise_for_status = lambda: None

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_get_resp)

        async def mock_get_client():
            return mock_client

        import asyncio
        with patch.object(p, "get_client", mock_get_client):
            models = asyncio.run(p.list_models())
            assert "gemini-2.0-flash" in models
            assert "gemini-2.5-pro" in models

    def test_chat_parses_text(self):
        p = GeminiProvider(base_url="", model="test", api_key="k")

        async def mock_post(path, body):
            return {"candidates": [{"content": {"parts": [{"text": "Hello!"}]}}]}

        p._post = mock_post
        import asyncio
        msgs = [Message(role=Role.USER, content="hi")]
        result = asyncio.run(p.chat(msgs))
        assert result["content"] == "Hello!"
        assert result["tool_calls"] is None

    def test_chat_parses_function_call(self):
        p = GeminiProvider(base_url="", model="test", api_key="k")

        async def mock_post(path, body):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"functionCall": {"name": "get_weather", "args": {"city": "Tokyo"}}}]
                    }
                }]
            }

        p._post = mock_post
        import asyncio
        msgs = [Message(role=Role.USER, content="weather in Tokyo")]
        result = asyncio.run(p.chat(msgs))
        assert result["content"] is None
        assert result["tool_calls"] is not None
        assert result["tool_calls"][0]["function"]["name"] == "get_weather"
