"""Abstract base class for LLM API clients."""

from abc import ABC, abstractmethod
from typing import Protocol

from llm_bench_data.core.models import ChatRequest, ChatResponse


class CatalogModel(Protocol):
    """Minimum catalog-model interface required by a provider client."""

    def provider_id(self, provider: str) -> str:
        """Return a provider-specific model identifier."""


class LLMClient(ABC):
    """Abstract client for sending chat completion requests."""

    provider_name = "openrouter"

    def model_id(self, model: CatalogModel) -> str:
        """Resolve a catalog model to this provider's model identifier."""
        return model.provider_id(self.provider_name)

    @abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request and return a typed response."""

    @abstractmethod
    def close(self) -> None:
        """Close any underlying HTTP resources."""
