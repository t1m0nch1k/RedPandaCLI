import pytest

from aios.config.settings import ProviderConfig, Settings
from aios.providers.ollama import OllamaProvider
from aios.providers.openai_compatible import OpenAICompatibleProvider
from aios.providers.registry import build_provider


def _settings() -> Settings:
    return Settings(
        providers={
            "ollama": ProviderConfig(base_url="http://localhost:11434"),
            "groq": ProviderConfig(api_key="x", base_url="https://api.groq.com/openai/v1"),
            "openai": ProviderConfig(api_key="x", base_url="https://api.openai.com/v1"),
        }
    )


def test_build_ollama_provider():
    provider = build_provider("ollama", "qwen3:8b", _settings())
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "qwen3:8b"


def test_build_openai_like_provider():
    provider = build_provider("groq", "llama-3.3-70b", _settings())
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_key == "x"


@pytest.mark.asyncio
async def test_ollama_has_model_matching(monkeypatch):
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3:8b")

    async def fake_list_models():
        return ["qwen3:8b", "llama3:70b"]

    monkeypatch.setattr(provider, "list_models", fake_list_models)

    assert await provider.has_model("qwen3:8b") is True
    assert await provider.has_model("qwen3") is True
    assert await provider.has_model("mistral") is False


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        build_provider("nope", "model", _settings())
