"""Tests for compression calculations."""

from decimal import Decimal

import pytest

from llm_bench_data.calculations.compression import CompressionCalculator


def test_compression_ratio_positive() -> None:
    """A 50% token reduction yields a 0.50 compression ratio."""
    assert CompressionCalculator.compression_ratio(50, 100) == Decimal("0.50")


def test_compression_ratio_negative() -> None:
    """A 50% token increase yields a -0.50 compression ratio."""
    assert CompressionCalculator.compression_ratio(150, 100) == Decimal("-0.50")


def test_compression_ratio_zero_baseline_raises() -> None:
    """A zero baseline is undefined."""
    with pytest.raises(ValueError):  # noqa: PT011
        CompressionCalculator.compression_ratio(50, 0)


def test_tokens_per_word() -> None:
    """Output tokens per word is rounded to two decimals."""
    assert CompressionCalculator.tokens_per_word(50, 25) == Decimal("2.00")
