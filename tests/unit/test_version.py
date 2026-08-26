"""Smoke test that the package is importable."""

import llm_bench_data


def test_version() -> None:
    """The package exposes a version string."""
    assert llm_bench_data.__version__ == "2.0.0"
