"""SQLModel tables for measured benchmark data."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return the current UTC time as a naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


class ExperimentRun(SQLModel, table=True):
    """A single execution of an experiment configuration."""

    id: int | None = Field(default=None, primary_key=True)
    experiment_id: str = Field(index=True)
    started_at: datetime = Field(default_factory=_utc_now)
    finished_at: datetime | None = None
    status: str = "running"
    parameters: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    notes: str | None = None


class Measurement(SQLModel, table=True):
    """One raw or derived measurement row."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="experimentrun.id", index=True)
    experiment_id: str = Field(index=True)
    model_slug: str = Field(index=True)
    model_id: str | None = None
    task_id: str | None = None
    sample_id: str | None = None
    method_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    output_words: int | None = None
    reasoning_tokens: int | None = None
    elapsed_ms: int | None = None
    cost: Decimal | None = Field(default=None, decimal_places=10, max_digits=20)
    status: str = "success"
    error: str | None = None
    meta: dict[str, Any] | None = Field(default=None, sa_type=JSON)
    created_at: datetime = Field(default_factory=_utc_now)

    @property
    def output_tokens(self) -> int | None:
        """Alias completion_tokens as output_tokens for clarity."""
        return self.completion_tokens


class PricingSnapshot(SQLModel, table=True):
    """A cached live-pricing observation from OpenRouter."""

    id: int | None = Field(default=None, primary_key=True)
    model_id: str = Field(index=True)
    input: Decimal | None = Field(default=None, decimal_places=10, max_digits=20)
    output: Decimal | None = Field(default=None, decimal_places=10, max_digits=20)
    cached_read: Decimal | None = Field(default=None, decimal_places=10, max_digits=20)
    source: str
    fetched_at: datetime = Field(default_factory=_utc_now)
