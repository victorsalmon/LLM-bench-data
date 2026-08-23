"""Typed domain models for catalog data and measurements."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class ProviderPricing(BaseModel):
    """Per-provider token pricing."""

    model_config = ConfigDict(extra="forbid")

    input: Decimal | None = None
    output: Decimal | None = None
    cached_read: Decimal | None = None


class MaxVariant(BaseModel):
    """A max/reasoning variant of a base model."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    suffix: str = "max"
    openrouter_id: str | None = None
    reasoning_effort: str | None = None


class Model(BaseModel):
    """Static metadata for an LLM."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    family: str
    openrouter_id: str | None = None
    deepinfra_id: str | None = None
    zen_id: str | None = None
    zen_available: bool = False
    tier: str
    context_window: int | None = None
    parameters: str | None = None
    open_weights: bool | None = None
    license: str | None = None
    aliases: list[str] = Field(default_factory=list)
    max_variants: list[MaxVariant] = Field(default_factory=list)
    reasoning_effort: str | None = None
    pricing_source: str | None = None
    pricing: dict[str, ProviderPricing] | None = None
    features: str | None = None
    specialty: str | None = None
    strategy_note: str | None = None
    notes: str | None = None

    def provider_id(self, provider: str) -> str:
        """Return this model's identifier for *provider*."""
        provider_id = getattr(self, f"{provider}_id", None)
        if provider_id:
            return provider_id
        if provider == "openrouter":
            return self.slug
        raise ValueError(f"Model '{self.slug}' has no {provider} identifier")


class Task(BaseModel):
    """A single benchmark task/prompt."""

    model_config = ConfigDict(extra="forbid")

    id: str
    prompt: str
    category: str
    max_tokens: int
    fallback_tokens: int | None = None


class Sample(BaseModel):
    """A fixed text sample used to measure tokenizer efficiency."""

    model_config = ConfigDict(extra="forbid")

    id: str
    path: Path
    word_count: int
    description: str | None = None

    def absolute_path(self, root: Path) -> Path:
        """Resolve the sample path relative to the repository root."""
        return (root / self.path).resolve()


class Method(BaseModel):
    """A compression or prompting method."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    system_prompt: str


class ExperimentParams(BaseModel):
    """Default parameters shared by all experiments."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = 0.0
    timeout: int = 120
    max_retries: int = 3
    sleep_ms: int = 200
    max_tokens: int | None = None
    fallback_tokens: int | None = None
    prompt: str | None = None


class ExperimentConfig(BaseModel):
    """Static configuration for an experiment type."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    description: str | None = None
    model_refs: list[str] = Field(default_factory=list)
    task_refs: list[str] = Field(default_factory=list)
    sample_refs: list[str] = Field(default_factory=list)
    method_refs: list[str] = Field(default_factory=list)
    params: ExperimentParams = Field(default_factory=ExperimentParams)


class Tier(BaseModel):
    """A price tier classification."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    label: str
    output_price_min: Decimal | None = None
    output_price_max: Decimal | None = None
    role: str
    top_pick: str | None = None
    top_3: list[str] = Field(default_factory=list)


class AppraiseSlots(BaseModel):
    """Watch list used when appraising a new model."""

    model_config = ConfigDict(extra="forbid")

    active_stack: list[str] = Field(default_factory=list)
    watching: dict[str, str | None] = Field(default_factory=dict)


class PricingSource(BaseModel):
    """Metadata about a pricing source."""

    model_config = ConfigDict(extra="forbid")

    name: str
    docs: str
    type: str
    markup: str


class Catalog(BaseModel):
    """Aggregated in-memory catalog loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    models: list[Model]
    tasks: list[Task]
    samples: list[Sample]
    methods: list[Method]
    experiments: list[ExperimentConfig]
    tiers: list[Tier] = Field(default_factory=list)
    appraise_slots: AppraiseSlots = Field(default_factory=AppraiseSlots)
    pricing_sources: dict[str, PricingSource] = Field(default_factory=dict)
    root_path: Path = Field(default=Path("."))

    _model_lookup: dict[str, Model] = PrivateAttr(default_factory=dict)
    _alias_lookup: dict[str, Model] = PrivateAttr(default_factory=dict)
    _openrouter_lookup: dict[str, Model] = PrivateAttr(default_factory=dict)
    _task_lookup: dict[str, Task] = PrivateAttr(default_factory=dict)
    _sample_lookup: dict[str, Sample] = PrivateAttr(default_factory=dict)
    _method_lookup: dict[str, Method] = PrivateAttr(default_factory=dict)
    _experiment_lookup: dict[str, ExperimentConfig] = PrivateAttr(default_factory=dict)
    _tier_lookup: dict[str, Tier] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Build lookup indexes after validation."""
        for model in self.models:
            self._model_lookup[model.slug] = model
            for alias in model.aliases:
                self._alias_lookup[alias] = model
            if model.openrouter_id:
                self._openrouter_lookup[model.openrouter_id] = model
            for variant in model.max_variants:
                if variant.openrouter_id:
                    self._openrouter_lookup[variant.openrouter_id] = model

        for task in self.tasks:
            self._task_lookup[task.id] = task
        for sample in self.samples:
            self._sample_lookup[sample.id] = sample
        for method in self.methods:
            self._method_lookup[method.id] = method
        for experiment in self.experiments:
            self._experiment_lookup[experiment.id] = experiment
        for tier in self.tiers:
            self._tier_lookup[tier.slug] = tier

    def get_model(self, slug: str) -> Model:
        """Look up a model by slug or alias."""
        if slug in self._model_lookup:
            return self._model_lookup[slug]
        if slug in self._alias_lookup:
            return self._alias_lookup[slug]
        from llm_cost_comparison.core.exceptions import CatalogError

        raise CatalogError(f"Model '{slug}' not found in catalog")

    def get_model_by_openrouter_id(self, openrouter_id: str) -> Model:
        """Look up a model by its OpenRouter provider ID."""
        if openrouter_id in self._openrouter_lookup:
            return self._openrouter_lookup[openrouter_id]
        from llm_cost_comparison.core.exceptions import CatalogError

        raise CatalogError(f"OpenRouter model '{openrouter_id}' not found in catalog")

    def get_task(self, task_id: str) -> Task:
        """Look up a task by ID."""
        if task_id not in self._task_lookup:
            from llm_cost_comparison.core.exceptions import CatalogError

            raise CatalogError(f"Task '{task_id}' not found in catalog")
        return self._task_lookup[task_id]

    def get_sample(self, sample_id: str) -> Sample:
        """Look up a sample by ID."""
        if sample_id not in self._sample_lookup:
            from llm_cost_comparison.core.exceptions import CatalogError

            raise CatalogError(f"Sample '{sample_id}' not found in catalog")
        return self._sample_lookup[sample_id]

    def get_method(self, method_id: str) -> Method:
        """Look up a method by ID."""
        if method_id not in self._method_lookup:
            from llm_cost_comparison.core.exceptions import CatalogError

            raise CatalogError(f"Method '{method_id}' not found in catalog")
        return self._method_lookup[method_id]

    def get_experiment(self, experiment_id: str) -> ExperimentConfig:
        """Look up an experiment by ID."""
        experiment = next(
            (e for e in self.experiments if e.id == experiment_id),
            None,
        )
        if experiment is None:
            from llm_cost_comparison.core.exceptions import CatalogError

            raise CatalogError(f"Experiment '{experiment_id}' not found in catalog")
        return experiment

    def get_tier(self, tier_slug: str) -> Tier:
        """Look up a tier by slug."""
        if tier_slug not in self._tier_lookup:
            from llm_cost_comparison.core.exceptions import CatalogError

            raise CatalogError(f"Tier '{tier_slug}' not found in catalog")
        return self._tier_lookup[tier_slug]

    def resolve_model_refs(self, refs: list[str]) -> list[Model]:
        """Resolve a list of model references ('all' or slugs) to models."""
        if refs == ["all"]:
            return self.models
        return [self.get_model(ref) for ref in refs]

    def resolve_task_refs(self, refs: list[str]) -> list[Task]:
        """Resolve a list of task references ('all' or IDs) to tasks."""
        if refs == ["all"]:
            return self.tasks
        return [self.get_task(ref) for ref in refs]

    def resolve_sample_refs(self, refs: list[str]) -> list[Sample]:
        """Resolve a list of sample references ('all' or IDs) to samples."""
        if refs == ["all"]:
            return self.samples
        return [self.get_sample(ref) for ref in refs]

    def resolve_method_refs(self, refs: list[str]) -> list[Method]:
        """Resolve a list of method references ('all' or IDs) to methods."""
        if refs == ["all"]:
            return self.methods
        return [self.get_method(ref) for ref in refs]


class Message(BaseModel):
    """A chat message sent to an LLM API."""

    model_config = ConfigDict(extra="forbid")

    role: str
    content: str


class ChatRequest(BaseModel):
    """Request payload for a single chat completion."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    messages: list[Message]
    max_tokens: int
    temperature: float = 0.0
    reasoning_effort: str | None = None

    def to_api_body(self) -> dict[str, object]:
        """Build the JSON body expected by OpenAI-compatible endpoints."""
        body: dict[str, object] = {
            "model": self.model_id,
            "messages": [m.model_dump() for m in self.messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if self.reasoning_effort is not None:
            body["reasoning_effort"] = self.reasoning_effort
        return body


class ChatResponse(BaseModel):
    """Response data returned from a chat completion."""

    model_config = ConfigDict(extra="forbid")

    model_id: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    elapsed_ms: int
    cost: Decimal | None = None
