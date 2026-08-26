"""Tests for application settings."""

from pathlib import Path

import pytest

from llm_bench_data.core.config import Settings


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Settings are loaded from environment variables."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("LLMCC_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("LLMCC_DATABASE_URL", "sqlite:///custom.db")

    settings = Settings()
    assert settings.openrouter_api_key.get_secret_value() == "sk-or-v1-test"
    assert settings.output_dir == tmp_path / "out"
    assert settings.database_url == "sqlite:///custom.db"


def test_settings_redacts_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API key is a SecretStr and is not leaked by repr/str."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-secret")

    settings = Settings()
    assert "sk-or-v1-secret" not in str(settings.openrouter_api_key)


def test_alibaba_settings_use_workspace_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALIBABA_API", "alibaba-test-key")
    monkeypatch.setenv("ALIBABA_ID1", "workspace-test")

    settings = Settings()

    assert settings.alibaba_api_key.get_secret_value() == "alibaba-test-key"
    assert settings.alibaba_workspace_id == "workspace-test"


def test_alibaba_settings_support_legacy_key_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALIBABA_KEYSUB", "legacy-alibaba-test-key")

    settings = Settings()

    assert settings.alibaba_api_key.get_secret_value() == "legacy-alibaba-test-key"
    assert "sk-or-v1-secret" not in repr(settings)
