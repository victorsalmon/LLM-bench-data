"""Tests for the experiment harness and concrete experiment types."""

from decimal import Decimal

from llm_bench_data.clients.base import LLMClient
from llm_bench_data.core.catalog import load_catalog
from llm_bench_data.core.models import (
    ChatRequest,
    ChatResponse,
    ExperimentConfig,
    ExperimentParams,
    ProviderPricing,
)
from llm_bench_data.experiments import create_runner
from llm_bench_data.storage.repository import MeasurementRepository
from llm_bench_data.storage.session import get_engine, init_db


class FakeClient(LLMClient):
    """Deterministic in-memory LLM client for unit tests."""

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Return a fake response with deterministic token counts."""
        text = request.messages[-1].content
        return ChatResponse(
            model_id=request.model_id,
            content=f"response to {text[:20]}",
            prompt_tokens=len(text.split()),
            completion_tokens=5,
            elapsed_ms=100,
        )

    def close(self) -> None:
        """No-op for the fake client."""


def _custom_catalog(base: object, experiment: ExperimentConfig) -> object:
    """Return a catalog copy with a single test experiment."""
    return base.model_copy(update={"experiments": [experiment]})


def _make_runner(catalog: object) -> tuple[object, MeasurementRepository]:
    """Create an in-memory repository and experiment runner."""
    engine = get_engine("sqlite://")
    init_db(engine)
    repository = MeasurementRepository(engine)
    return create_runner(catalog, FakeClient(), repository), repository


def test_tokenizer_efficiency_experiment() -> None:
    """The tokenizer efficiency experiment produces one measurement per model/sample pair."""
    catalog = load_catalog("catalogs")
    experiment = ExperimentConfig(
        id="test-tokenizer",
        type="tokenizer_efficiency",
        model_refs=["deepseek-v4-flash"],
        sample_refs=["code"],
        params=ExperimentParams(max_tokens=20),
    )
    custom = _custom_catalog(catalog, experiment)
    runner, repo = _make_runner(custom)

    pricing = {
        "deepseek/deepseek-v4-flash": ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    }
    run = runner.run_experiment("test-tokenizer", pricing=pricing)

    measurements = repo.get_measurements(run_id=run.id)
    assert len(measurements) == 1
    assert measurements[0].model_slug == "deepseek-v4-flash"
    assert measurements[0].sample_id == "code"
    assert measurements[0].prompt_tokens > 0
    assert measurements[0].cost is not None


def test_output_verbosity_experiment() -> None:
    """The output verbosity experiment produces one measurement per model/task pair."""
    catalog = load_catalog("catalogs")
    experiment = ExperimentConfig(
        id="test-verbosity",
        type="output_verbosity",
        model_refs=["deepseek-v4-flash"],
        task_refs=["one-word"],
        params=ExperimentParams(max_tokens=80),
    )
    custom = _custom_catalog(catalog, experiment)
    runner, repo = _make_runner(custom)

    pricing = {
        "deepseek/deepseek-v4-flash": ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    }
    run = runner.run_experiment("test-verbosity", pricing=pricing)

    measurements = repo.get_measurements(run_id=run.id)
    assert len(measurements) == 1
    assert measurements[0].task_id == "one-word"
    assert measurements[0].completion_tokens == 5


def test_compression_experiment() -> None:
    """The compression experiment stores a baseline plus one row per method."""
    catalog = load_catalog("catalogs")
    experiment = ExperimentConfig(
        id="test-compression",
        type="compression",
        model_refs=["deepseek-v4-flash"],
        task_refs=["one-word"],
        method_refs=["smc"],
        params=ExperimentParams(max_tokens=80),
    )
    custom = _custom_catalog(catalog, experiment)
    runner, repo = _make_runner(custom)

    pricing = {
        "deepseek/deepseek-v4-flash": ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    }
    run = runner.run_experiment("test-compression", pricing=pricing)

    measurements = repo.get_measurements(run_id=run.id)
    methods = {m.method_id for m in measurements}
    assert methods == {"none", "smc"}
    assert all(m.task_id == "one-word" for m in measurements)


def test_speed_experiment() -> None:
    """The speed experiment stores a tokens-per-second observation."""
    catalog = load_catalog("catalogs")
    experiment = ExperimentConfig(
        id="test-speed",
        type="speed",
        model_refs=["deepseek-v4-flash"],
        params=ExperimentParams(prompt="count to ten", max_tokens=100),
    )
    custom = _custom_catalog(catalog, experiment)
    runner, repo = _make_runner(custom)

    pricing = {
        "deepseek/deepseek-v4-flash": ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    }
    run = runner.run_experiment("test-speed", pricing=pricing)

    measurements = repo.get_measurements(run_id=run.id)
    assert len(measurements) == 1
    assert measurements[0].completion_tokens == 5


def test_appraisal_experiment() -> None:
    """The appraisal experiment runs tokenizer, speed, and reasoning checks."""
    catalog = load_catalog("catalogs")
    experiment = ExperimentConfig(
        id="test-appraisal",
        type="appraisal",
        model_refs=["deepseek-v4-flash"],
        sample_refs=["code"],
        params=ExperimentParams(max_tokens=20),
    )
    custom = _custom_catalog(catalog, experiment)
    runner, repo = _make_runner(custom)

    pricing = {
        "deepseek/deepseek-v4-flash": ProviderPricing(input=Decimal("0.14"), output=Decimal("0.28"))
    }
    run = runner.run_experiment("test-appraisal", pricing=pricing)

    measurements = repo.get_measurements(run_id=run.id)
    checks = {m.meta.get("check") for m in measurements if m.meta}
    assert "speed" in checks
    assert "reasoning" in checks
    assert any(m.sample_id == "code" for m in measurements)
