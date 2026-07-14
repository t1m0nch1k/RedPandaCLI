from __future__ import annotations

from aios.runtime.models import ModelCapabilities


class CapabilityRegistryProtocol:
    """
    Describes model capabilities — what each model can do.

    This is a model-centric registry, not a provider registry.
    A model's capabilities are intrinsic (e.g., GPT-4o supports
    vision regardless of which provider serves it). ProviderRouter
    queries this service to find models that match task requirements.

    Capabilities are identified by string name — the Capability enum
    provides well-known names, but any string is accepted. This keeps
    the registry extensible without interface changes.
    """

    async def get_capabilities(self, model_name: str) -> ModelCapabilities | None:
        """Return the capabilities for a given model name, or None if unknown."""

    async def list_models_with(
        self,
        capabilities: set[str],
    ) -> list[str]:
        """List all model names that satisfy ALL the given capabilities."""

    async def supports(
        self,
        model_name: str,
        capability: str,
    ) -> bool:
        """Check whether a model supports a specific capability."""

    def register_model(self, capabilities: ModelCapabilities) -> None:
        """Register a model with its intrinsic capabilities."""

    def unregister_model(self, model_name: str) -> None:
        """Remove a model from the registry."""

    def list_all_models(self) -> list[str]:
        """Return all registered model names."""
