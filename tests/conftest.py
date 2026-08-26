"""Shared test fixtures."""

import pytest

from llm_bench_data.core.config import Settings


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Return a Settings instance with a dummy API key and short retries."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test-key")
    monkeypatch.setenv("LLMCC_DEFAULT_RETRIES", "2")
    return Settings()
