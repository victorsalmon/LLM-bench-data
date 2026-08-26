"""Tokenizer efficiency (tokens per word) calculations."""

from decimal import ROUND_HALF_UP, Decimal


class EfficiencyCalculator:
    """Pure functions for tokenizer-efficiency metrics."""

    @staticmethod
    def tokens_per_word(prompt_tokens: int, word_count: int) -> Decimal:
        """E = prompt_tokens / word_count."""
        if word_count <= 0:
            raise ValueError("word_count must be positive")
        return (Decimal(prompt_tokens) / Decimal(word_count)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def blend_60_40(e_code: Decimal | float, e_prose: Decimal | float) -> Decimal:
        """Weighted 60% code, 40% prose blend."""
        return (
            Decimal("0.6") * Decimal(str(e_code)) + Decimal("0.4") * Decimal(str(e_prose))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def blend_33_33_33(
        e_code: Decimal | float,
        e_prose: Decimal | float,
        e_blended: Decimal | float,
    ) -> Decimal:
        """Equal-weight blend of code, prose, and blended samples."""
        return (
            (Decimal(str(e_code)) + Decimal(str(e_prose)) + Decimal(str(e_blended))) / Decimal("3")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
