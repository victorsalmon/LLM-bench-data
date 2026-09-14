"""JSON exporter that builds a site-facing benchmarks artifact."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from llm_bench_data.calculations.compression import CompressionCalculator
from llm_bench_data.calculations.efficiency import EfficiencyCalculator
from llm_bench_data.exporters._io import atomic_write
from llm_bench_data.storage.models import Measurement


class BenchmarkExporter:
    """Aggregate Measurement rows into a benchmarks.json v2 artifact."""

    def __init__(self, measurements: list[Measurement]) -> None:
        """Initialize the exporter with a list of measurements."""
        self.measurements = measurements

    @staticmethod
    def _tokens_per_second(measurement: Measurement) -> Decimal | None:
        """Compute tokens per second from elapsed time."""
        if not measurement.elapsed_ms:
            return None
        completion = measurement.completion_tokens or 0
        return Decimal(completion) * 1000 / Decimal(measurement.elapsed_ms)

    def _aggregate(self) -> dict[str, Any]:
        """Group measurements by model and experiment, then compute summary stats."""
        by_model: dict[str, dict[str, list[Measurement]]] = defaultdict(lambda: defaultdict(list))
        for measurement in self.measurements:
            by_model[measurement.model_slug][measurement.experiment_id].append(measurement)

        result: dict[str, Any] = {
            "last_updated": datetime.now(UTC).isoformat(),
            "models": {},
        }
        for slug, experiments in by_model.items():
            model_entry: dict[str, Any] = {}
            tokenizer_measurements: list[Measurement] = []

            for experiment_id, rows in experiments.items():
                if "tokenizer" in experiment_id:
                    tokenizer_measurements.extend(rows)
                elif "verbosity" in experiment_id:
                    model_entry["output_verbosity"] = self._aggregate_verbosity(rows)
                elif "compression" in experiment_id:
                    model_entry["compression"] = self._aggregate_compression(rows)
                elif "speed" in experiment_id:
                    model_entry["speed_tok_per_s"] = self._aggregate_speed(rows)
                elif "appraisal" in experiment_id:
                    model_entry["thinking_token_ratio"] = self._aggregate_thinking(rows)

            if tokenizer_measurements:
                model_entry["tokenizer_efficiency"] = self._aggregate_tokenizer(
                    tokenizer_measurements
                )

            result["models"][slug] = model_entry

        return result

    def _aggregate_tokenizer(self, rows: list[Measurement]) -> float:
        """Average tokens per word across tokenizer-efficiency measurements."""
        ratios: list[Decimal] = []
        for measurement in rows:
            word_count: int | None = None
            if measurement.meta:
                word_count = measurement.meta.get("sample_word_count")
            if word_count is None:
                word_count = measurement.output_words
            if word_count and measurement.prompt_tokens is not None:
                ratios.append(
                    EfficiencyCalculator.tokens_per_word(measurement.prompt_tokens, word_count)
                )
        if not ratios:
            return 0.0
        return float(sum(ratios) / len(ratios))

    def _aggregate_verbosity(self, rows: list[Measurement]) -> dict[str, Any]:
        """Aggregate output-verbosity measurements by task."""
        per_task: dict[str, list[Measurement]] = defaultdict(list)
        all_tokens: list[int] = []
        all_words: list[int] = []
        for measurement in rows:
            per_task[measurement.task_id or "unknown"].append(measurement)
            if measurement.completion_tokens is not None:
                all_tokens.append(measurement.completion_tokens)
            all_words.append(measurement.output_words or 0)

        tasks: dict[str, dict[str, float]] = {}
        for task_id, task_rows in per_task.items():
            tokens = [m.completion_tokens for m in task_rows if m.completion_tokens is not None]
            words = [m.output_words or 0 for m in task_rows]
            tasks[task_id] = {
                "avg_tokens": sum(tokens) / len(tokens) if tokens else 0.0,
                "max_tokens": max(tokens) if tokens else 0,
                "min_tokens": min(tokens) if tokens else 0,
                "avg_words": sum(words) / len(words) if words else 0.0,
            }

        return {
            "total_calls": len(rows),
            "avg_output_tokens": sum(all_tokens) / len(all_tokens) if all_tokens else 0.0,
            "avg_words_per_call": sum(all_words) / len(all_words) if all_words else 0.0,
            "per_task": tasks,
        }

    def _aggregate_compression(self, rows: list[Measurement]) -> dict[str, float]:
        """Average compression ratio per method across all tasks."""
        baselines = {m.task_id: m for m in rows if m.method_id == "none"}
        by_method: dict[str, list[Decimal]] = defaultdict(list)
        for measurement in rows:
            if measurement.method_id == "none" or measurement.method_id is None:
                continue
            baseline = baselines.get(measurement.task_id)
            if baseline and baseline.completion_tokens:
                ratio = CompressionCalculator.compression_ratio(
                    measurement.completion_tokens or 0,
                    baseline.completion_tokens,
                )
                by_method[measurement.method_id].append(ratio)

        return {
            method_id: float(sum(ratios) / len(ratios))
            for method_id, ratios in by_method.items()
            if ratios
        }

    def _aggregate_speed(self, rows: list[Measurement]) -> float:
        """Average tokens per second for speed measurements."""
        speeds = [tps for m in rows if (tps := self._tokens_per_second(m)) is not None]
        if not speeds:
            return 0.0
        return float(sum(speeds) / len(speeds))

    def _aggregate_thinking(self, rows: list[Measurement]) -> float:
        """Compute a reasoning-token ratio from appraisal reasoning checks."""
        for measurement in rows:
            if measurement.meta and measurement.meta.get("check") == "reasoning":
                completion = measurement.completion_tokens or 0
                reasoning = measurement.reasoning_tokens or 0
                if completion:
                    return reasoning / completion
        return 0.0

    def to_path(self, path: Path | str) -> None:
        """Write the aggregated benchmarks artifact to *path*."""
        path = Path(path)
        with atomic_write(path, "w", encoding="utf-8") as fh:
            json.dump(self._aggregate(), fh, indent=2, default=str)
