"""Alibaba Cloud Model Studio OpenAI-compatible API client."""

from urllib.parse import quote

import httpx

from llm_bench_data.clients.openrouter import OpenRouterClient
from llm_bench_data.core.config import Settings


class AlibabaClient(OpenRouterClient):
    """HTTP client for Alibaba Cloud's workspace-scoped chat endpoint."""

    provider_name = "alibaba"

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the client with Alibaba API key and workspace settings."""
        self.settings = settings or Settings()
        if self.settings.alibaba_api_key is None:
            raise ValueError("ALIBABA_KEYSUB is required for the Alibaba provider")
        if not self.settings.alibaba_workspace_id:
            raise ValueError("ALIBABA_ID1 is required for the Alibaba provider")

        configured_endpoint = self.settings.alibaba_workspace_id.rstrip("/")
        if configured_endpoint.startswith(("https://", "http://")):
            self.base_url = configured_endpoint
        else:
            workspace_id = quote(configured_endpoint, safe="")
            self.base_url = (
                f"https://{workspace_id}.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
            )
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.settings.default_timeout),
            headers={
                "Authorization": f"Bearer {self.settings.alibaba_api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
        )
