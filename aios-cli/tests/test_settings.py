from __future__ import annotations

import os
from pathlib import Path

import pytest

from aios.config.settings import Settings, ProviderConfig, GitConfig, MCPServerConfig, add_provider_to_config, _resolve_env


class TestEnvResolution:
    def test_no_env_var(self):
        assert _resolve_env("hello") == "hello"

    def test_basic_env_var(self):
        os.environ["_TEST_AIOS_VAR"] = "resolved"
        try:
            assert _resolve_env("${_TEST_AIOS_VAR}") == "resolved"
        finally:
            del os.environ["_TEST_AIOS_VAR"]

    def test_unset_env_var_keeps_original(self):
        assert _resolve_env("${_NONEXISTENT_VAR_XYZ}") == "${_NONEXISTENT_VAR_XYZ}"

    def test_env_in_long_string(self):
        os.environ["_TEST_AIOS_HOST"] = "localhost"
        try:
            assert _resolve_env("http://${_TEST_AIOS_HOST}:11434") == "http://localhost:11434"
        finally:
            del os.environ["_TEST_AIOS_HOST"]


class TestProviderConfig:
    def test_defaults(self):
        cfg = ProviderConfig()
        assert cfg.api_key == ""
        assert cfg.base_url == ""

    def test_custom_values(self):
        cfg = ProviderConfig(api_key="x", base_url="http://example.com")
        assert cfg.api_key == "x"
        assert cfg.base_url == "http://example.com"


class TestGitConfig:
    def test_defaults(self):
        cfg = GitConfig()
        assert cfg.auto_commit is False
        assert "main" in cfg.protected_branches
        assert cfg.secret_scanning is True
        assert cfg.commit_prefix == "aios: "

    def test_custom(self):
        cfg = GitConfig(auto_commit=True, protected_branches=["stable"], secret_scanning=False, commit_prefix="bot: ")
        assert cfg.auto_commit is True
        assert cfg.protected_branches == ["stable"]
        assert cfg.secret_scanning is False
        assert cfg.commit_prefix == "bot: "


class TestMCPServerConfig:
    def test_defaults(self):
        cfg = MCPServerConfig()
        assert cfg.name == ""
        assert cfg.transport == "stdio"
        assert cfg.url == ""

    def test_stdio_config(self):
        cfg = MCPServerConfig(name="test", command="node", args=["server.js"])
        assert cfg.name == "test"
        assert cfg.command == "node"


class TestSettings:
    def test_default_model(self):
        s = Settings()
        assert s.default_model == "qwen3:8b"
        assert s.default_provider == "ollama"
        assert s.temperature == 0.2
        assert s.providers == {}
        assert s.mcp_servers == []

    def test_custom_settings(self):
        s = Settings(
            default_provider="openai",
            default_model="gpt-4",
            temperature=0.7,
            providers={"openai": ProviderConfig(api_key="x", base_url="https://api.openai.com/v1")},
        )
        assert s.default_provider == "openai"
        assert s.default_model == "gpt-4"
        assert s.temperature == 0.7
        assert s.providers["openai"].api_key == "x"

    def test_round_trip_providers(self):
        s = Settings(
            providers={
                "ollama": ProviderConfig(base_url="http://localhost:11434"),
                "groq": ProviderConfig(api_key="abc", base_url="https://api.groq.com/openai/v1"),
            }
        )
        assert list(s.providers.keys()) == ["ollama", "groq"]


class TestAddProvider:
    def test_add_new_provider(self, tmp_path: Path):
        from aios.config.settings import CONFIG_FILE
        old_file = CONFIG_FILE if Path(str(CONFIG_FILE)).exists() else None

        test_config = tmp_path / "config.toml"
        test_config.write_text('default_provider = "ollama"\n')
        import aios.config.settings as s
        original = s.CONFIG_FILE
        s.CONFIG_FILE = test_config
        s.CONFIG_DIR = tmp_path

        try:
            add_provider_to_config("test-llm", "http://test:8000", "sekret")
            content = test_config.read_text()
            assert "[providers.test-llm]" in content
            assert "http://test:8000" in content
            assert 'api_key = "sekret"' in content
        finally:
            s.CONFIG_FILE = original

    def test_add_existing_provider_does_not_duplicate(self, tmp_path: Path):
        test_config = tmp_path / "config.toml"
        test_config.write_text('default_provider = "ollama"\n[providers.test-llm]\napi_key = "x"\nbase_url = "y"\n')
        import aios.config.settings as s
        original = s.CONFIG_FILE
        s.CONFIG_FILE = test_config
        s.CONFIG_DIR = tmp_path

        try:
            add_provider_to_config("test-llm", "http://dup")
            content = test_config.read_text()
            assert content.count("[providers.test-llm]") == 1
        finally:
            s.CONFIG_FILE = original
