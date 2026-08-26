"""Experiment implementations and runner factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_bench_data.experiments.appraisal import AppraisalExperiment
from llm_bench_data.experiments.base import REGISTRY, Experiment, ExperimentRunner, register
from llm_bench_data.experiments.compression import CompressionExperiment
from llm_bench_data.experiments.output_verbosity import OutputVerbosityExperiment
from llm_bench_data.experiments.speed import SpeedExperiment
from llm_bench_data.experiments.tokenizer import TokenizerEfficiencyExperiment

if TYPE_CHECKING:
    from llm_bench_data.clients.base import LLMClient
    from llm_bench_data.core.models import Catalog
    from llm_bench_data.storage.repository import MeasurementRepository

__all__ = [
    "REGISTRY",
    "AppraisalExperiment",
    "CompressionExperiment",
    "Experiment",
    "ExperimentRunner",
    "OutputVerbosityExperiment",
    "SpeedExperiment",
    "TokenizerEfficiencyExperiment",
    "register",
]


def create_runner(
    catalog: Catalog,
    client: LLMClient,
    repository: MeasurementRepository,
) -> ExperimentRunner:
    """Return a runner with all built-in experiments pre-registered."""
    return ExperimentRunner(catalog, client, repository)
