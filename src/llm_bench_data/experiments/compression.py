"""Compression experiment."""

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
from llm_bench_data.experiments.utils import word_count
from llm_bench_data.storage.models import ExperimentRun, Measurement


@register
class CompressionExperiment(Experiment):
    """Measure token savings for output-compression methods."""

    experiment_type = "compression"

    def _call(
        self,
        model_id: str,
        task_prompt: str,
        max_tokens: int,
        client: LLMClient,
        system_prompt: str | None = None,
    ) -> tuple[int, int, int, str]:
        """Send one request and return prompt, completion, elapsed, and content."""
        messages: list[Message] = []
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        messages.append(Message(role="user", content=task_prompt))
        response = client.chat(
            ChatRequest(model_id=model_id, messages=messages, max_tokens=max_tokens)
        )
        return (
            response.prompt_tokens,
            response.completion_tokens,
            response.elapsed_ms,
            response.content,
        )

    def run(
        self,
        config: ExperimentConfig,
        catalog: Catalog,
        client: LLMClient,
        run: ExperimentRun,
        pricing: dict[str, ProviderPricing],
    ) -> list[Measurement]:
        """Run compression methods against an uncompressed baseline per task."""
        if run.id is None:
            raise ValueError("Run must be persisted before running an experiment")
        run_id = run.id
        measurements: list[Measurement] = []
        max_tokens = config.params.max_tokens or 4096

        for model in catalog.resolve_model_refs(config.model_refs):
            model_key = client.model_id(model)
            for task in catalog.resolve_task_refs(config.task_refs):
                baseline_pt, baseline_ct, baseline_ms, baseline_content = self._call(
                    model_key,
                    task.prompt,
                    task.max_tokens or max_tokens,
                    client,
                )
                price = pricing.get(model_key)
                baseline_cost = CostCalculator.compute(baseline_pt, baseline_ct, price)
                measurements.append(
                    Measurement(
                        run_id=run_id,
                        experiment_id=config.id,
                        model_slug=model.slug,
                        model_id=model_key,
                        task_id=task.id,
                        method_id="none",
                        prompt_tokens=baseline_pt,
                        completion_tokens=baseline_ct,
                        output_words=word_count(baseline_content),
                        elapsed_ms=baseline_ms,
                        cost=baseline_cost,
                    )
                )

                for method in catalog.resolve_method_refs(config.method_refs):
                    pt, ct, ms, content = self._call(
                        model_key,
                        task.prompt,
                        task.max_tokens or max_tokens,
                        client,
                        system_prompt=method.system_prompt,
                    )
                    cost = CostCalculator.compute(pt, ct, price)
                    measurements.append(
                        Measurement(
                            run_id=run_id,
                            experiment_id=config.id,
                            model_slug=model.slug,
                            model_id=model_key,
                            task_id=task.id,
                            method_id=method.id,
                            prompt_tokens=pt,
                            completion_tokens=ct,
                            output_words=word_count(content),
                            elapsed_ms=ms,
                            cost=cost,
                            meta={"baseline_tokens": baseline_ct},
                        )
                    )

        return measurements
