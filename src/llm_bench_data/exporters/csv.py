"""CSV export for raw measurement rows."""

import csv
from pathlib import Path
from typing import Any, ClassVar

from llm_bench_data.exporters._io import atomic_write
from llm_bench_data.storage.models import Measurement


class CSVExporter:
    """Export Measurement rows to CSV."""

    BASE_COLUMNS: ClassVar[list[str]] = [
        "experiment_id",
        "run_id",
        "model_slug",
        "model_id",
        "task_id",
        "sample_id",
        "method_id",
        "status",
        "prompt_tokens",
        "completion_tokens",
        "output_words",
        "reasoning_tokens",
        "elapsed_ms",
        "cost",
        "error",
        "created_at",
    ]

    def __init__(self, measurements: list[Measurement]) -> None:
        """Initialize the exporter with a list of measurements."""
        self.measurements = measurements

    def _row(self, m: Measurement) -> dict[str, Any]:
        return {
            "experiment_id": m.experiment_id,
            "run_id": m.run_id,
            "model_slug": m.model_slug,
            "model_id": m.model_id,
            "task_id": m.task_id,
            "sample_id": m.sample_id,
            "method_id": m.method_id,
            "status": m.status,
            "prompt_tokens": m.prompt_tokens,
            "completion_tokens": m.completion_tokens,
            "output_words": m.output_words,
            "reasoning_tokens": m.reasoning_tokens,
            "elapsed_ms": m.elapsed_ms,
            "cost": m.cost,
            "error": m.error,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    def to_path(self, path: Path | str) -> None:
        """Write all measurements to *path* as CSV."""
        path = Path(path)
        with atomic_write(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self.BASE_COLUMNS)
            writer.writeheader()
            for measurement in self.measurements:
                writer.writerow(self._row(measurement))
