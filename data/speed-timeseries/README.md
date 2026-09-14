# Speed Time-of-Day Experiment

## Purpose

Measures token output speed (tokens/second) for 5 LLMs every hour on the hour for 24 hours, via OpenRouter. The goal is to detect time-of-day speed patterns that correlate with regional server load — specifically whether China-based models slow during Asian peak hours and whether US-based models slow during American peak hours.

Developers who switch between model ecosystems can use this data to plan their work schedules around predictable speed sweet spots.

## Models

| Model | OpenRouter ID | Region | Why |
|-------|--------------|--------|-----|
| DeepSeek V4 Flash | `deepseek/deepseek-v4-flash` | China | Budget daily driver (284B MoE, 13B active) |
| GLM 5.2 | `z-ai/glm-5.2` | China | Task runner (753B MoE, 40B active) |
| MiniMax M3 | `minimax/minimax-m3` | China | Budget task runner (multimodal) |
| Claude Sonnet 5 | `anthropic/claude-sonnet-5` | US | Daily tier (Anthropic) |
| o4-mini | `openai/o4-mini` | US | Task runner (OpenAI reasoning) |

## Methodology

- **Prompt**: `"Write the numbers from 1 to 200, comma-separated."` (~790 output tokens)
- **max_tokens**: 3300 (headroom — the prompt doesn't fill it, but provides consistency margin)
- **temperature**: 0 (deterministic)
- **Timing**: Wall-clock `(Get-Date)` delta, non-streaming
- **Trials**: N=1 per model per hour (matches existing speed benchmark methodology)
- **API**: OpenRouter (`openrouter.ai/api/v1/chat/completions`)
- **Rate limiting**: 200ms sleep between model calls within a round

## CSV Schema

File naming: `speed-timeseries-<YYYY-MM-DD>.csv`

| Column | Type | Description |
|--------|------|-------------|
| `run_date` | string | Date of the experiment run (YYYY-MM-DD) |
| `hour_pst` | string | Hour in Pacific Time (00–23) |
| `hour_utc` | string | Hour in UTC (00–23) |
| `model_id` | string | OpenRouter model ID |
| `model_name` | string | Human-readable model name |
| `slug` | string | Canonical kebab slug (matches models.json) |
| `region` | string | `China` or `US` |
| `max_tokens` | int | max_tokens setting used |
| `prompt_tokens` | int? | Input tokens returned by API |
| `output_tokens` | int? | Output tokens returned by API |
| `elapsed_ms` | int? | Wall-clock milliseconds for the response |
| `tokens_per_sec` | float? | `output_tokens / (elapsed_ms / 1000)`, rounded to 1 decimal |
| `cost` | string | USD cost of the call (legacy; enrichment script removed), or `N/A` |
| `status` | string | `success`, `not_found`, `timeout`, `blocked`, or `error` |
| `error` | string | Error message (truncated to 200 chars) on failure, empty on success |
| `measured_at` | string | ISO-ish timestamp of when the call was made |

## Running the Experiment

The original `speed-timeseries.ps1` harness has been removed. Current weekly runs: `../speed-weekly/README.md`.

## Cost Estimate

~$0.38/day total (5 models × 24 hours = 120 calls). Claude Sonnet 5 is the most expensive at ~$0.19/day due to its $10/M output pricing.

## Interpreting Results

- **tokens_per_sec** is the key metric — higher is better.
- Compare `hour_pst` vs `hour_utc` to align with Chinese business hours (UTC+8, so PST+16).
- The hypothesis: China models may degrade around UTC 02:00–10:00 (PST 18:00–02:00), which is Chinese daytime.
- US models may degrade around UTC 14:00–22:00 (PST 06:00–14:00), which is US daytime.
- Individual call variance is high (N=1), so look for multi-hour trends rather than single-point outliers.
