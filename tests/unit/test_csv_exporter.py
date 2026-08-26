"""Tests for the CSV exporter."""

from pathlib import Path
from typing import Any

import pytest

from llm_bench_data.exporters.csv import CSVExporter
from llm_bench_data.storage.models import Measurement


def _measurement() -> Measurement:
    """Build a minimal measurement row."""
    return Measurement(
        run_id=1,
        experiment_id="tokenizer-efficiency",
        model_slug="deepseek-v4-flash",
        model_id="deepseek/deepseek-v4-flash",
        sample_id="code",
        prompt_tokens=612,
        completion_tokens=1,
        elapsed_ms=1200,
    )


def test_csv_exporter_writes_header_and_rows(tmp_path: Path) -> None:
    """The CSV exporter writes a header row plus one row per measurement."""
    output = tmp_path / "out.csv"

    CSVExporter([_measurement()]).to_path(output)

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == (
        "experiment_id,run_id,model_slug,model_id,task_id,sample_id,method_id,status,"
        "prompt_tokens,completion_tokens,output_words,reasoning_tokens,elapsed_ms,cost,"
        "error,created_at"
    )
    assert len(lines) == 2
    assert "deepseek-v4-flash" in lines[1]


def test_csv_export_failure_leaves_destination_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing CSV write keeps the previous file and leaves no temp artifact."""
    output = tmp_path / "out.csv"
    output.write_text("previous", encoding="utf-8")

    def _boom(_row: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("injected failure")

    exporter = CSVExporter([_measurement()])
    monkeypatch.setattr(exporter, "_row", _boom)

    with pytest.raises(RuntimeError):
        exporter.to_path(output)

    assert output.read_text(encoding="utf-8") == "previous"
    assert not (tmp_path / "out.csv.tmp").exists()


def test_csv_export_success_atomically_replaces_destination(tmp_path: Path) -> None:
    """A successful CSV export replaces the previous file and leaves no temp artifact."""
    output = tmp_path / "out.csv"
    output.write_text("stale", encoding="utf-8")

    CSVExporter([_measurement()]).to_path(output)

    assert output.read_text(encoding="utf-8").startswith("experiment_id,")
    assert not (tmp_path / "out.csv.tmp").exists()
