# data/appraise/

Per-model appraisal raw data. One CSV per appraisal, written by
`uv run llmcc appraise <slug>`, named `<slug>-<YYYY-MM-DD>.csv`.

This is distinct from the batch session CSVs in `../` (Session 5 / 6 / 6b) and
`../output-experiment/` — those are one-shot multi-model sweeps. This directory
is the landing zone for the **event-driven, single-model** Appraise-Model flow:
when a new model drops, one file lands here.

## CSV schema

```
model_id,model_name,family,slug,date,measurement,sample_type,reasoning_effort,
max_tokens,prompt_tokens,output_tokens,reasoning_tokens,elapsed_ms,tokens_per_sec,
tokens_per_word,blend_60_40,cost,status,error
```

- `measurement` — `tokenizer_E` | `thinking_tokens` | `speed`
- `sample_type` — `code` | `prose` | `blended` (for tokenizer_E / thinking); `numbers` (for speed)
- `reasoning_effort` — `none` | `xhigh` (only `thinking_tokens` rows use `xhigh`)
- `cost` — per-call cost, enriched inline from live OpenRouter pricing

## Headline metrics (derived by the script, printed to console)

- **tokenizer_efficiency** = `0.6*E_code + 0.4*E_prose` (the 60:40 blend)
- **thinking_token_ratio** = `reasoning_tokens / completion_tokens` (thinking_tokens row only)
- **speed_tok_per_s** = the `max_tokens=1000` speed row

These three values land in `models.json` under the appraised model's entry.
