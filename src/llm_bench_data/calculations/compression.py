"""Compression ratio calculations."""

from decimal import ROUND_HALF_UP, Decimal


class CompressionCalculator:
    """Pure functions for measuring output-compression effectiveness."""

    @staticmethod
    def compression_ratio(method_tokens: int, baseline_tokens: int) -> Decimal:
        """CR = 1 - method_tokens / baseline_tokens.

        A positive value means the method produced fewer tokens than the baseline.
        """
        if baseline_tokens <= 0:
            raise ValueError("baseline_tokens must be positive")
        return (
            Decimal("1") - (Decimal(method_tokens) / Decimal(baseline_tokens))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def tokens_per_word(output_tokens: int, word_count: int) -> Decimal:
        """Output tokens per word for a generated response."""
        if word_count <= 0:
            raise ValueError("word_count must be positive")
        return (Decimal(output_tokens) / Decimal(word_count)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
