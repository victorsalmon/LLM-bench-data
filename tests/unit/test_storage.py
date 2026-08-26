"""Tests for SQLModel storage and repository."""

import threading
from pathlib import Path

from sqlalchemy.exc import OperationalError

from llm_bench_data.storage.models import Measurement, PricingSnapshot
from llm_bench_data.storage.repository import MeasurementRepository
from llm_bench_data.storage.session import get_engine, init_db


def test_create_and_query_measurements() -> None:
    """Measurements can be persisted and retrieved by experiment and model."""
    engine = get_engine("sqlite://")
    init_db(engine)
    repo = MeasurementRepository(engine)

    run = repo.create_run("tokenizer-efficiency", {"max_tokens": 20})
    measurement = Measurement(
        run_id=run.id,
        experiment_id="tokenizer-efficiency",
        model_slug="deepseek-v4-flash",
        model_id="deepseek/deepseek-v4-flash",
        sample_id="code",
        prompt_tokens=612,
        completion_tokens=1,
        elapsed_ms=1200,
    )
    saved = repo.add_measurement(measurement)

    assert saved.id is not None
    assert saved.run_id == run.id

    rows = repo.get_measurements(experiment_id="tokenizer-efficiency")
    assert len(rows) == 1
    assert rows[0].model_slug == "deepseek-v4-flash"


def test_run_lifecycle() -> None:
    """Runs are created in 'running' status and can be completed."""
    engine = get_engine("sqlite://")
    init_db(engine)
    repo = MeasurementRepository(engine)

    run = repo.create_run("output-verbosity")
    assert run.status == "running"

    finished = repo.finish_run(run.id, "completed", "all good")
    assert finished.status == "completed"
    assert finished.finished_at is not None


def test_pricing_snapshot() -> None:
    """Pricing snapshots are stored and fetched by recency."""
    engine = get_engine("sqlite://")
    init_db(engine)
    repo = MeasurementRepository(engine)

    snapshot = PricingSnapshot(
        model_id="deepseek/deepseek-v4-flash",
        input="0.0938",
        output="0.1876",
        cached_read="0.01876",
        source="openrouter",
    )
    saved = repo.save_pricing_snapshot(snapshot)

    assert saved.id is not None
    latest = repo.get_latest_pricing("deepseek/deepseek-v4-flash")
    assert latest is not None
    assert latest.model_id == snapshot.model_id


def test_concurrent_writes_do_not_raise_lock_error(tmp_path: Path) -> None:
    """Concurrent writers against one DB file do not hit 'database is locked'."""
    engine = get_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    init_db(engine)
    repo = MeasurementRepository(engine)
    run = repo.create_run("concurrency-check")

    errors: list[BaseException] = []

    def _write(index: int) -> None:
        try:
            repo.add_measurement(
                Measurement(
                    run_id=run.id,
                    experiment_id="concurrency-check",
                    model_slug="deepseek-v4-flash",
                    model_id="deepseek/deepseek-v4-flash",
                    sample_id=f"sample-{index}",
                    prompt_tokens=100 + index,
                    completion_tokens=1,
                    elapsed_ms=100,
                )
            )
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lock_errors = [
        error
        for error in errors
        if isinstance(error, OperationalError) and "database is locked" in str(error)
    ]
    assert not lock_errors, f"concurrent writers raised lock errors: {lock_errors}"
    assert not errors, f"concurrent writers raised: {errors}"
    rows = repo.get_measurements(experiment_id="concurrency-check")
    assert len(rows) == 8
