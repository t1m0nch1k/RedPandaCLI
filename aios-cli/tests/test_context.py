from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from aios.context.budget import TokenBudget
from aios.context.compactor import Compactor
from aios.context.window import ContextWindow
from aios.context.manager import ContextManager
from aios.core.models import Conversation, Message, Role


# ── ContextWindow ─────────────────────────────────────────────────────

class TestContextWindow:
    def test_estimate_tokens(self):
        w = ContextWindow("test-model")
        t = w.estimate_tokens("hello world")
        assert t > 0

    def test_estimate_tokens_empty(self):
        w = ContextWindow("test-model")
        assert w.estimate_tokens("") == 0

    def test_total_tokens(self):
        w = ContextWindow("test-model")
        msgs = [
            Message(role=Role.USER, content="hi"),
            Message(role=Role.ASSISTANT, content="hello there"),
        ]
        t = w.total_tokens(msgs)
        assert t > 0

    def test_total_tokens_empty(self):
        w = ContextWindow("test-model")
        assert w.total_tokens([]) == 0


# ── TokenBudget ──────────────────────────────────────────────────────

class TestTokenBudget:
    def test_defaults(self):
        b = TokenBudget()
        assert b.limit == 128000
        assert b.current_usage == 0

    def test_custom_limit(self):
        b = TokenBudget(limit=4096)
        assert b.limit == 4096

    def test_add_tokens(self):
        b = TokenBudget()
        b.add_tokens(100)
        assert b.current_usage == 100

    def test_subtract_tokens(self):
        b = TokenBudget()
        b.add_tokens(200)
        b.subtract_tokens(50)
        assert b.current_usage == 150

    def test_usage_percentage(self):
        b = TokenBudget(limit=1000)
        b.add_tokens(250)
        assert b.usage_percentage == 25.0

    def test_is_over_budget(self):
        b = TokenBudget(limit=100)
        b.add_tokens(50)
        assert not b.is_over_budget()
        b.add_tokens(60)
        assert b.is_over_budget()


# ── Compactor ────────────────────────────────────────────────────────

class TestCompactor:
    def test_truncate_tool_result_short(self):
        c = Compactor(ContextWindow("test"))
        text = "short text"
        result, truncated = c.truncate_tool_result(text, max_tokens=1000)
        assert result == text
        assert truncated is False

    def test_truncate_tool_result_long(self):
        c = Compactor(ContextWindow("test"))
        text = "x" * 10_000
        result, truncated = c.truncate_tool_result(text, max_tokens=100)
        assert truncated is True
        assert "truncated" in result.lower()


# ── ContextManager ───────────────────────────────────────────────────

class TestContextManager:
    def test_init(self):
        cm = ContextManager("test-model")
        assert cm.window is not None
        assert cm.budget is not None
        assert cm.compactor is not None

    def test_update_usage(self):
        cm = ContextManager("test-model", token_limit=10000)
        msgs = [Message(role=Role.USER, content="hello")]
        cm.update_usage(msgs)
        assert cm.budget.current_usage > 0

    def test_manage_below_threshold(self):
        cm = ContextManager("test-model", token_limit=1000000)
        conv = Conversation(provider="test", model="test")
        conv.add(Role.USER, "hi")

        import asyncio
        provider = AsyncMock()
        asyncio.run(cm.manage(conv, provider))
        assert cm.budget.usage_percentage < 80
        # Should not have compacted
        assert len(conv.messages) == 1

    def test_summarize_replaces_half(self):
        cm = ContextManager("test-model", token_limit=200)

        conv = Conversation(provider="test", model="test")
        for i in range(20):
            conv.add(Role.USER, "this is a fairly long message that uses tokens " * 5)

        provider = AsyncMock()
        provider.complete.return_value = "Mock summary of the conversation history preserving key facts"

        import asyncio
        asyncio.run(cm.manage(conv, provider))

        # After compaction, messages should be fewer and start with summary
        first = conv.messages[0]
        assert "Mock summary" in first.content
