"""Tests for the JSON benchmark exporter."""

import json
from pathlib import Path
from typing import Any

import pytest

from llm_bench_data.calculations.compression import CompressionCalculator
from llm_bench_data.exporters.json import BenchmarkExporter
from llm_bench_data.storage.models import Measurement


def test_benchmark_exporter_aggregates_tokenizer_and_speed(tmp_path: object) -> None:
    """The JSON exporter produces a model-keyed artifact with tokenizer and speed stats."""
    measurements = [
        Measurement(
            run_id=1,
            experiment_id="tokenizer-efficiency",
            model_slug="deepseek-v4-flash",
            sample_id="code",
            prompt_tokens=600,
            completion_tokens=1,
            elapsed_ms=1000,
            meta={"sample_word_count": 300, "tokens_per_word": "2.0"},
        ),
        Measurement(
            run_id=1,
            experiment_id="speed",
            model_slug="deepseek-v4-flash",
            prompt_tokens=10,
            completion_tokens=100,
            elapsed_ms=1000,
        ),
    ]

    output = tmp_path / "benchmarks.json"
    BenchmarkExporter(measurements).to_path(output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert "last_updated" in data
    assert "models" in data
    model = data["models"]["deepseek-v4-flash"]
    assert model["tokenizer_efficiency"] == 2.0
    assert model["speed_tok_per_s"] == 100.0


def test_export_failure_leaves_destination_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing export keeps the previous file and leaves no temp artifact."""
    output = tmp_path / "benchmarks.json"
    output.write_text('{"previous": true}', encoding="utf-8")

    def _boom(_self: BenchmarkExporter) -> dict[str, Any]:
        raise RuntimeError("injected failure")

    monkeypatch.setattr(BenchmarkExporter, "_aggregate", _boom)

    with pytest.raises(RuntimeError):
        BenchmarkExporter([]).to_path(output)

    assert output.read_text(encoding="utf-8") == '{"previous": true}'
    assert not (tmp_path / "benchmarks.json.tmp").exists()


def test_export_success_atomically_replaces_destination(tmp_path: Path) -> None:
    """A successful export replaces the previous file and leaves no temp artifact."""
    output = tmp_path / "benchmarks.json"
    output.write_text("stale", encoding="utf-8")

    BenchmarkExporter([]).to_path(output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert "models" in data
    assert not (tmp_path / "benchmarks.json.tmp").exists()

def test_aggregate_verbosity_per_task(tmp_path: Path) -> None:
    """Verbosity measurements aggregate per task with token/word rollups."""
    measurements = [
        Measurement(
            run_id=1, experiment_id="output-verbosity", model_slug="m1",
            task_id="one-word", completion_tokens=10, output_words=3,
        ),
        Measurement(
            run_id=1, experiment_id="output-verbosity", model_slug="m1",
            task_id="one-word", completion_tokens=20, output_words=5,
        ),
        Measurement(
            run_id=1, experiment_id="output-verbosity", model_slug="m1",
            task_id="short-code", completion_tokens=30, output_words=6,
        ),
    ]

    output = tmp_path / "benchmarks.json"
    BenchmarkExporter(measurements).to_path(output)

    verbosity = json.loads(output.read_text(encoding="utf-8"))["models"]["m1"]["output_verbosity"]
    assert verbosity["total_calls"] == 3
    assert verbosity["avg_output_tokens"] == 20.0
    one_word = verbosity["per_task"]["one-word"]
    assert one_word["avg_tokens"] == 15.0
    assert one_word["max_tokens"] == 20
    assert one_word["min_tokens"] == 10
    assert one_word["avg_words"] == 4.0


def test_aggregate_compression_ratios(tmp_path: Path) -> None:
    """Compression ratios are computed against the per-task baseline; baseless rows are excluded."""
    measurements = [
        Measurement(
            run_id=1, experiment_id="compression", model_slug="m1",
            task_id="t1", method_id="none", completion_tokens=100,
        ),
        Measurement(
            run_id=1, experiment_id="compression", model_slug="m1",
            task_id="t1", method_id="smc", completion_tokens=40,
        ),
        Measurement(
            run_id=1, experiment_id="compression", model_slug="m1",
            task_id="t2", method_id="smc", completion_tokens=80,
        ),
    ]

    output = tmp_path / "benchmarks.json"
    BenchmarkExporter(measurements).to_path(output)

    compression = json.loads(output.read_text(encoding="utf-8"))["models"]["m1"]["compression"]
    assert compression["smc"] == pytest.approx(
        float(CompressionCalculator.compression_ratio(40, 100))
    )


def test_aggregate_thinking_ratio(tmp_path: Path) -> None:
    """Reasoning measurements yield a reasoning/completion ratio; non-reasoning yield 0.0."""
    measurements = [
        Measurement(
            run_id=1, experiment_id="appraisal", model_slug="m1",
            completion_tokens=200, reasoning_tokens=50, meta={"check": "reasoning"},
        ),
        Measurement(
            run_id=1, experiment_id="appraisal", model_slug="m2",
            completion_tokens=100, reasoning_tokens=0, meta={},
        ),
    ]

    output = tmp_path / "benchmarks.json"
    BenchmarkExporter(measurements).to_path(output)

    models = json.loads(output.read_text(encoding="utf-8"))["models"]
    assert models["m1"]["thinking_token_ratio"] == 0.25
    assert models["m2"]["thinking_token_ratio"] == 0.0


def test_aggregate_speed_skips_missing_elapsed(tmp_path: Path) -> None:
    """Speed aggregates average tokens/sec and skip rows without elapsed_ms."""
    measurements = [
        Measurement(
            run_id=1, experiment_id="speed", model_slug="m1",
            completion_tokens=100, elapsed_ms=1000,
        ),
        Measurement(
            run_id=1, experiment_id="speed", model_slug="m1",
            completion_tokens=200, elapsed_ms=1000,
        ),
        Measurement(
            run_id=1, experiment_id="speed", model_slug="m1",
            completion_tokens=50, elapsed_ms=None,
        ),
    ]

    output = tmp_path / "benchmarks.json"
    BenchmarkExporter(measurements).to_path(output)

    data = json.loads(output.read_text(encoding="utf-8"))
    speed = data["models"]["m1"]["speed_tok_per_s"]
    assert speed == 150.0
