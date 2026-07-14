from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from aios.config.settings import GitConfig
from aios.core.models import ToolResult
from aios.tools.git import GitTool, _check_secrets, _run_git, PROTECTED_BRANCHES, SECRET_PATTERNS
from aios.workspace import WorkspaceContext


def _git_tool(tmp_path: Path, **overrides) -> GitTool:
    cfg = GitConfig(auto_commit=False, secret_scanning=True, **overrides)
    return GitTool(workspace=WorkspaceContext(tmp_path), git_config=cfg)


def _init_repo(path: Path) -> None:
    import asyncio
    asyncio.run(_run_git(["init"], str(path)))
    asyncio.run(_run_git(["config", "user.email", "test@test.com"], str(path)))
    asyncio.run(_run_git(["config", "user.name", "Test"], str(path)))


def _write(repo: Path, name: str, content: str = "hello") -> Path:
    f = repo / name
    f.write_text(content)
    return f


def _run_sync(coro):
    import asyncio
    return asyncio.run(coro)


# ── init ──────────────────────────────────────────────────────────────

def test_git_init(tmp_path: Path):
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="init"))
    assert r.success
    assert (tmp_path / ".git").exists()


# ── status ────────────────────────────────────────────────────────────

def test_git_status_clean(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="status"))
    assert r.success
    assert "Clean" in r.output or "On branch" in r.output


def test_git_status_untracked(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "new.txt")
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="status"))
    assert r.success
    assert "Untracked" in r.output
    assert "new.txt" in r.output


# ── add / commit ──────────────────────────────────────────────────────

def test_git_add_and_commit(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    tool = _git_tool(tmp_path)
    r1 = _run_sync(tool.run(action="add", paths=["a.txt"]))
    assert r1.success

    r2 = _run_sync(tool.run(action="commit", message="first"))
    assert r2.success
    assert "first" in r2.output


def test_git_commit_no_message(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    tool = _git_tool(tmp_path)
    _run_sync(tool.run(action="add", paths=["a.txt"]))
    r = _run_sync(tool.run(action="commit", message=""))
    assert not r.success
    assert "required" in r.error.lower()


def test_git_commit_nothing_to_commit(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="commit", message="nope"))
    assert not r.success
    assert "nothing" in r.error.lower()


def test_smart_commit_no_changes(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="smart_commit"))
    assert not r.success
    assert "nothing" in r.error.lower()


def test_smart_commits_changes(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="smart_commit", message="auto update"))
    assert r.success


# ── branch ────────────────────────────────────────────────────────────

def test_git_branch_list(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))

    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="branch", branch_action="list"))
    assert r.success
    assert "* master" in r.output or "* main" in r.output


def test_git_branch_create_and_switch(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))

    tool = _git_tool(tmp_path)
    r1 = _run_sync(tool.run(action="branch", branch_action="create", branch="feature"))
    assert r1.success

    r2 = _run_sync(tool.run(action="branch", branch_action="switch", branch="feature"))
    assert r2.success


def test_git_branch_create_requires_name(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="branch", branch_action="create", branch=""))
    assert not r.success
    assert "required" in r.error.lower()


# ── log ───────────────────────────────────────────────────────────────

def test_git_log(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))

    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="log", count=5))
    assert r.success
    assert "Recent commits" in r.output


def test_git_log_empty(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="log"))
    assert r.success
    assert "No commits" in r.output


# ── diff ──────────────────────────────────────────────────────────────

def test_git_diff_no_changes(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="diff"))
    assert r.success
    assert "No differences" in r.output


def test_git_diff_with_changes(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt", "hello")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))
    _write(tmp_path, "a.txt", "world")

    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="diff"))
    assert r.success
    assert "world" in r.output


# ── stash ─────────────────────────────────────────────────────────────

def test_git_stash_list_empty(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="stash", stash_action="list"))
    assert r.success
    assert "No stashes" in r.output


def test_git_stash_push_pop(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "init.txt")
    _run_sync(_run_git(["add", "init.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))
    _write(tmp_path, "a.txt")
    tool = _git_tool(tmp_path)
    r1 = _run_sync(tool.run(action="stash", stash_action="push", message="wip"))
    assert r1.success
    assert "wip" in r1.output or "Stashed" in r1.output

    r2 = _run_sync(tool.run(action="stash", stash_action="pop"))
    assert r2.success


# ── add wildcard ──────────────────────────────────────────────────────

def test_git_add_wildcard(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="add", paths=["*"]))
    assert r.success


def test_git_add_no_paths(tmp_path: Path):
    _init_repo(tmp_path)
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="add", paths=[]))
    assert not r.success


# ── protected branches ────────────────────────────────────────────────

def test_commit_blocked_on_protected_branch(tmp_path: Path):
    _init_repo(tmp_path)
    _write(tmp_path, "a.txt")
    _run_sync(_run_git(["add", "a.txt"], str(tmp_path)))
    _run_sync(_run_git(["commit", "-m", "init"], str(tmp_path)))

    cfg = GitConfig(protected_branches=["master", "main"])
    tool = GitTool(workspace=WorkspaceContext(tmp_path), git_config=cfg)
    r = _run_sync(tool.run(action="commit", message="bad", paths=["a.txt"]))
    assert not r.success
    assert "protected" in r.error.lower()


# ── secret scanning ───────────────────────────────────────────────────

class TestSecretScanning:
    def test_detect_api_key(self):
        found = _check_secrets("api_key = 'sk-abcdefghijklmnopqrstuvwxyz1234567890'")
        assert len(found) > 0

    def test_detect_token(self):
        found = _check_secrets("token = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        assert len(found) > 0

    def test_detect_private_key(self):
        found = _check_secrets("-----BEGIN PRIVATE KEY-----\nblah")
        assert len(found) > 0

    def test_clean_code(self):
        found = _check_secrets("print('hello world')")
        assert len(found) == 0

    def test_secret_blocks_commit(self):
        tmp_path = Path(__file__).parent / "_secret_test"
        tmp_path.mkdir(exist_ok=True)
        try:
            _init_repo(tmp_path)
            _write(tmp_path, "config.txt", "api_key = sk-abc123def456ghi789")
            tool = _git_tool(tmp_path)
            _run_sync(tool.run(action="add", paths=["*"]))
            r = _run_sync(tool.run(action="commit", message="leak"))
            assert not r.success
            assert "secret" in r.error.lower()
        finally:
            import shutil
            shutil.rmtree(tmp_path, ignore_errors=True)


# ── unknown action ────────────────────────────────────────────────────

def test_unknown_action(tmp_path: Path):
    tool = _git_tool(tmp_path)
    r = _run_sync(tool.run(action="nonexistent"))
    assert not r.success
    assert "unknown" in r.error.lower()


# ── secret patterns regex sanity ─────────────────────────────────────

def test_all_secret_patterns_compile():
    for p in SECRET_PATTERNS:
        assert re.compile(p)
