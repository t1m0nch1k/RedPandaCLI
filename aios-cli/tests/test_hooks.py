from __future__ import annotations

from pathlib import Path

import pytest

from aios.hooks.events import HookEvent, HookContext, HookAction
from aios.hooks.manager import HookManager
from aios.hooks.git_hooks import make_auto_commit_hook
from aios.config.settings import GitConfig
from aios.core.models import Conversation, Role, ToolResult


# ── HookEvent enum ────────────────────────────────────────────────────

class TestHookEvent:
    def test_all_events_defined(self):
        expected = {
            HookEvent.PRE_TOOL,
            HookEvent.POST_TOOL,
            HookEvent.PRE_PROMPT,
            HookEvent.POST_RESPONSE,
            HookEvent.SESSION_START,
            HookEvent.SESSION_END,
            HookEvent.ERROR,
        }
        assert set(HookEvent) == expected


# ── HookContext ───────────────────────────────────────────────────────

class TestHookContext:
    def test_defaults(self):
        ctx = HookContext(event=HookEvent.PRE_TOOL, conversation="mock")
        assert ctx.event == HookEvent.PRE_TOOL
        assert ctx.tool_name is None
        assert ctx.tool_args is None
        assert ctx.tool_result is None
        assert ctx.error is None
        assert ctx.metadata == {}


# ── HookManager ───────────────────────────────────────────────────────

class TestHookManager:
    def test_register_and_trigger(self):
        mgr = HookManager()
        results = []

        async def my_hook(ctx: HookContext) -> HookAction:
            results.append(ctx.event)
            return HookAction.CONTINUE

        mgr.register(HookEvent.PRE_TOOL, my_hook)
        ctx = HookContext(event=HookEvent.PRE_TOOL, conversation="mock")
        action = mgr.trigger(HookEvent.PRE_TOOL, ctx)
        import asyncio
        result = asyncio.run(action)
        assert result == HookAction.CONTINUE
        assert results == [HookEvent.PRE_TOOL]

    def test_block_stops_execution(self):
        mgr = HookManager()

        async def blocker(ctx: HookContext) -> HookAction:
            return HookAction.BLOCK

        async def after(ctx: HookContext) -> HookAction:
            pytest.fail("Should not be called")

        mgr.register(HookEvent.PRE_TOOL, blocker)
        mgr.register(HookEvent.PRE_TOOL, after)

        ctx = HookContext(event=HookEvent.PRE_TOOL, conversation="mock")
        import asyncio
        result = asyncio.run(mgr.trigger(HookEvent.PRE_TOOL, ctx))
        assert result == HookAction.BLOCK

    def test_multiple_hooks_all_continue(self):
        mgr = HookManager()
        calls = []

        async def hook1(ctx):
            calls.append("h1")
            return HookAction.CONTINUE

        async def hook2(ctx):
            calls.append("h2")
            return HookAction.CONTINUE

        mgr.register(HookEvent.POST_TOOL, hook1)
        mgr.register(HookEvent.POST_TOOL, hook2)

        import asyncio
        result = asyncio.run(mgr.trigger(HookEvent.POST_TOOL, HookContext(event=HookEvent.POST_TOOL, conversation="mock")))
        assert result == HookAction.CONTINUE
        assert calls == ["h1", "h2"]

    def test_hook_exception_does_not_crash(self):
        mgr = HookManager()

        async def broken(ctx):
            raise ValueError("boom")

        async def good(ctx):
            return HookAction.CONTINUE

        mgr.register(HookEvent.PRE_TOOL, broken)
        mgr.register(HookEvent.PRE_TOOL, good)

        import asyncio
        result = asyncio.run(mgr.trigger(HookEvent.PRE_TOOL, HookContext(event=HookEvent.PRE_TOOL, conversation="mock")))
        assert result == HookAction.CONTINUE

    def test_trigger_wrong_event_no_crash(self):
        mgr = HookManager()

        async def hook(ctx):
            return HookAction.CONTINUE

        mgr.register(HookEvent.PRE_PROMPT, hook)

        import asyncio
        result = asyncio.run(mgr.trigger(HookEvent.POST_TOOL, HookContext(event=HookEvent.POST_TOOL, conversation="mock")))
        assert result == HookAction.CONTINUE

    def test_register_multiple_same_event(self):
        mgr = HookManager()
        for _ in range(5):
            mgr.register(HookEvent.PRE_TOOL, lambda ctx: HookAction.CONTINUE)
        assert len(mgr._hooks[HookEvent.PRE_TOOL]) == 5


# ── Git Hooks ────────────────────────────────────────────────────────

class TestGitHooks:
    def test_auto_commit_skipped_if_not_filesystem(self):
        hook = make_auto_commit_hook(GitConfig(auto_commit=True), Path.cwd())
        ctx = HookContext(
            event=HookEvent.POST_TOOL,
            conversation="mock",
            tool_name="shell",
            tool_result=ToolResult(success=True, output="done"),
        )
        import asyncio
        result = asyncio.run(hook(ctx))
        assert result == HookAction.CONTINUE

    def test_auto_commit_skipped_if_disabled(self):
        hook = make_auto_commit_hook(GitConfig(auto_commit=False), Path.cwd())
        ctx = HookContext(
            event=HookEvent.POST_TOOL,
            conversation="mock",
            tool_name="filesystem",
            tool_result=ToolResult(success=True, output="done"),
        )
        import asyncio
        result = asyncio.run(hook(ctx))
        assert result == HookAction.CONTINUE

    def test_auto_commit_skipped_on_failure(self):
        hook = make_auto_commit_hook(GitConfig(auto_commit=True), Path.cwd())
        ctx = HookContext(
            event=HookEvent.POST_TOOL,
            conversation="mock",
            tool_name="filesystem",
            tool_result=ToolResult(success=False, error="fail"),
        )
        import asyncio
        result = asyncio.run(hook(ctx))
        assert result == HookAction.CONTINUE

    def test_auto_commit_skipped_without_tool_result(self):
        hook = make_auto_commit_hook(GitConfig(auto_commit=True), Path.cwd())
        ctx = HookContext(event=HookEvent.POST_TOOL, conversation="mock", tool_name="filesystem")
        import asyncio
        result = asyncio.run(hook(ctx))
        assert result == HookAction.CONTINUE
