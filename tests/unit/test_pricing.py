"""Tests for the live pricing service."""

from decimal import Decimal

import respx

from llm_bench_data.clients.pricing import PricingService
from llm_bench_data.core.config import Settings


def _models_payload() -> dict:
    return {
        "data": [
            {
                "id": "deepseek/deepseek-v4-flash",
                "pricing": {
                    "prompt": "0.0000000938",
                    "completion": "0.0000001876",
                    "input_cache_read": "0.00000001876",
                },
            }
        ]
    }


def test_pricing_converts_per_token_to_per_million(settings: Settings) -> None:
    """OpenRouter per-token prices are converted to dollars per million tokens."""
    with respx.mock:
        route = respx.get("https://openrouter.ai/api/v1/models").respond(
            200, json=_models_payload()
        )

        service = PricingService(settings)
        pricing = service.get("deepseek/deepseek-v4-flash")

        assert pricing is not None
        assert pricing.input == Decimal("0.0938")
        assert pricing.output == Decimal("0.1876")
        assert pricing.cached_read == Decimal("0.01876")
        assert route.call_count == 1


def test_pricing_cache_avoids_duplicate_fetch(settings: Settings) -> None:
    """The second lookup uses the in-memory cache."""
    with respx.mock:
        route = respx.get("https://openrouter.ai/api/v1/models").respond(
            200, json=_models_payload()
        )

        service = PricingService(settings)
        service.get("deepseek/deepseek-v4-flash")
        service.get("deepseek/deepseek-v4-flash")

        assert route.call_count == 1
