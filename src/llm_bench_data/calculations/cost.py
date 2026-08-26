"""Cost calculations: per-call cost and blended price-per-million."""

from decimal import Decimal

from llm_bench_data.core.models import ProviderPricing


class CostCalculator:
    """Compute API call costs and blended price benchmarks."""

    MILLION = Decimal("1000000")

    @classmethod
    def compute(
        cls,
        prompt_tokens: int,
        completion_tokens: int,
        pricing: ProviderPricing | None,
    ) -> Decimal | None:
        """Return the total cost of a single API call.

        *pricing* is expected to be in dollars per million tokens.
        """
        if pricing is None or pricing.input is None or pricing.output is None:
            return None
        prompt_cost = Decimal(prompt_tokens) * pricing.input / cls.MILLION
        completion_cost = Decimal(completion_tokens) * pricing.output / cls.MILLION
        return (prompt_cost + completion_cost).quantize(Decimal("0.00000001"))

    @classmethod
    def blended_price(
        cls,
        pricing: ProviderPricing | None,
        thinking_token_ratio: Decimal | float = 0,
    ) -> Decimal | None:
        """Compute a 7:2:1 (or thinking-adjusted) blended price per million tokens.

        The 7:2:1 ratio mirrors Artificial Analysis' industry standard and is
        extended to account for hidden reasoning tokens when *thinking_token_ratio*
        is greater than zero.
        """
        if pricing is None or pricing.input is None or pricing.output is None:
            return None

        cached_price = pricing.cached_read if pricing.cached_read is not None else pricing.input
        r = Decimal(str(thinking_token_ratio))

        # (7 * P_cached + 2 * P_input + (1 + R) * P_output) / (10 + R)
        denominator = Decimal("10") + r
        numerator = (
            Decimal("7") * cached_price
            + Decimal("2") * pricing.input
            + (Decimal("1") + r) * pricing.output
        )
        return (numerator / denominator).quantize(Decimal("0.0001"))

    @classmethod
    def thinking_adjusted_output_price(
        cls,
        pricing: ProviderPricing | None,
        thinking_token_ratio: Decimal | float = 0,
    ) -> Decimal | None:
        """Return the effective output price after applying the thinking tax."""
        if pricing is None or pricing.output is None:
            return None
        r = Decimal(str(thinking_token_ratio))
        return (pricing.output * (Decimal("1") + r)).quantize(Decimal("0.0001"))
