"""Tests for tokenizer efficiency calculations."""

from decimal import Decimal

import pytest

from llm_bench_data.calculations.efficiency import EfficiencyCalculator


def test_tokens_per_word() -> None:
    """E = tokens / words, rounded to two decimals."""
    assert EfficiencyCalculator.tokens_per_word(306, 306) == Decimal("1.00")
    assert EfficiencyCalculator.tokens_per_word(612, 306) == Decimal("2.00")


def test_tokens_per_word_zero_words_raises() -> None:
    """Zero word count is an invalid input."""
    with pytest.raises(ValueError):  # noqa: PT011
        EfficiencyCalculator.tokens_per_word(10, 0)


def test_blend_60_40() -> None:
    """60/40 weighted blend of code and prose efficiency."""
    blend = EfficiencyCalculator.blend_60_40("2.00", "1.00")
    assert blend == Decimal("1.60")


def test_blend_33_33_33() -> None:
    """Equal-weight three-way blend."""
    blend = EfficiencyCalculator.blend_33_33_33("2.00", "1.00", "1.50")
    assert blend == Decimal("1.50")
