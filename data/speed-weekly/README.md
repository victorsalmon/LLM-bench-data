# Weekly Speed Consistency Benchmark

This directory holds the configuration and time-of-day CSVs for the weekly
LLM speed benchmark.

## Purpose

Measure tokens/second for a small, fixed coding task once every 3 hours for
24 hours, once per week (8 rounds total). The goal is **consistency**: detecting
which endpoints slow down at which times, not producing a perfect absolute speed
number.

A model can be benchmarked across multiple providers (OpenRouter, DeepInfra,
OpenCode) so you can compare speed and cost per provider. `deepseek-v4-flash`
is currently configured for OpenRouter and DeepInfra.

## Files

- `models.json` — editable list of models and providers to benchmark. Add or
  remove slugs/providers each week.
- `speed-weekly-YYYY-MM-DD.csv` — one row per `(hour, slug, provider)` call.

## CSV Schema

| Column | Description |
|--------|-------------|
| `run_date` | UTC date the run started |
| `hour_pst` | Hour in America/Los_Angeles time (00–23) |
| `hour_utc` | Hour in UTC (00–23) |
| `slug` | Canonical `models.json` slug |
| `provider` | Provider label: `openrouter`, `deepinfra`, or `opencode` |
| `model_id` | Provider model ID used for the call |
| `model_name` | Human-readable name |
| `tier` | Price tier |
| `max_tokens` | `max_tokens` setting |
| `prompt_tokens` | Input tokens charged |
| `output_tokens` | Completion tokens generated |
| `elapsed_ms` | Wall-clock milliseconds |
| `tokens_per_sec` | `output_tokens / (elapsed_ms / 1000)` |
| `cost` | USD cost of the call (using provider price from the config) |
| `status` | `success` or `error` |
| `error` | Error message if `status == error` |
| `measured_at` | ISO timestamp |

## Running manually

```powershell
# 24-hour run starting at the next hour boundary (24 rounds / hourly)
uv run python scripts/speed-weekly.py

# Single round (for cron/Tempo schedules that fire every 3 hours)
uv run python scripts/speed-weekly.py --rounds 1 --no-wait --max-tokens 250

# Regenerate the default model list after updating models.json/catalogs
uv run python scripts/speed-weekly.py --generate-config

# Dry-run to see the model/provider list and estimated cost
uv run python scripts/speed-weekly.py --dry-run

# Benchmark only one provider
uv run python scripts/speed-weekly.py --providers openrouter

# Benchmark a specific model across all configured providers
uv run python scripts/speed-weekly.py --models data/speed-weekly/models.json
```

## Prompt

The default prompt asks the model to:
1. Estimate the token count of a short Python snippet.
2. Write a tiny module with `fibonacci`, `is_palindrome`, and `factorial_iterative`.
3. Print the first 50 Fibonacci numbers.

This produces a small, deterministic code output while still generating enough
tokens for a meaningful speed reading.

## Cost Estimate

Prices are per-million-tokens. The schedule runs an 8-round, 24-hour snapshot
once every **8 days** (8 rounds total per snapshot). Manual `--rounds 24` is
3× these amounts. Actual spend depends on how much each model generates and
which providers are available. Estimates use 140 input tokens.

| Profile | Output | 32 non-frontier models | 25 cheap models |
|---------|--------|------------------------|-----------------|
| Consistency | 250 | ~$0.32/snapshot | ~$0.14/snapshot |
| Default | 500 | **~$0.60/snapshot** | **~$0.27/snapshot** |
| Accuracy | 750 | ~$0.89/snapshot | ~$0.39/snapshot |

At one snapshot every 8 days, the full 32-model set at 250 `max_tokens` costs
about **~$14.49/year** (~$0.28/week on average).

## Scheduling

A Tempo schedule in `salmon-orchestrator/Tasks/Schedule/` dispatches the
benchmark with **8 schedule files**, one per 3-hour slot, each repeating every
8 days. This makes the 24-hour snapshot drift through the weekdays
(Monday → Tuesday → Wednesday …). Each run is a single round at 250
`max_tokens`:

```powershell
uv run python scripts/speed-weekly.py --rounds 1 --no-wait --max-tokens 250
```

An OS-native Windows Task Scheduler alternative is available at
`scripts/install-speed-weekly-scheduled-task.ps1`. If you use it, delete the
`salmon-orchestrator/Tasks/Schedule/sched-20260825-*.json` files so the Tempo
poller does not also trigger the benchmark.

The schedule files are:

- `sched-20260825-001.json` — 00:00 UTC
- `sched-20260825-002.json` — 03:00 UTC
- `sched-20260825-003.json` — 06:00 UTC
- `sched-20260825-004.json` — 09:00 UTC
- `sched-20260825-005.json` — 12:00 UTC
- `sched-20260825-006.json` — 15:00 UTC
- `sched-20260825-007.json` — 18:00 UTC
- `sched-20260825-008.json` — 21:00 UTC

First snapshot: **2026-08-31**. The script is resumable and skips any
`(hour, slug, provider)` triples already recorded for the day.

## Adding or removing providers

Edit `models.json`. Each entry has a `providers` object mapping a provider key
(`openrouter`, `deepinfra`, `alibaba`) to a provider-specific `model_id`,
`in_price`, and `out_price`. For example:

```json
{
  "slug": "deepseek-v4-flash",
  "providers": {
    "openrouter": {
      "model_id": "deepseek/deepseek-v4-flash",
      "in_price": 0.0679,
      "out_price": 0.168
    },
    "deepinfra": {
      "model_id": "deepseek-ai/DeepSeek-V4-Flash",
      "in_price": 0.09,
      "out_price": 0.18
    }
  }
}
```

The `alibaba` provider corresponds to Alibaba Cloud / OpenCode / Zen pricing.
