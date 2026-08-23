"""DeepInfra OpenAI-compatible API client."""

import httpx

from llm_cost_comparison.clients.openrouter import OpenRouterClient
from llm_cost_comparison.core.config import Settings


class DeepInfraClient(OpenRouterClient):
    """HTTP client for DeepInfra's OpenAI-compatible chat endpoint."""

    BASE_URL = "https://api.deepinfra.com/v1/openai"
    provider_name = "deepinfra"

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the client with a DeepInfra token."""
        self.settings = settings or Settings()
        if self.settings.deepinfra_api_key is None:
            raise ValueError("DEEPINFRA_API_KEY is required for the DeepInfra provider")
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(self.settings.default_timeout),
            headers={
                "Authorization": f"Bearer {self.settings.deepinfra_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
        )
