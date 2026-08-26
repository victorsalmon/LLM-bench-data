# LLM Cost Comparison

A reproducible, testable benchmark pipeline for measuring LLM tokenizer efficiency, output verbosity, compression, speed, cost, and reasoning-token behavior.

## Quick start

```bash
# Install dependencies and create the virtual environment
uv sync --all-extras

# Copy the example environment file and add your provider key
cp .env.example .env
# edit .env

# See available commands
uv run llmcc --help

# Run the test suite
uv run pytest

# Validate an existing CSV for the Session 6b corruption signature
uv run llmcc validate data/experiment-session5-consolidated.csv

`llmcc validate` and `scripts/validate-data.py --strict` share the same corruption-signature thresholds; the CLI is the canonical implementation.

# Run an experiment through OpenRouter (default)
uv run llmcc run tokenizer-efficiency --dry-run

# Or use DeepInfra's OpenAI-compatible endpoint
DEEPINFRA_API_KEY=... uv run llmcc run tokenizer-efficiency --provider deepinfra

# Appraise a single model
uv run llmcc appraise deepseek-v4-flash

# Export measurements to CSV
uv run llmcc export out.csv --experiment-id tokenizer-efficiency

# Export site-facing benchmark artifact
uv run llmcc export benchmarks.json --experiment-id tokenizer-efficiency --format json

# Migrate a legacy Session 5 CSV into the database
uv run llmcc migrate-legacy data/experiment-session5-consolidated.csv session-5
```

## Development

```bash
# Run the test suite
uv run pytest

# Lint and typecheck
uv run ruff check .
uv run mypy src

# Run the CLI in dry-run mode
uv run llmcc run tokenizer-efficiency --dry-run
```

## Project layout

- `catalogs/` - YAML source of truth for models, tasks, samples, compression methods, experiments, tiers, and pricing sources.
- `src/llm_bench_data/` - Python package: CLI (`cli`), domain models (`core`), experiment harness (`experiments`), OpenRouter client (`clients`), calculations (`calculations`), storage (`storage`), validation (`validation`), and exporters (`exporters`).
- `tests/` - pytest suite with mocked API clients and in-memory SQLite databases.
- `data/` - legacy CSVs and new exports; also holds the generated SQLite database at the path named by `LLMCC_DATABASE_URL` (default `sqlite:///data/llm_bench_data.db`, gitignored).

See `ARCHITECTURE.md` for the design overview and migration notes.
