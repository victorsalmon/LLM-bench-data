"""Base experiment runner and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from llm_cost_comparison.storage.models import ExperimentRun
from llm_cost_comparison.storage.session import get_session

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from llm_cost_comparison.clients.base import LLMClient
    from llm_cost_comparison.core.models import Catalog, ExperimentConfig, ProviderPricing
    from llm_cost_comparison.storage.models import Measurement
    from llm_cost_comparison.storage.repository import MeasurementRepository


class Experiment(ABC):
    """Abstract experiment that produces a list of measurements."""

    experiment_type: ClassVar[str]

    @abstractmethod
    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Execute the experiment and return measurement rows."""


class ExperimentRegistry:
    """Map experiment type strings to Experiment classes."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._experiments: dict[str, type[Experiment]] = {}

    def register(self, experiment_cls: type[Experiment]) -> type[Experiment]:
        """Register an experiment class by its experiment_type."""
        self._experiments[experiment_cls.experiment_type] = experiment_cls
        return experiment_cls

    def get(self, experiment_type: str) -> type[Experiment]:
        """Return the experiment class for *experiment_type*."""
        if experiment_type not in self._experiments:
            raise ValueError(f"Unknown experiment type: {experiment_type}")
        return self._experiments[experiment_type]

    def types(self) -> list[str]:
        """Return the list of registered experiment type names."""
        return sorted(self._experiments.keys())


REGISTRY = ExperimentRegistry()


def register(experiment_cls: type[Experiment]) -> type[Experiment]:
    """Decorator that registers an Experiment subclass with the global registry."""
    REGISTRY.register(experiment_cls)
    return experiment_cls


class ExperimentRunner:
    """Orchestrate loading, executing, and persisting an experiment."""

    def __init__(
        self,
        catalog: Catalog,
        client: LLMClient,
        repository: MeasurementRepository,
        registry: ExperimentRegistry | None = None,
    ) -> None:
        """Initialize the runner with catalog, client, and repository."""
        self.catalog = catalog
        self.client = client
        self.repository = repository
        self.registry = registry or REGISTRY

    def build_catalog_pricing(
        self,
        models: Sequence[Any],
    ) -> dict[str, ProviderPricing]:
        """Build a provider model ID -> pricing map from the catalog."""
        pricing_map: dict[str, ProviderPricing] = {}
        for model in models:
            key = self.client.model_id(model)
            if not model.pricing:
                continue
            provider = self.client.provider_name
            if provider in model.pricing:
                pricing_map[key] = model.pricing[provider]
            elif model.pricing_source and model.pricing_source in model.pricing:
                pricing_map[key] = model.pricing[model.pricing_source]
            else:
                pricing_map[key] = next(iter(model.pricing.values()))
        return pricing_map

    def run_experiment(
        self,
        experiment_id: str,
        pricing: dict[str, ProviderPricing] | None = None,
    ) -> ExperimentRun:
        """Run the configured experiment and persist its measurements."""
        config = self.catalog.get_experiment(experiment_id)
        experiment_cls = self.registry.get(config.type)
        experiment = experiment_cls()

        with get_session(self.repository.engine) as session:
            run = ExperimentRun(
                experiment_id=experiment_id,
                parameters=config.params.model_dump(),
            )
            session.add(run)
            session.flush()
            session.refresh(run)
        assert run.id is not None

        if pricing is None:
            models = self.catalog.resolve_model_refs(config.model_refs)
            pricing = self.build_catalog_pricing(models)

        try:
            measurements = experiment.run(config, self.catalog, self.client, run, pricing)
            self.repository.add_measurements(measurements)
            self.repository.finish_run(run.id, "completed")
        except Exception as exc:
            self.repository.finish_run(run.id, "failed", str(exc))
            raise

        return run
