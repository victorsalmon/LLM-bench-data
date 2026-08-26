"""High-level repository for runs, measurements, and pricing snapshots."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.engine import Engine
from sqlmodel import select

from llm_bench_data.storage.models import ExperimentRun, Measurement, PricingSnapshot
from llm_bench_data.storage.session import get_session


class MeasurementRepository:
    """Persistence layer for benchmark measurements."""

    def __init__(self, engine: Engine) -> None:
        """Initialize the repository with a SQLAlchemy engine."""
        self.engine = engine

    def create_run(
        self,
        experiment_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> ExperimentRun:
        """Start a new experiment run."""
        with get_session(self.engine) as session:
            run = ExperimentRun(
                experiment_id=experiment_id,
                parameters=parameters or {},
                status="running",
            )
            session.add(run)
            session.flush()
            session.refresh(run)
            return run

    def finish_run(self, run_id: int, status: str, notes: str | None = None) -> ExperimentRun:
        """Mark a run as completed or failed."""
        with get_session(self.engine) as session:
            run = session.get(ExperimentRun, run_id)
            if run is None:
                raise ValueError(f"Run {run_id} not found")
            run.status = status
            run.finished_at = datetime.now(UTC).replace(tzinfo=None)
            run.notes = notes
            session.add(run)
            return run

    def add_measurement(self, measurement: Measurement) -> Measurement:
        """Persist a single measurement."""
        with get_session(self.engine) as session:
            session.add(measurement)
            session.flush()
            session.refresh(measurement)
            return measurement

    def add_measurements(self, measurements: Sequence[Measurement]) -> list[Measurement]:
        """Persist many measurements in one transaction."""
        with get_session(self.engine) as session:
            session.add_all(measurements)
            session.flush()
            for m in measurements:
                session.refresh(m)
            return list(measurements)

    def get_measurements(
        self,
        experiment_id: str | None = None,
        model_slug: str | None = None,
        run_id: int | None = None,
    ) -> list[Measurement]:
        """Fetch measurements with optional filters."""
        with get_session(self.engine) as session:
            query = select(Measurement)
            if experiment_id is not None:
                query = query.where(Measurement.experiment_id == experiment_id)
            if model_slug is not None:
                query = query.where(Measurement.model_slug == model_slug)
            if run_id is not None:
                query = query.where(Measurement.run_id == run_id)
            return list(session.exec(query).all())

    def save_pricing_snapshot(self, snapshot: PricingSnapshot) -> PricingSnapshot:
        """Persist a live-pricing observation."""
        with get_session(self.engine) as session:
            session.add(snapshot)
            session.flush()
            session.refresh(snapshot)
            return snapshot

    def get_latest_pricing(self, model_id: str) -> PricingSnapshot | None:
        """Return the most recent pricing snapshot for a model."""
        with get_session(self.engine) as session:
            query = (
                select(PricingSnapshot)
                .where(PricingSnapshot.model_id == model_id)
                .order_by(desc(PricingSnapshot.fetched_at))  # type: ignore[arg-type]
            )
            return session.exec(query).first()
