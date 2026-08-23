"""Application settings loaded from environment and .env files."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: SecretStr | None = Field(
        default=None, validation_alias="OPENROUTER_API_KEY"
    )
    deepinfra_api_key: SecretStr | None = Field(
        default=None, validation_alias="DEEPINFRA_API_KEY"
    )
    alibaba_api_key: SecretStr | None = Field(
        default=None, validation_alias="ALIBABA_KEYSUB"
    )
    alibaba_workspace_id: str | None = Field(
        default=None, validation_alias="ALIBABA_ID1"
    )
    output_dir: Path = Field(default=Path("data"), validation_alias="LLMCC_OUTPUT_DIR")
    database_url: str = Field(
        default="sqlite:///data/llm_cost_comparison.db",
        validation_alias="LLMCC_DATABASE_URL",
    )
    referer: str = Field(
        default="https://github.com/ClockLobsterLabs/LLM-Cost-Comparison",
        validation_alias="LLMCC_REFERER",
    )
    default_timeout: int = Field(default=120, validation_alias="LLMCC_DEFAULT_TIMEOUT")
    default_retries: int = Field(default=3, validation_alias="LLMCC_DEFAULT_RETRIES")
    db_busy_timeout_ms: int = Field(
        default=5000,
        validation_alias="LLMCC_DB_BUSY_TIMEOUT",
    )
