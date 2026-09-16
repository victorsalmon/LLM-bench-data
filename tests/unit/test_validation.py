"""Tests for validators and legacy CSV corruption checks."""

import csv
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from llm_bench_data.core.models import ChatResponse
from llm_bench_data.storage.models import Measurement
from llm_bench_data.validation.legacy import (
    find_constant_prompt_tokens,
    find_empty_required_values,
    find_task_id_leaking_method_names,
    validate_csv_signature,
)
from llm_bench_data.validation.validators import MeasurementValidator, ResponseValidator


def test_valid_measurement() -> None:
    """A success measurement with valid token counts passes."""
    measurement = Measurement(
        run_id=1,
        experiment_id="tokenizer-efficiency",
        model_slug="deepseek-v4-flash",
        prompt_tokens=100,
        completion_tokens=50,
        elapsed_ms=1200,
        status="success",
    )
    assert MeasurementValidator.validate(measurement) == []


def test_missing_model_slug() -> None:
    """Missing model_slug is rejected."""
    measurement = Measurement(
        run_id=1,
        experiment_id="output-verbosity",
        model_slug="",
        prompt_tokens=10,
        completion_tokens=5,
        status="success",
    )
    errors = MeasurementValidator.validate(measurement)
    assert any("model_slug" in e for e in errors)


def test_negative_tokens() -> None:
    """Negative token counts on success rows are rejected."""
    measurement = Measurement(
        run_id=1,
        experiment_id="output-verbosity",
        model_slug="x",
        prompt_tokens=-1,
        completion_tokens=5,
        status="success",
    )
    errors = MeasurementValidator.validate(measurement)
    assert any("prompt_tokens" in e for e in errors)


def test_constant_prompt_tokens_signature() -> None:
    """Constant prompt_tokens within a variance group is flagged as corruption."""
    rows = [
        {"model_id": "a", "task_id": "t1", "method_id": "smc", "prompt_tokens": 100},
        {"model_id": "a", "task_id": "t1", "method_id": "smc", "prompt_tokens": 100},
        {"model_id": "a", "task_id": "t1", "method_id": "smc", "prompt_tokens": 100},
    ]
    result = find_constant_prompt_tokens(rows, ["model_id", "task_id", "method_id"])
    assert len(result) == 1
    assert result[0][1] == 1


def test_task_id_leaking_method_names() -> None:
    """task_id values matching method names are flagged."""
    rows = [
        {"task_id": "smc"},
        {"task_id": "short-code"},
    ]
    leaked = find_task_id_leaking_method_names(
        rows, "task_id", {"smc", "diff-only"}, {"short-code", "one-word"}
    )
    assert leaked == ["smc"]


def test_empty_required_values() -> None:
    """Empty required columns on success rows are counted."""
    rows = [
        {"status": "success", "category": "coding"},
        {"status": "success", "category": ""},
        {"status": "error", "category": ""},
    ]
    assert find_empty_required_values(rows, "category") == 1


def test_validate_csv_signature_integration() -> None:
    """validate_csv_signature returns errors and warnings together."""
    rows = [
        {"task_id": "smc", "prompt_tokens": 100, "category": "x", "status": "success"},
        {"task_id": "smc", "prompt_tokens": 100, "category": "", "status": "success"},
        {"task_id": "smc", "prompt_tokens": 100, "category": "x", "status": "success"},
    ]
    errors, warnings = validate_csv_signature(
        rows,
        variance_groups=["task_id"],
        task_col="task_id",
        method_names={"smc"},
        known_tasks={"one-word"},
        required_cols=["category"],
    )
    assert any("CORRUPTION" in e for e in errors)
    assert any("task_id contains method" in e for e in errors)
    assert any("empty 'category'" in w for w in warnings)


def test_response_validator_rejects_negative_tokens() -> None:
    """A ChatResponse with negative token counts is flagged."""
    response = ChatResponse(
        model_id="deepseek-v4-flash",
        content="c",
        prompt_tokens=-1,
        completion_tokens=5,
        elapsed_ms=10,
    )
    errors = ResponseValidator.validate(response)
    assert any("token counts" in e for e in errors)


def test_response_validator_rejects_negative_elapsed() -> None:
    """A ChatResponse with negative elapsed_ms is flagged."""
    response = ChatResponse(
        model_id="deepseek-v4-flash",
        content="c",
        prompt_tokens=1,
        completion_tokens=5,
        elapsed_ms=-3,
    )
    errors = ResponseValidator.validate(response)
    assert any("elapsed_ms" in e for e in errors)


def test_response_validator_accepts_valid_response() -> None:
    """A valid ChatResponse passes validation."""
    response = ChatResponse(
        model_id="deepseek-v4-flash",
        content="c",
        prompt_tokens=10,
        completion_tokens=5,
        elapsed_ms=100,
    )
    assert ResponseValidator.validate(response) == []


def test_measurement_multiple_violations_reported() -> None:
    """A row with several simultaneous violations reports all of them."""
    measurement = Measurement(
        run_id=1,
        experiment_id="output-verbosity",
        model_slug="",
        prompt_tokens=-1,
        completion_tokens=5,
        elapsed_ms=-4,
        status="success",
    )
    errors = MeasurementValidator.validate(measurement)
    assert any("model_slug" in e for e in errors)
    assert any("prompt_tokens" in e for e in errors)
    assert any("elapsed_ms" in e for e in errors)


def test_negative_cost_rejected() -> None:
    """A success row with negative cost is rejected."""
    measurement = Measurement(
        run_id=1,
        experiment_id="output-verbosity",
        model_slug="x",
        prompt_tokens=10,
        completion_tokens=5,
        status="success",
        cost=Decimal("-0.01"),
    )
    errors = MeasurementValidator.validate(measurement)
    assert any("cost" in e for e in errors)


def _write_compression_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a compression-shaped CSV for the validate-data.py gate."""
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["model_id", "task_id", "method_id", "prompt_tokens"]
        )
        writer.writeheader()
        writer.writerows(rows)


def test_validate_data_py_and_llmcc_validate_agree(tmp_path: Path) -> None:
    """The commit gate and llmcc validate flag the same corruption signature."""
    repo_root = Path(__file__).resolve().parents[2]
    corrupt_rows = [
        {"model_id": "m1", "task_id": "t1", "method_id": "smc", "prompt_tokens": "100"},
    ] * 5
    clean_rows = [
        {"model_id": "m1", "task_id": "t1", "method_id": "smc", "prompt_tokens": str(90 + i)}
        for i in range(5)
    ]

    corrupt_path = tmp_path / "corrupt.csv"
    clean_path = tmp_path / "clean.csv"
    _write_compression_csv(corrupt_path, corrupt_rows)
    _write_compression_csv(clean_path, clean_rows)

    corrupt_script = subprocess.run(
        [sys.executable, "scripts/validate-data.py", str(corrupt_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    clean_script = subprocess.run(
        [sys.executable, "scripts/validate-data.py", str(clean_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    corrupt_legacy = validate_csv_signature(corrupt_rows, variance_groups=("model_id", "method_id"))
    clean_legacy = validate_csv_signature(clean_rows, variance_groups=("model_id", "method_id"))

    assert corrupt_script.returncode != 0
    assert "CORRUPTION SIGNATURE" in corrupt_script.stdout
    assert any("CORRUPTION" in e for e in corrupt_legacy[0])

    assert clean_script.returncode == 0
    assert not any("CORRUPTION" in e for e in clean_legacy[0])


def _write_model_id_prompt_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a model_id + prompt_tokens CSV (the validate-data.py fallback shape)."""
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["model_id", "prompt_tokens", "status"])
        writer.writeheader()
        writer.writerows(rows)


def test_constant_prompt_tokens_per_model_id_rejected(tmp_path: Path) -> None:
    """A2 regression: one prompt_tokens value repeated per model_id is rejected.

    Emulates the A2 speed-CSV shape (model_id + prompt_tokens, no task/method
    columns), which validate-data.py classifies via its content fallback and
    groups by model_id.
    """
    repo_root = Path(__file__).resolve().parents[2]
    corrupt_rows = [
        {"model_id": "m1", "prompt_tokens": "19", "status": "success"},
    ] * 5

    corrupt_path = tmp_path / "constant-per-model.csv"
    _write_model_id_prompt_csv(corrupt_path, corrupt_rows)

    result = subprocess.run(
        [sys.executable, "scripts/validate-data.py", str(corrupt_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "CORRUPTION SIGNATURE" in result.stdout

    errors, _ = validate_csv_signature(corrupt_rows, variance_groups=["model_id"])
    assert any("CORRUPTION" in e for e in errors)
