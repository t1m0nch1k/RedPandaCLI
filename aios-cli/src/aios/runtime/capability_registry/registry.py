from __future__ import annotations

from aios.runtime.models import ModelCapabilities


class CapabilityRegistry:
    """
    Model-centric capability registry.

    Stores what each model can do — capabilities are intrinsic to the
    model, not the provider. New capabilities can be added via the
    `extras` dict on ModelCapabilities without modifying this class.
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelCapabilities] = {}

    async def get_capabilities(self, model_name: str) -> ModelCapabilities | None:
        return self._models.get(model_name)

    async def list_models_with(self, capabilities: set[str]) -> list[str]:
        result: list[str] = []
        for name, caps in self._models.items():
            if all(self._check(caps, c) for c in capabilities):
                result.append(name)
        return result

    async def supports(self, model_name: str, capability: str) -> bool:
        caps = self._models.get(model_name)
        if caps is None:
            return False
        return self._check(caps, capability)

    def register_model(self, capabilities: ModelCapabilities) -> None:
        self._models[capabilities.model_name] = capabilities

    def unregister_model(self, model_name: str) -> None:
        self._models.pop(model_name, None)

    def list_all_models(self) -> list[str]:
        return list(self._models.keys())

    def _find_by_capability(self, capability: str) -> list[str]:
        return [name for name, caps in self._models.items() if self._check(caps, capability)]

    def _check(self, caps: ModelCapabilities, capability: str) -> bool:
        val = caps.get(capability)
        if isinstance(val, bool):
            return val
        if isinstance(val, int) and val > 0:
            return True
        if isinstance(val, str) and val and val != "none":
            return True
        return bool(val)
