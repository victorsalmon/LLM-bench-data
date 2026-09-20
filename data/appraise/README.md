# data/appraise/

Per-model appraisal raw data. One CSV per appraisal, written by
`uv run llmcc appraise <slug>`, named `<slug>-<YYYY-MM-DD>.csv`.

This is distinct from the batch session CSVs in `../` (Session 5 / 6 / 6b) and
`../output-experiment/` — those are one-shot multi-model sweeps. This directory
is the landing zone for the **event-driven, single-model** Appraise-Model flow:
when a new model drops, one file lands here.

## CSV schema

The CSV is the raw `Measurement` export. Its columns are defined by the
`CSVExporter.BASE_COLUMNS` contract in
`src/llm_bench_data/exporters/csv.py` — link there rather than restating the
list here. Tokenizer rows carry `sample_id` (`code` / `prose` / `blended`); the
speed and reasoning rows leave it empty.

## Headline metrics

`uv run llmcc appraise <slug>` writes the raw rows and prints only a run
summary. The headline values are derived from those rows by the JSON exporter
(`BenchmarkExporter`, `uv run llmcc export --format json`):

- **tokenizer_efficiency** — mean tokens per word across the tokenizer samples
- **thinking_token_ratio** — `reasoning_tokens / completion_tokens` from the reasoning check
- **speed_tok_per_s** — from the speed check's completion tokens and elapsed time

Copy the values you want to keep into `models.json` under the appraised model's entry.
