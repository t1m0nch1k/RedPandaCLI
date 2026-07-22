from __future__ import annotations

from pathlib import Path

from aios.plugins.provider_plugin import ProviderPlugin
from aios.providers.plugins import (
    _find_provider_plugin_class,
    load_provider_plugin_from_dir,
)
from aios.providers.registry import (
    build_provider_cls,
    get_provider_class,
    list_registered_providers,
    register_provider,
)

TEST_PLUGIN_DIR = Path(__file__).parent / "plugins" / "example_provider"


def test_register_and_list_providers():
    register_provider("test-llm", object)
    names = list_registered_providers()
    assert "test-llm" in names


def test_get_provider_class():
    assert get_provider_class("ollama") is not None
    assert get_provider_class("openai-compatible") is not None


def test_build_via_registered_class():
    cls = get_provider_class("openai-compatible")
    assert cls is not None
    inst = cls(base_url="http://localhost:11434/v1", model="test")
    assert inst.model == "test"


def test_build_provider_cls_fallback():
    inst = build_provider_cls("unknown", "test-model", "http://localhost:8000")
    from aios.providers.openai_compatible import OpenAICompatibleProvider

    assert isinstance(inst, OpenAICompatibleProvider)


def test_load_example_provider_from_dir():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None
    assert plugin.name == "echo"
    assert plugin.metadata.version == "0.1.0"

    cls = plugin.get_provider_class()
    assert cls.__name__ == "EchoProvider"
    inst = cls(base_url="", model="test")
    assert inst.name == "echo"


def test_find_provider_plugin_class():
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "test_echo_plugin",
        str(TEST_PLUGIN_DIR / "plugin.py"),
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    cls = _find_provider_plugin_class(mod)
    assert cls is not None
    assert issubclass(cls, ProviderPlugin)
    assert cls is not ProviderPlugin


def test_register_and_build_echo():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None

    cls = plugin.get_provider_class()
    register_provider("echo", cls)

    retrieved = get_provider_class("echo")
    assert retrieved is cls

    inst = retrieved(base_url="", model="test")
    assert inst.name == "echo"


def test_echo_provider_complete():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None
    cls = plugin.get_provider_class()
    inst = cls(base_url="", model="test")

    from aios.core.models import Message, Role

    msgs = [Message(role=Role.USER, content="hello")]
    import asyncio

    text = asyncio.run(inst.complete(msgs))
    assert "hello" in text


def test_echo_provider_stream():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None
    cls = plugin.get_provider_class()
    inst = cls(base_url="", model="test")

    from aios.core.models import Message, Role

    msgs = [Message(role=Role.USER, content="hello")]
    import asyncio

    parts = asyncio.run(async_list(inst.stream(msgs)))
    assert "hello" in "".join(parts)


def test_echo_provider_chat():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None
    cls = plugin.get_provider_class()
    inst = cls(base_url="", model="test")

    from aios.core.models import Message, Role

    msgs = [Message(role=Role.USER, content="hello")]
    import asyncio

    resp = asyncio.run(inst.chat(msgs))
    assert "hello" in resp["content"]


def test_echo_provider_stream_chat():
    plugin = load_provider_plugin_from_dir(TEST_PLUGIN_DIR)
    assert plugin is not None
    cls = plugin.get_provider_class()
    inst = cls(base_url="", model="test")

    from aios.core.models import Message, Role

    msgs = [Message(role=Role.USER, content="hello")]
    import asyncio

    chunks = asyncio.run(async_list(inst.stream_chat(msgs)))
    assert any("hello" in c.content for c in chunks if c.type == "content")


async def async_list(async_iter):
    return [item async for item in async_iter]
