from __future__ import annotations

from aios.config.settings import Settings
from aios.providers.base import LLMProvider
from aios.providers.gemini import GeminiProvider
from aios.providers.ollama import OllamaProvider
from aios.providers.openai_compatible import OpenAICompatibleProvider

_provider_classes: dict[str, type[LLMProvider]] = {}
_provider_instances: dict[str, type[LLMProvider]] = {}


def register_provider(name: str, provider_class: type[LLMProvider]) -> None:
    _provider_classes[name] = provider_class


def get_provider_class(name: str) -> type[LLMProvider] | None:
    return _provider_classes.get(name)


def list_registered_providers() -> list[str]:
    return list(_provider_classes.keys())


register_provider("ollama", OllamaProvider)
register_provider("openai-compatible", OpenAICompatibleProvider)
register_provider("gemini", GeminiProvider)


def build_provider(name: str, model: str, settings: Settings) -> LLMProvider:
    cfg = settings.providers.get(name)
    if cfg is None:
        if name == "omniroute":
            return build_provider_cls("omniroute", model, "https://investigation-raises-ingredients-slight.trycloudflare.com/v1")
        raise ValueError(f"Unknown provider: {name}. Add it to ~/.aios/config.toml first.")

    cls = _provider_classes.get(name)
    if cls is None:
        cls = OpenAICompatibleProvider

    return cls(base_url=cfg.base_url, api_key=cfg.api_key, model=model)


def build_provider_cls(name: str, model: str, base_url: str, api_key: str = "") -> LLMProvider:
    cls = _provider_classes.get(name)
    if cls is None:
        cls = OpenAICompatibleProvider
    return cls(base_url=base_url, api_key=api_key, model=model)


def list_provider_names(settings: Settings) -> list[str]:
    return list(settings.providers.keys())
