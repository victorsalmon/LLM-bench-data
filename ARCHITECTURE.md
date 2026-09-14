# Architecture

This document describes the modular Python redesign of the LLM Cost Comparison pipeline.

## Design goals

- **Reproducible**: every experiment is declared in YAML catalog files.
- **Testable**: all network and storage boundaries are abstracted and unit-tested.
- **Composable**: experiments, clients, storage, validation, and export are independent packages.
- **Site-ready**: measurements can be aggregated into a `benchmarks.json` v2 artifact.

## Package layout

```
src/llm_bench_data/
├── cli/           # Typer CLI (run, appraise, validate, export, migrate-legacy)
├── clients/       # LLMClient base, OpenRouterClient with retries, PricingService
├── core/          # Pydantic domain models, YAML catalog loader, Settings, exceptions
├── experiments/   # Experiment base/Runner and concrete experiment types
├── calculations/  # Cost, efficiency, compression ratio math
├── storage/       # SQLModel tables, session, and MeasurementRepository
├── validation/    # Measurement validators and legacy CSV corruption checks
└── exporters/     # CSV and JSON (benchmarks.json) exporters
```

## Catalog-driven experiments

All experiments are configured in `catalogs/experiments.yaml` and resolved through `Catalog`:

- `tokenizer_efficiency` measures tokens per word for code/prose/blended samples.
- `output_verbosity` measures token usage per task.
- `compression` compares a baseline prompt to system-prompt compression methods.
- `speed` measures tokens per second for a fixed generation prompt.
- `appraisal` runs tokenizer + speed + reasoning checks for a single model.

The `ExperimentRunner` creates an `ExperimentRun`, calls `Experiment.run`, persists `Measurement` rows, and marks the run complete or failed.

### Model-data files: catalog vs site artifact

The repo has **two model databases with different schemas** — they are not interchangeable:

- `catalogs/*.yaml` (e.g. `catalogs/models.yaml`, 49 entries) — the **CLI/experiment source of truth**, loaded by `Catalog` (`core/models.py`). Fields: `slug`, `name`, `family`, `tier`, `pricing: {zen: {input/output/cached_read}}`, `pricing_source`, `openrouter_id`, `max_variants`. No benchmarks, no speed/thinking fields.
- `models.json` — the **site-facing canonical DB** for the website's Benchmarks sub-blog; hand-edited per `SKILL.md` step 4. Keys: `zen_pricing`, `openrouter_pricing`, `benchmarks`, `speed_tok_per_s`, `thinking_token_ratio`, `tokenizer_efficiency`, `output_verbosity`.

**Relationship**: the CLI never reads `models.json` (zero references in `src/`/`scripts/`). Live measurements are exported from the SQLite DB by `llmcc export --format json` (`BenchmarkExporter`) into a `benchmarks.json` artifact; `models.json` is a curated hand-edited superset maintained alongside it.

**Field-name mapping**: `catalog pricing.zen` ↔ `models.json zen_pricing`; `pricing.openrouter` ↔ `openrouter_pricing`; `benchmarks`/`speed_tok_per_s`/`thinking_token_ratio`/`tokenizer_efficiency`/`output_verbosity` are **not** catalog fields — they exist only in `models.json`.

## Storage model

Three SQLModel tables:

- `ExperimentRun` - a single execution of an experiment configuration.
- `Measurement` - one raw or derived measurement row (tokens, words, elapsed time, cost).
- `PricingSnapshot` - cached live-pricing observation from OpenRouter.

## CLI commands

- `llmcc run <experiment-id>` - run a configured experiment.
- `llmcc appraise <model-slug>` - run the appraisal pipeline for one model.
- `llmcc validate <csv>` - detect Session 6b corruption signatures.
- `llmcc export <path> --run-id/--experiment-id [--format csv|json]` - export measurements.
- `llmcc migrate-legacy <csv> <experiment-id>` - import legacy Session 5/6 CSV rows.

## Legacy migration

The original PowerShell measurement and enrichment scripts have been removed. The Python CLI (`llmcc`) now covers tokenizer efficiency, output verbosity, compression, speed, and per-model appraisal. The remaining `scripts/` helpers are: `validate-data.py` (used by `commit-data.sh`) and `commit-data.sh` itself for the data-commit protocol; plus the Session 6b data-cleanup utilities `analyze-s6b.py`, `close-gaps-s6b-rerun.py`, and `merge-s6b-clean.py`; and the weekly speed benchmark `speed-weekly.py` with its scheduled-task installer `install-speed-weekly-scheduled-task.ps1`.
