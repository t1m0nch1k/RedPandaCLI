from __future__ import annotations

import pytest

from aios.cli.slash import (
    dispatch_slash_command,
    get_commands,
    get_command,
    get_categories,
    register,
    _COMMANDS,
)


def teardown_module():
    _COMMANDS.clear()
    from aios.cli import slash as mod
    import importlib
    importlib.reload(mod)


class TestRegistration:
    def test_register_and_list(self):
        register(["test-cmd"], lambda a: "ok", "Test", "test description")
        cmds = get_commands()
        names = [c["name"] for c in cmds]
        assert "test-cmd" in names

    def test_get_command(self):
        cmd = get_command("/help")
        assert cmd is not None
        assert cmd["name"] == "/help"

    def test_get_command_nonexistent(self):
        assert get_command("/nonexistent") is None

    def test_get_categories(self):
        cats = get_categories()
        assert "Core" in cats
        assert "Git" in cats
        assert "System" in cats


class TestDispatch:
    async def test_help(self):
        result = await dispatch_slash_command("/help")
        assert result is not None
        assert "AIOS Commands" in result

    async def test_help_shorthand(self):
        result = await dispatch_slash_command("/?")
        assert result is not None

    async def test_exit(self):
        result = await dispatch_slash_command("/exit")
        assert result == "EXIT"

    async def test_quit(self):
        result = await dispatch_slash_command("/quit")
        assert result == "EXIT"

    async def test_clear(self):
        result = await dispatch_slash_command("/clear")
        assert result == "CLEAR"

    async def test_version(self):
        result = await dispatch_slash_command("/version")
        assert result is not None
        assert "AIOS CLI" in result

    async def test_unknown(self):
        result = await dispatch_slash_command("/nonexistent")
        assert result is None

    async def test_empty_string(self):
        result = await dispatch_slash_command("")
        assert result is None

    async def test_only_slash(self):
        result = await dispatch_slash_command("/")
        assert result is None

    async def test_no_slash(self):
        result = await dispatch_slash_command("just a message")
        assert result is None

    async def test_doctor(self):
        result = await dispatch_slash_command("/doctor")
        assert result is not None
        assert "Python" in result or "Config" in result
