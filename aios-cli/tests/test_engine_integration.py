from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from aios.config.settings import GitConfig
from aios.core.models import Conversation, Role, StreamChunk, ToolResult
from aios.executor.engine import ExecutionEngine
from aios.permissions.base import PermissionDecision
from aios.permissions.manager import PermissionManager
from aios.permissions.policy import PermissionPolicy
from aios.permissions.rules import PermissionRule
from aios.providers.base import LLMProvider
from aios.tools.base import Tool
from aios.tools.registry import ToolRegistry
from aios.workspace import WorkspaceContext


class EchoTool(Tool):
    name = "echo"
    description = "Echoes back whatever is passed"
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def run(self, text: str = "") -> ToolResult:
        return ToolResult(success=True, output=f"echoed: {text}")


class ErrorTool(Tool):
    name = "error-tool"
    description = "Always fails"
    parameters = {
        "type": "object",
        "properties": {"msg": {"type": "string"}},
        "required": ["msg"],
    }

    async def run(self, msg: str = "") -> ToolResult:
        return ToolResult(success=False, error=f"failed: {msg}")


class SumTool(Tool):
    name = "sum"
    description = "Sum two numbers"
    parameters = {
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    }

    async def run(self, a: int = 0, b: int = 0) -> ToolResult:
        return ToolResult(success=True, output=str(a + b))


class MockProvider(LLMProvider):
    def __init__(self, responses: list):
        super().__init__(base_url="http://mock", api_key="", model="mock-model")
        self.responses = responses
        self.current = 0
        self.last_messages = []

    async def chat(self, messages, tools=None, **kwargs):
        self.last_messages = messages
        if self.current < len(self.responses):
            r = self.responses[self.current]
            self.current += 1
            return r
        return {"content": "done", "tool_calls": []}

    async def complete(self, prompt, **kwargs):
        return "mock"

    async def list_models(self):
        return ["mock-model"]

    async def stream(self, messages, **kwargs):
        yield "mock"

    async def health_check(self):
        return True

    async def has_model(self, model):
        return True

    async def stream_chat(self, messages, temperature=0.2, tools=None) -> AsyncIterator[StreamChunk]:
        resp = await self.chat(messages, temperature=temperature, tools=tools)
        content = resp.get("content")
        if content:
            yield StreamChunk(type="content", content=content)
        tcs = resp.get("tool_calls")
        if tcs:
            yield StreamChunk(type="tool_call", tool_calls=tcs)
        yield StreamChunk(type="done")


def _allow_all_policy():
    class AllowAll(PermissionRule):
        def matches(self, *args):
            return True
    return PermissionPolicy(name="allow-all", rules=[AllowAll(tool="any", decision=PermissionDecision.ALLOW)])


def _yes_confirm(name, args):
    import asyncio
    async def _inner():
        return True
    return asyncio.run(_inner())


async def _yes(name: str, args: dict) -> bool:
    return True


class TestEngineIntegration:
    @pytest.mark.asyncio
    async def test_simple_tool_call_then_finish(self, tmp_path: Path):
        provider = MockProvider([
            {
                "content": "I will use echo",
                "tool_calls": [{"id": "c1", "function": {"name": "echo", "arguments": {"text": "hi"}}}],
            },
            {"content": "Done!", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(EchoTool())
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "say hi")
        result = await engine.run(conv, max_iterations=5)
        assert "Done!" in result

    @pytest.mark.asyncio
    async def test_tool_failure_handling(self, tmp_path: Path):
        provider = MockProvider([
            {
                "content": "I will use error-tool",
                "tool_calls": [{"id": "c1", "function": {"name": "error-tool", "arguments": {"msg": "explosion"}}}],
            },
            {"content": "Recovered!", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(ErrorTool())
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "trigger error")
        result = await engine.run(conv, max_iterations=5)
        assert "Recovered!" in result

    @pytest.mark.asyncio
    async def test_max_iterations_reached(self, tmp_path: Path):
        provider = MockProvider([
            {
                "content": "loop",
                "tool_calls": [{"id": "c1", "function": {"name": "echo", "arguments": {"text": "x"}}}],
            }
            for _ in range(3)
        ] + [{"content": "should not be reached", "tool_calls": []}])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(EchoTool())
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "keep looping")
        result = await engine.run(conv, max_iterations=3)
        assert "Maximum iterations" in result

    @pytest.mark.asyncio
    async def test_permission_denial_blocks_tool(self, tmp_path: Path):
        deny_policy = PermissionPolicy(name="deny-all", rules=[
            PermissionRule(tool="echo", decision=PermissionDecision.DENY),
        ])
        provider = MockProvider([
            {
                "content": "I will use echo",
                "tool_calls": [{"id": "c1", "function": {"name": "echo", "arguments": {"text": "secret"}}}],
            },
            {"content": "Blocked!", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(EchoTool())
        pm = PermissionManager(policy=deny_policy)
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "do echo")
        result = await engine.run(conv, max_iterations=5)
        assert "Blocked!" in result
        tool_msg = [m for m in conv.messages if m.role == Role.TOOL]
        assert any("denied" in m.content for m in tool_msg)

    @pytest.mark.asyncio
    async def test_user_declines_asks_confirmation(self, tmp_path: Path):
        ask_policy = PermissionPolicy(name="ask-all", rules=[
            PermissionRule(tool="echo", decision=PermissionDecision.ASK),
        ])
        provider = MockProvider([
            {
                "content": "I will use echo",
                "tool_calls": [{"id": "c1", "function": {"name": "echo", "arguments": {"text": "confirm?"}}}],
            },
            {"content": "They declined", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(EchoTool())
        pm = PermissionManager(policy=ask_policy)
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, confirmation_callback=_yes, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "do it")
        result = await engine.run(conv, max_iterations=5)
        assert "They declined" in result

    @pytest.mark.asyncio
    async def test_streaming_callback_invoked(self, tmp_path: Path):
        provider = MockProvider([
            {"content": "Final answer", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        chunks = []

        async def on_stream(chunk: StreamChunk):
            chunks.append(chunk)

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "hi")
        result = await engine.run(conv, max_iterations=5, stream_callback=on_stream)
        assert "Final answer" in result
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_hook_blocks_execution(self, tmp_path: Path):
        from aios.hooks.events import HookAction, HookEvent

        provider = MockProvider([
            {"content": "This should be blocked", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        pm = PermissionManager(policy=_allow_all_policy())

        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        async def blocker(ctx):
            return HookAction.BLOCK

        engine.hook_manager.register(HookEvent.PRE_PROMPT, blocker)

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "hi")
        result = await engine.run(conv, max_iterations=5)
        assert "blocked" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_arguments(self, tmp_path: Path):
        class RawArgsProvider(LLMProvider):
            name = "raw-args"

            def __init__(self):
                super().__init__(base_url="http://mock", api_key="", model="mock")
                self.called = False

            async def chat(self, messages, tools=None, **kwargs):
                if not self.called:
                    self.called = True
                    return {
                        "content": "bad json",
                        "tool_calls": [{"id": "c1", "function": {"name": "echo", "arguments": "{invalid json here}"}}],
                    }
                return {"content": "recovered", "tool_calls": []}

            async def complete(self, *a, **kw): return ""
            async def list_models(self): return ["m"]
            async def stream(self, *a, **kw): yield ""
            async def health_check(self): return True
            async def has_model(self, m): return True
            async def stream_chat(self, messages, temperature=0.2, tools=None) -> AsyncIterator[StreamChunk]:
                resp = await self.chat(messages, temperature=temperature, tools=tools)
                yield StreamChunk(type="content", content=resp.get("content", ""))

        provider = RawArgsProvider()
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(EchoTool())
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "test")
        result = await engine.run(conv, max_iterations=5)
        assert "recovered" in result

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, tmp_path: Path):
        provider = MockProvider([
            {
                "content": "calling unknown",
                "tool_calls": [{"id": "c1", "function": {"name": "no-such-tool", "arguments": {"x": "y"}}}],
            },
            {"content": "handled error", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "go")
        result = await engine.run(conv, max_iterations=5)
        assert "handled error" in result
        tool_msgs = [m for m in conv.messages if m.role == Role.TOOL]
        assert any("not found" in m.content for m in tool_msgs)

    @pytest.mark.asyncio
    async def test_system_prompt_injected(self, tmp_path: Path):
        provider = MockProvider([
            {"content": "with system prompt", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(
            provider=provider, tool_registry=registry, permission_manager=pm,
            system_prompt="You are a helpful bot", git_config=GitConfig(auto_commit=False, secret_scanning=False),
        )

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "hi")
        result = await engine.run(conv, max_iterations=5)
        assert "with system prompt" in result
        sys_msgs = [m for m in provider.last_messages if m.role == Role.SYSTEM]
        assert any("helpful bot" in m.content for m in sys_msgs)

    @pytest.mark.asyncio
    async def test_conversation_history_preserved(self, tmp_path: Path):
        provider = MockProvider([
            {"content": "First response", "tool_calls": [{"id": "c1", "function": {"name": "sum", "arguments": {"a": 1, "b": 2}}}]},
            {"content": "Second response", "tool_calls": []},
        ])
        registry = ToolRegistry(WorkspaceContext(tmp_path))
        registry.register(SumTool())
        pm = PermissionManager(policy=_allow_all_policy())
        engine = ExecutionEngine(provider=provider, tool_registry=registry, permission_manager=pm, git_config=GitConfig(auto_commit=False, secret_scanning=False))

        conv = Conversation(provider="mock", model="mock")
        conv.add(Role.USER, "compute")
        result = await engine.run(conv, max_iterations=5)
        assert "Second response" in result
        assert any("3" in m.content for m in conv.messages if m.role == Role.TOOL)
