"""Tests for the Typer CLI."""

import pytest
import respx
from typer.testing import CliRunner

from llm_bench_data.cli.main import app
from llm_bench_data.storage.models import Measurement
from llm_bench_data.storage.repository import MeasurementRepository
from llm_bench_data.storage.session import get_engine, init_db

runner = CliRunner()


def test_run_dry_run() -> None:
    """The run command with --dry-run exits without calling APIs."""
    result = runner.invoke(
        app,
        ["run", "tokenizer-efficiency", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "Dry run" in result.stdout


def test_validate_detects_corruption(tmp_path: pytest.TempPathFactory) -> None:
    """validate flags the constant prompt_tokens corruption signature."""
    csv = tmp_path / "corrupt.csv"
    csv.write_text(
        "model_id,sample_type,method_id,prompt_tokens,output_tokens,status\n"
        "x,t1,m,100,5,success\n"
        "x,t1,m,100,5,success\n"
        "x,t1,m,100,5,success\n"
    )
    result = runner.invoke(app, ["validate", str(csv)])
    assert result.exit_code == 1
    assert "CORRUPTION" in result.stdout


def test_export_measurements(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """export writes measurements for a given run to CSV."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    db = tmp_path / "db.sqlite"
    engine = get_engine(f"sqlite:///{db}")
    init_db(engine)
    repo = MeasurementRepository(engine)
    run = repo.create_run("output-verbosity")
    repo.add_measurement(
        Measurement(
            run_id=run.id,
            experiment_id="output-verbosity",
            model_slug="deepseek-v4-flash",
            prompt_tokens=10,
            completion_tokens=5,
        )
    )

    output = tmp_path / "out.csv"
    result = runner.invoke(
        app,
        ["export", str(output), f"--db=sqlite:///{db}", f"--run-id={run.id}"],
    )
    assert result.exit_code == 0
    assert "Exported 1" in result.stdout
    assert output.exists()


def test_migrate_legacy(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """migrate-legacy imports Session 5 style rows into the database."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    db = tmp_path / "db.sqlite"
    csv = tmp_path / "legacy.csv"
    csv.write_text(
        "model_id,model_name,family,sample_type,word_count,prompt_tokens,output_tokens,tokens_per_word,status\n"
        "ai21/jamba-large-1.7,Jamba Large,ai21,prose,235,287,20,1.22,success\n"
    )

    result = runner.invoke(
        app,
        ["migrate-legacy", str(csv), "session-5", f"--db=sqlite:///{db}"],
    )
    assert result.exit_code == 0
    assert "Migrated 1" in result.stdout

    engine = get_engine(f"sqlite:///{db}")
    repo = MeasurementRepository(engine)
    rows = repo.get_measurements(experiment_id="session-5")
    assert len(rows) == 1
    assert rows[0].model_slug == "ai21/jamba-large-1.7"
    assert rows[0].prompt_tokens == 287


def test_migrate_legacy_warns_when_word_count_missing(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CSV that passes validate but lacks word_count migrates with a warning.

    word_count is optional per the shared column contract (Session 6/6b CSVs
    carry output_words instead), so validation must not reject the CSV — but
    migrate-legacy must surface the NULL output_words impact on the
    benchmarks aggregates instead of importing it silently.
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    db = tmp_path / "db.sqlite"
    csv = tmp_path / "no-word-count.csv"
    csv.write_text(
        "model_id,sample_type,prompt_tokens,output_tokens,status\n"
        "x,t1,100,5,success\n"
        "x,t2,120,6,success\n"
    )

    validate_result = runner.invoke(app, ["validate", str(csv), "--strict"])
    assert validate_result.exit_code == 0
    assert "No corruption signatures detected." in validate_result.stdout

    migrate_result = runner.invoke(
        app,
        ["migrate-legacy", str(csv), "session-5", f"--db=sqlite:///{db}"],
    )
    assert migrate_result.exit_code == 0
    assert "Migrated 2" in migrate_result.stdout
    assert "2 rows lacked 'word_count'" in migrate_result.stderr
    assert "tokenizer-efficiency" in migrate_result.stderr

    engine = get_engine(f"sqlite:///{db}")
    repo = MeasurementRepository(engine)
    rows = repo.get_measurements(experiment_id="session-5")
    assert len(rows) == 2
    assert all(row.output_words is None for row in rows)


def test_appraise_writes_csv(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """appraise runs the full pipeline and writes a CSV file."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    db = tmp_path / "db.sqlite"
    output = tmp_path / "deepseek-v4-flash-2026-07-21.csv"
    payload = {
        "model": "deepseek/deepseek-v4-flash",
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 5,
            "total_tokens": 105,
        },
    }

    with respx.mock:
        respx.post("https://openrouter.ai/api/v1/chat/completions").respond(200, json=payload)
        result = runner.invoke(
            app,
            [
                "appraise",
                "deepseek-v4-flash",
                f"--db=sqlite:///{db}",
                f"--output={output}",
            ],
        )

    assert result.exit_code == 0, result.stdout
    assert output.exists()
    assert output.read_text(encoding="utf-8").startswith("experiment_id,")
