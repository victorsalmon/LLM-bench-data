"""Live pricing lookup from OpenRouter, cached in memory."""

from decimal import Decimal
from typing import Any

import httpx

from llm_bench_data.core.config import Settings
from llm_bench_data.core.exceptions import APIError
from llm_bench_data.core.models import ProviderPricing


class PricingService:
    """Fetch and cache model pricing from OpenRouter.

    Prices are stored as dollars per million tokens to match the catalog
    and the site-facing benchmark artifact.
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    _TOKEN_TO_MILLION = Decimal("1000000")

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the pricing service with settings and an HTTP client."""
        self.settings = settings or Settings()
        if self.settings.openrouter_api_key is None:
            raise ValueError("OPENROUTER_API_KEY is required for the pricing service")
        api_key = self.settings.openrouter_api_key.get_secret_value()
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": self.settings.referer,
            },
        )
        self._cache: dict[str, ProviderPricing] | None = None

    def refresh(self) -> dict[str, ProviderPricing]:
        """Fetch the latest OpenRouter model list and build the pricing cache."""
        try:
            response = self._client.get("/models")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise APIError(f"Could not fetch OpenRouter pricing: {exc}") from exc

        data = response.json()
        cache: dict[str, ProviderPricing] = {}
        for item in data.get("data", []):
            model_id = item.get("id")
            pricing = item.get("pricing", {})
            if not model_id or not pricing:
                continue
            cache[model_id] = self._parse_pricing(pricing)

        self._cache = cache
        return cache

    def _parse_pricing(self, pricing: dict[str, Any]) -> ProviderPricing:
        """Convert OpenRouter per-token prices to dollars per million tokens."""
        return ProviderPricing(
            input=self._per_million(pricing.get("prompt")),
            output=self._per_million(pricing.get("completion")),
            cached_read=self._per_million(pricing.get("input_cache_read")),
        )

    def _per_million(self, value: Any) -> Decimal | None:
        """Convert a per-token price to a per-million-token price."""
        if value is None:
            return None
        return Decimal(str(value)) * self._TOKEN_TO_MILLION

    def get(self, model_id: str) -> ProviderPricing | None:
        """Return live pricing for *model_id*, fetching once if needed."""
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache.get(model_id)

    def get_all(self) -> dict[str, ProviderPricing]:
        """Return the full pricing cache, fetching once if needed."""
        if self._cache is None:
            self.refresh()
        assert self._cache is not None
        return self._cache

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
