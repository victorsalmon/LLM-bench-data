"""Database engine and session management."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from llm_bench_data.core.config import Settings
from llm_bench_data.core.exceptions import StorageError


def get_engine(database_url: str | None = None, settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine from a database URL or settings."""
    if database_url is None:
        if settings is None:
            settings = Settings()
        database_url = settings.database_url

    try:
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    except Exception as exc:
        raise StorageError(f"Could not create database engine: {exc}") from exc

    if database_url.startswith("sqlite"):
        busy_timeout_ms = settings.db_busy_timeout_ms if settings is not None else 5000

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn: Any, _record: Any) -> None:
            """Apply WAL and busy-timeout pragmas to every new SQLite connection."""
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
            cur.close()

    return engine


def init_db(engine: Engine) -> None:
    """Create all tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """Yield a SQLModel session and commit/rollback automatically."""
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
