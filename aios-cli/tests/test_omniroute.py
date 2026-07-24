import pytest
from aios.config.settings import Settings
from aios.providers.registry import build_provider, build_provider_cls


def test_build_omniroute_provider_cls():
    """Verify build_provider_cls instantiates OmniRoute as OpenAI-compatible provider."""
    provider = build_provider_cls("omniroute", "gpt-4o", "http://localhost:8000/v1")
    assert provider.name == "openai_compatible"
    assert provider.base_url == "http://localhost:8000/v1"
    assert provider.model == "gpt-4o"


def test_build_omniroute_provider_fallback():
    """Verify build_provider successfully resolves omniroute with fallback."""
    settings = Settings()
    provider = build_provider("omniroute", "claude-3-5-sonnet", settings)
    assert provider.name == "openai_compatible"
    assert provider.base_url == "http://localhost:8000/v1"
    assert provider.model == "claude-3-5-sonnet"
