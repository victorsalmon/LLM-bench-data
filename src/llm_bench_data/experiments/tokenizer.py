"""Tokenizer efficiency experiment."""

from llm_bench_data.calculations.cost import CostCalculator
from llm_bench_data.calculations.efficiency import EfficiencyCalculator
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
class TokenizerEfficiencyExperiment(Experiment):
    """Measure tokens per word for code, prose, and blended samples."""

    experiment_type = "tokenizer_efficiency"

    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Run the tokenizer-efficiency benchmark for all configured models and samples."""
        if run.id is None:
            raise ValueError("Run must be persisted before running an experiment")
        run_id = run.id
        measurements: list[Measurement] = []
        max_tokens = config.params.max_tokens or 20

        for model in catalog.resolve_model_refs(config.model_refs):
            for sample in catalog.resolve_sample_refs(config.sample_refs):
                text = sample.absolute_path(catalog.root_path).read_text(encoding="utf-8")
                model_id = client.model_id(model)
                request = ChatRequest(
                    model_id=model_id,
                    messages=[Message(role="user", content=text)],
                    max_tokens=max_tokens,
                )
                response = client.chat(request)
                price = pricing.get(model_id)
                cost = CostCalculator.compute(
                    response.prompt_tokens,
                    response.completion_tokens,
                    price,
                )
                tokens_per_word = EfficiencyCalculator.tokens_per_word(
                    response.prompt_tokens, sample.word_count
                )
                measurements.append(
                    Measurement(
                        run_id=run_id,
                        experiment_id=config.id,
                        model_slug=model.slug,
                        model_id=model_id,
                        sample_id=sample.id,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        elapsed_ms=response.elapsed_ms,
                        cost=cost,
                        meta={
                            "sample_word_count": sample.word_count,
                            "tokens_per_word": str(tokens_per_word),
                        },
                    )
                )

        return measurements
