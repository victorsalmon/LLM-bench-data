"""Output verbosity experiment."""

from llm_cost_comparison.calculations.cost import CostCalculator
from llm_cost_comparison.clients.base import LLMClient
from llm_cost_comparison.core.models import (
    Catalog,
    ChatRequest,
    ExperimentConfig,
    Message,
    ProviderPricing,
)
from llm_cost_comparison.experiments.base import Experiment, register
from llm_cost_comparison.experiments.utils import word_count
from llm_cost_comparison.storage.models import ExperimentRun, Measurement


@register
class OutputVerbosityExperiment(Experiment):
    """Measure how many tokens each model uses for fixed tasks."""

    experiment_type = "output_verbosity"

    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Run the output-verbosity benchmark for all configured models and tasks."""
        if run.id is None:
            raise ValueError("Run must be persisted before running an experiment")
        run_id = run.id
        measurements: list[Measurement] = []
        max_tokens = config.params.max_tokens or 1500

        for model in catalog.resolve_model_refs(config.model_refs):
            for task in catalog.resolve_task_refs(config.task_refs):
                model_id = client.model_id(model)
                request = ChatRequest(
                    model_id=model_id,
                    messages=[Message(role="user", content=task.prompt)],
                    max_tokens=task.max_tokens or max_tokens,
                )
                response = client.chat(request)
                price = pricing.get(model_id)
                cost = CostCalculator.compute(
                    response.prompt_tokens,
                    response.completion_tokens,
                    price,
                )
                measurements.append(
                    Measurement(
                        run_id=run_id,
                        experiment_id=config.id,
                        model_slug=model.slug,
                        model_id=model_id,
                        task_id=task.id,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        output_words=word_count(response.content),
                        elapsed_ms=response.elapsed_ms,
                        cost=cost,
                    )
                )

        return measurements
