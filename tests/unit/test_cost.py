"""Tests for cost and blended-price calculations."""

from decimal import Decimal

from llm_bench_data.calculations.cost import CostCalculator
from llm_bench_data.core.models import ProviderPricing


def test_compute_per_call_cost() -> None:
    """Cost uses per-million pricing and returns a Decimal."""
    pricing = ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    cost = CostCalculator.compute(1000, 500, pricing)

    assert cost == Decimal("0.00028")


def test_compute_returns_none_when_pricing_missing() -> None:
    """Missing prices produce None instead of a bogus zero cost."""
    assert CostCalculator.compute(1000, 500, None) is None
    assert CostCalculator.compute(1000, 500, ProviderPricing()) is None


def test_blended_price_no_thinking() -> None:
    """Standard 7:2:1 blend for a non-reasoning model."""
    pricing = ProviderPricing(
        cached_read=Decimal("0.028"), input=Decimal("0.14"), output=Decimal("0.28")
    )
    blend = CostCalculator.blended_price(pricing)

    # (7*0.028 + 2*0.14 + 1*0.28) / 10 = (0.196 + 0.28 + 0.28) / 10 = 0.0756
    assert blend == Decimal("0.0756")


def test_blended_price_with_thinking() -> None:
    """Thinking-adjusted 7:2:(1+R) blend."""
    pricing = ProviderPricing(
        cached_read=Decimal("0.145"), input=Decimal("1.74"), output=Decimal("3.48")
    )
    blend = CostCalculator.blended_price(pricing, thinking_token_ratio=Decimal("4"))

    assert blend == Decimal("1.5639")


def test_thinking_adjusted_output_price() -> None:
    """A 4x thinking tax quadruples the effective output price."""
    pricing = ProviderPricing(output=Decimal("3.48"))
    effective = CostCalculator.thinking_adjusted_output_price(pricing, 4)

    assert effective == Decimal("17.4000")
