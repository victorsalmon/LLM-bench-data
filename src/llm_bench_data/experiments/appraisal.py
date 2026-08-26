"""Single-model appraisal harness."""

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

REASONING_PROMPT = (
    "A bat and a ball cost $1.10. The bat costs $1.00 more than the ball. "
    "How much does the ball cost? Show your reasoning."
)


@register
class AppraisalExperiment(Experiment):
    """Appraise a single model across tokenizer efficiency, speed, and reasoning."""

    experiment_type = "appraisal"

    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Run tokenizer, speed, and reasoning checks for each configured model."""
        if run.id is None:
            raise ValueError("Run must be persisted before running an experiment")
        run_id = run.id
        measurements: list[Measurement] = []
        max_tokens = config.params.max_tokens or 20
        speed_max_tokens = 3300

        for model in catalog.resolve_model_refs(config.model_refs):
            model_key = client.model_id(model)
            price = pricing.get(model_key)

            for sample in catalog.resolve_sample_refs(config.sample_refs):
                text = sample.absolute_path(catalog.root_path).read_text(encoding="utf-8")
                response = client.chat(
                    ChatRequest(
                        model_id=model_key,
                        messages=[Message(role="user", content=text)],
                        max_tokens=max_tokens,
                    )
                )
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
                        model_id=model_key,
                        sample_id=sample.id,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        elapsed_ms=response.elapsed_ms,
                        cost=cost,
                        meta={
                            "sample_word_count": sample.word_count,
                            "tokens_per_word": str(
                                EfficiencyCalculator.tokens_per_word(
                                    response.prompt_tokens, sample.word_count
                                )
                            ),
                        },
                    )
                )

            speed_response = client.chat(
                ChatRequest(
                    model_id=model_key,
                    messages=[Message(role="user", content="Write numbers 1 to 200.")],
                    max_tokens=speed_max_tokens,
                )
            )
            measurements.append(
                Measurement(
                    run_id=run_id,
                    experiment_id=config.id,
                    model_slug=model.slug,
                    model_id=model_key,
                    prompt_tokens=speed_response.prompt_tokens,
                    completion_tokens=speed_response.completion_tokens,
                    elapsed_ms=speed_response.elapsed_ms,
                    cost=CostCalculator.compute(
                        speed_response.prompt_tokens,
                        speed_response.completion_tokens,
                        price,
                    ),
                    meta={"check": "speed"},
                )
            )

            reasoning_response = client.chat(
                ChatRequest(
                    model_id=model_key,
                    messages=[Message(role="user", content=REASONING_PROMPT)],
                    max_tokens=2000,
                )
            )
            measurements.append(
                Measurement(
                    run_id=run_id,
                    experiment_id=config.id,
                    model_slug=model.slug,
                    model_id=model_key,
                    prompt_tokens=reasoning_response.prompt_tokens,
                    completion_tokens=reasoning_response.completion_tokens,
                    reasoning_tokens=reasoning_response.reasoning_tokens,
                    elapsed_ms=reasoning_response.elapsed_ms,
                    cost=CostCalculator.compute(
                        reasoning_response.prompt_tokens,
                        reasoning_response.completion_tokens,
                        price,
                    ),
                    meta={"check": "reasoning"},
                )
            )

        return measurements
