"""Speed experiment."""

from decimal import Decimal

from llm_bench_data.calculations.cost import CostCalculator
from llm_bench_data.clients.base import LLMClient
from llm_bench_data.core.models import (
    Catalog,
    ChatRequest,
    ExperimentConfig,
    Message,
    ProviderPricing,
)
from llm_bench_data.experiments.base import Experiment, register
from llm_bench_data.storage.models import ExperimentRun, Measurement


@register
class SpeedExperiment(Experiment):
    """Measure tokens per second for a fixed generation prompt."""

    experiment_type = "speed"

    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Run the speed benchmark for all configured models."""
        if run.id is None:
            raise ValueError("Run must be persisted before running an experiment")
        run_id = run.id
        measurements: list[Measurement] = []
        prompt = config.params.prompt or "Write the numbers from 1 to 200, comma-separated."
        max_tokens = config.params.max_tokens or 3300

        for model in catalog.resolve_model_refs(config.model_refs):
            model_key = client.model_id(model)
            response = client.chat(
                ChatRequest(
                    model_id=model_key,
                    messages=[Message(role="user", content=prompt)],
                    max_tokens=max_tokens,
                )
            )
            price = pricing.get(model_key)
            cost = CostCalculator.compute(
                response.prompt_tokens,
                response.completion_tokens,
                price,
            )
            tokens_per_second = (
                Decimal(response.completion_tokens) * 1000 / Decimal(response.elapsed_ms)
                if response.elapsed_ms
                else None
            )
            measurements.append(
                Measurement(
                    run_id=run_id,
                    experiment_id=config.id,
                    model_slug=model.slug,
                    model_id=model_key,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    elapsed_ms=response.elapsed_ms,
                    cost=cost,
                    meta={
                        "tokens_per_second": str(tokens_per_second) if tokens_per_second else None
                    },
                )
            )

        return measurements
