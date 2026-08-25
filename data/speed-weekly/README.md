# Weekly Speed Consistency Benchmark

This directory holds the configuration and time-of-day CSVs for the weekly
LLM speed benchmark.

## Purpose

Measure tokens/second for a small, fixed coding task every hour for 24 hours,
once per week. The goal is **consistency**: detecting which endpoints slow down
at which times, not producing a perfect absolute speed number.

A model can be benchmarked across multiple providers (OpenRouter, DeepInfra,
Alibaba/OpenCode) so you can compare speed and cost per provider.

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
# 24-hour run starting at the next hour boundary
uv run python scripts/speed-weekly.py

# Single hourly round (for cron/Tempo schedules)
uv run python scripts/speed-weekly.py --rounds 1 --no-wait

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

## Weekly Cost Estimate

Prices are per-million-tokens. Actual spend depends on how much each model
actually generates and which providers are available; the estimates below use
140 input tokens and assume an average of 250, 500 (the default `max_tokens`),
or 750 output tokens.

| Profile | Output | Calls/hour | 32 non-frontier models | 25 cheap models |
|---------|--------|------------|------------------------|-----------------|
| Consistency | 250 | 1 | ~$0.95/week | ~$0.43/week |
| Consistency+ | 250 | 3 | ~$2.85/week | ~$1.28/week |
| Default | 500 | 1 | ~$1.80/week | ~$0.80/week |
| Default+ | 500 | 3 | ~$5.40/week | ~$2.39/week |
| Accuracy | 750 | 1 | ~$2.65/week | ~$1.17/week |
| Accuracy+ | 750 | 3 | ~$7.95/week | ~$3.50/week |

The default schedule runs **1 call per hour for 24 hours at 500 `max_tokens`**,
which costs about **$1.80/week** for the full 32-model non-frontier set. Only
providers with configured API keys are benchmarked.

## Scheduling

A Tempo schedule in `salmon-orchestrator/Tasks/Schedule/` dispatches the
benchmark every Monday, hourly, for 24 hours. Each hour it runs:

```powershell
uv run python scripts/speed-weekly.py --rounds 1 --no-wait
```

The schedule is cron `0 * * * 1` (top of every hour on Mondays). The script is
resumable and skips any `(hour, slug, provider)` triples already recorded for the
day.

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
    },
    "alibaba": {
      "model_id": "deepseek-v4-flash",
      "in_price": 0.14,
      "out_price": 0.28
    }
  }
}
```

The `alibaba` provider corresponds to Alibaba Cloud / OpenCode / Zen pricing.
