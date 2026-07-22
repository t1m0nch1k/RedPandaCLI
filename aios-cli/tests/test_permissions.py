from __future__ import annotations

import json
from pathlib import Path

from aios.permissions.base import PermissionDecision
from aios.permissions.manager import PermissionManager
from aios.permissions.policy import PermissionPolicy
from aios.permissions.profiles import get_strict_policy, get_trusted_policy
from aios.permissions.rules import PermissionRule

# ── PermissionDecision enum ───────────────────────────────────────────

class TestPermissionDecision:
    def test_values_distinct(self):
        assert PermissionDecision.ALLOW != PermissionDecision.DENY
        assert PermissionDecision.ALLOW != PermissionDecision.ASK
        assert PermissionDecision.DENY != PermissionDecision.ASK

    def test_always_allow_distinct(self):
        assert PermissionDecision.ALWAYS_ALLOW != PermissionDecision.ALLOW


# ── PermissionRule matching ───────────────────────────────────────────

class TestPermissionRule:
    def test_tool_match(self):
        rule = PermissionRule(tool="filesystem", decision=PermissionDecision.ALLOW)
        assert rule.matches("filesystem", {})
        assert not rule.matches("shell", {})

    def test_action_match(self):
        rule = PermissionRule(tool="filesystem", action="delete", decision=PermissionDecision.DENY)
        assert rule.matches("filesystem", {"action": "delete"})
        assert not rule.matches("filesystem", {"action": "read_file", "path": "/x"})

    def test_args_pattern_regex(self):
        rule = PermissionRule(tool="shell", args_pattern=r"rm\s+-rf\s+/", decision=PermissionDecision.DENY)
        assert rule.matches("shell", {"command": "rm -rf /"})
        assert not rule.matches("shell", {"command": "ls -la"})

    def test_fn_match_when_no_command_key(self):
        rule = PermissionRule(tool="filesystem", action="delete", decision=PermissionDecision.DENY)
        assert rule.matches("filesystem", {"action": "delete"})


# ── PermissionPolicy evaluation ───────────────────────────────────────

class TestPermissionPolicy:
    def test_first_matching_rule_wins(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="filesystem", decision=PermissionDecision.ALLOW),
            PermissionRule(tool="filesystem", action="delete", decision=PermissionDecision.DENY),
        ])
        assert policy.evaluate("filesystem", {"action": "read_file"}) == PermissionDecision.ALLOW
        assert policy.evaluate("filesystem", {"action": "delete"}) == PermissionDecision.ALLOW  # first rule matches first

    def test_fallback_to_ask(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="shell", decision=PermissionDecision.ALLOW),
        ])
        assert policy.evaluate("filesystem", {"action": "read_file"}) == PermissionDecision.ASK

    def test_empty_rules_fallback_to_ask(self):
        policy = PermissionPolicy(name="strict", rules=[])
        assert policy.evaluate("anything", {}) == PermissionDecision.ASK


# ── Profiles ─────────────────────────────────────────────────────────

class TestProfiles:
    def test_trusted_allows_read(self):
        policy = get_trusted_policy()
        assert policy.evaluate("filesystem", {"action": "read_file"}) == PermissionDecision.ALLOW
        assert policy.evaluate("filesystem", {"action": "list_files"}) == PermissionDecision.ALLOW
        assert policy.evaluate("filesystem", {"action": "search_text"}) == PermissionDecision.ALLOW

    def test_trusted_asks_modify(self):
        policy = get_trusted_policy()
        assert policy.evaluate("filesystem", {"action": "delete"}) == PermissionDecision.ASK
        assert policy.evaluate("filesystem", {"action": "replace_text"}) == PermissionDecision.ASK
        assert policy.evaluate("shell", {}) == PermissionDecision.ASK
        assert policy.evaluate("git", {}) == PermissionDecision.ASK

    def test_strict_always_asks(self):
        policy = get_strict_policy()
        assert policy.evaluate("filesystem", {"action": "read_file"}) == PermissionDecision.ASK
        assert policy.evaluate("shell", {"command": "echo hi"}) == PermissionDecision.ASK

    def test_yolo_always_allows(self):
        from aios.permissions.policy import PermissionPolicy
        class AnyRule(PermissionRule):
            def matches(self, *args):
                return True
        policy = PermissionPolicy(name="yolo", rules=[AnyRule("any", decision=PermissionDecision.ALLOW)])
        assert policy.evaluate("filesystem", {"action": "delete"}) == PermissionDecision.ALLOW
        assert policy.evaluate("shell", {"command": "rm -rf /"}) == PermissionDecision.ALLOW


# ── PermissionManager ────────────────────────────────────────────────

class TestPermissionManager:
    def test_allows_per_policy(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="filesystem", action="read_file", decision=PermissionDecision.ALLOW),
        ])
        mgr = PermissionManager(policy=policy)
        assert mgr.check("filesystem", {"action": "read_file", "path": "/x"}) == PermissionDecision.ALLOW

    def test_denies_per_policy(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="filesystem", action="delete", decision=PermissionDecision.DENY),
        ])
        mgr = PermissionManager(policy=policy)
        assert mgr.check("filesystem", {"action": "delete", "path": "/x"}) == PermissionDecision.DENY

    def test_no_match_asks(self):
        policy = PermissionPolicy(name="test", rules=[])
        mgr = PermissionManager(policy=policy)
        assert mgr.check("anything", {}) == PermissionDecision.ASK

    def test_remember_allow_caches(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="shell", decision=PermissionDecision.ASK),
        ])
        mgr = PermissionManager(policy=policy)
        assert mgr.check("shell", {"command": "ls"}) == PermissionDecision.ASK

        mgr.remember_allow("shell", {"command": "ls"})
        assert mgr.check("shell", {"command": "ls"}) == PermissionDecision.ALLOW

    def test_forget_allow_removes_cache(self):
        policy = PermissionPolicy(name="test", rules=[
            PermissionRule(tool="shell", decision=PermissionDecision.ASK),
        ])
        mgr = PermissionManager(policy=policy)
        mgr.remember_allow("shell", {"command": "ls"})
        assert mgr.check("shell", {"command": "ls"}) == PermissionDecision.ALLOW

        mgr.forget_allow("shell", {"command": "ls"})
        assert mgr.check("shell", {"command": "ls"}) == PermissionDecision.ASK

    def test_call_hash_is_consistent(self):
        policy = PermissionPolicy(name="test", rules=[])
        mgr = PermissionManager(policy=policy)
        h1 = mgr._generate_call_hash("tool", {"b": 2, "a": 1})
        h2 = mgr._generate_call_hash("tool", {"a": 1, "b": 2})
        assert h1 == h2

    def test_call_hash_differs_for_different_args(self):
        policy = PermissionPolicy(name="test", rules=[])
        mgr = PermissionManager(policy=policy)
        h1 = mgr._generate_call_hash("tool", {"path": "/a"})
        h2 = mgr._generate_call_hash("tool", {"path": "/b"})
        assert h1 != h2

    def test_load_always_allow_from_file(self, tmp_path: Path):
        from aios.permissions.manager import PERMISSIONS_FILE

        mgr_tmp = PermissionManager(policy=PermissionPolicy("test", rules=[]))
        expected_hash = mgr_tmp._generate_call_hash("shell", {"command": "ls"})
        data = [expected_hash]
        old_perms = PERMISSIONS_FILE
        test_file = tmp_path / "permissions.json"
        test_file.write_text(json.dumps(data))
        import aios.permissions.manager as pm
        pm.PERMISSIONS_FILE = test_file

        try:
            mgr = PermissionManager(policy=PermissionPolicy("test", rules=[]))
            assert expected_hash in mgr._always_allow_cache
        finally:
            pm.PERMISSIONS_FILE = old_perms
