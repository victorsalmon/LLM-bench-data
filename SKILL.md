---
name: research/appraise-llm
description: Appraise new and existing LLMs — research benchmarks, pricing, features, produce comparison tables, benchmark a model's tokenizer/thinking-tokens/speed live, publish a News blog post, and commit/push the data. Use when asked to appraise, evaluate, compare, review, benchmark, or audit LLMs, or when a new model is released.
type: skill
container: opencode
---

# Appraise LLM — Skill

## Purpose

Research and evaluate LLMs against the user's real-world usage strategy. Output a structured comparison table showing benchmarks, pricing, new features, and specialty for each model. Answer one question: "Is this model worth my attention given my current setup?"

## User's Strategy (Baseline)

| Layer | Model | Source | Use case |
|-------|-------|--------|----------|
| Daily driver | DeepSeek V4 Flash | OpenCode Zen ($0.28/M out) | General coding, daily agent work |
| Max variant | DeepSeek V4 Flash Max | OpenRouter (~$0.28/M out) | When Flash's Max config is needed |
| Complex planning | GLM 5.2 | OpenCode Zen ($4.40/M out) | Audits, architecture, planning from scratch |
| Subscription | OpenCode Zen | $20 PAYG top-up, auto-reload at $5 | Primary API gateway |
| Secondary | OpenRouter | PAYG + 5.5% fee | Max variants and models not on Zen |

Goal: **minimize cost, maximize effective capability.** New models are evaluated against this stack.

## Price Tiers (by Output $/M tokens)

All pricing sourced from [OpenCode Zen](https://opencode.ai/zen) (primary) and [OpenRouter](https://openrouter.ai) (secondary for Max variants).

| Tier | Output $/M | Role | Current top pick |
|------|-----------|------|-----------------|
| **Complex** | $18+ | Hardest problems — architecture, audits, planning from scratch | Claude Fable 5 |
| **Daily** | $8 – $17.99 | Strong daily driver — general coding, reasoning | Claude Sonnet 5 |
| **Taskrunner** | $2 – $7.99 | Fast routine tasks — implementation, refactoring, reviews | GLM 5.2 |
| **Budget Taskrunner** | $0.01 – $1.99 | High-volume, cost-sensitive work | DeepSeek V4 Flash |
| **Free** | $0 | No-cost experimentation (data may train models) | DeepSeek V4 Flash Free |

Repeat every appraisal: check for new models in each tier. Every tier gets at least one entry.

## Required Model Slots

Every appraisal report must include:

1. **Latest GLM** — currently GLM 5.2. Check for GLM 5.3+
2. **Latest DeepSeek Flash** — currently DeepSeek V4 Flash. Check for V5+
3. **Top 3 in each tier** — by AA Intelligence Index, then by output price (cheaper = better tiebreak)
4. **New arrivals** — any model released since the last appraisal that doesn't fit existing slots

## Blended Pricing Model

All pricing comparisons use a **weighted blend** across three token types: cache-hit, input, output. This mirrors Artificial Analysis' industry-standard 7:2:1 ratio, extended to account for thinking tokens.

### Baseline Blend (7:2:1)

Weights: cache-hit=7, input=2, output=1. Total weight = 10.

```
Blended_$/M = (7 × P_cached + 2 × P_input + 1 × P_output) / 10
```

This is the default for non-reasoning models (thinking_token_ratio = 0). It reflects a realistic workload where most tokens hit the cache.

### Thinking-Adjusted Blend (7:2:(1+R))

For reasoning models that generate invisible chain-of-thought tokens, the output portion inflates:

```
Blended_$/M = (7 × P_cached + 2 × P_input + (1+R) × P_output) / (10 + R)
```

Where **R** = `thinking_token_ratio` from `models.json` (thinking tokens per visible output token).

Example — DeepSeek V4 Pro (R=4, P_cached=$0.145, P_in=$1.74, P_out=$3.48):
```
Standard 7:2:1:  (7×0.145 + 2×1.74 + 1×3.48) / 10  = $0.756/M
Thinking-adjusted: (7×0.145 + 2×1.74 + 5×3.48) / 14 = $1.564/M  (2.07× standard)
```

The thinking-adjusted blend is the **true cost comparison** when evaluating reasoning vs. non-reasoning models for the same task.

### Tokenizer Efficiency

Each model family tokenizes text differently. E = tokens per word. Three raw values (`code`, `prose`, `blended`) measured via OpenRouter API on fixed sample texts (Session 5, 2026-07-09, 306-word code / 235-word prose / 250-word blended, max_tokens=20, temperature=0, same key for all 23 models). The blend value is a 60:40 code:prose weighted average reflecting typical coding workloads. The blended-sample E provides a third reference point for technical prose.

| Rank | Family | Model | E code | E prose | E blended | E blend (60:40) |
|:----:|--------|-------|:-----:|:------:|:---------:|:---------------:|
| 1 | Perplexity | Sonar Pro / Pro Search | 2.17 | 1.14 | 1.68 | **1.76** |
| 2 | OpenAI (GPT) | GPT-5.4 Nano, o3-mini | 2.20 | 1.16 | 1.71 | **1.78** |
| 3 | Microsoft | Phi-4 | 2.19 | 1.17 | 1.71 | **1.78** |
| 4 | Kimi / Moonshot | K2.7 Code | 2.21 | 1.16 | 1.71 | **1.79** |
| 5 | Meta | Llama 3.3 70B | 2.20 | 1.19 | 1.82 | **1.80** |
| 6 | Meta | Llama 4 Maverick | 2.22 | 1.19 | 1.72 | **1.81** |
| 7 | GLM / Zhipu | GLM 5.2 | 2.21 | 1.20 | 1.73 | **1.81** |
| 8 | Mistral | Large 3, Codestral | 2.27 | 1.18 | 1.73 | **1.83** |
| 9 | DeepSeek | V4 Flash, R1, Chat V3 | 2.28–2.29 | 1.19–1.20 | 1.76–1.83 | **1.84–1.85** |
| 10 | MiniMax | M3 | 2.33 | 1.29 | 1.84 | **1.91** |
| 11 | Amazon | Nova Pro | 2.45 | 1.16 | 1.76 | **1.93** |
| 12 | Cohere | Command A | 2.50 | 1.13 | 1.71 | **1.95** |
| 13 | Gemini | 2.5 Pro | 2.68 | 1.14 | 1.72 | **2.06** |
| 14 | AI21 | Jamba Large 1.7 | 2.82 | 1.22 | 1.90 | **2.18** |
| 15 | Anthropic | Claude Haiku 4.5 | 2.82 | 1.30 | 1.88 | **2.21** |
| 16 | Amazon | Nova Premier | 2.92 | 1.31 | 1.92 | **2.28** |
| 17 | Grok / xAI | Grok 4.5 | 3.09 | 2.01 | 2.54 | **2.66** |

> **Session 5 (2026-07-09):** Full standardized re-test of all 23 measurable models with identical samples, same API key (OPENROUTER_API_KEY), same max_tokens=20. 69 calls, ~$0.20 total. Replaces all earlier Sessions 1-4 data. Unmeasurable models: Fugu Ultra (ignores max_tokens, ~95 tok/word), o4-mini (Responses API, no usage field), Inflection 3 Pi/Productivity (502 errors), Qwen 3.7 Plus/Max (guardrail), Sonar Reasoning Pro/Deep Research (timeout). See `data/experiment-session5-raw.csv` and `docs/tokenizer-efficiency-experiment.md` for full data.
>
> **Output & reasoning extension (proposed):** Section 8 of the experiment doc defines 16 task prompts across 10 usage categories (Q&A, Coding, Analysis, Reasoning, Creative, Role-play, Instruction following, Safety, Multilingual, Extraction) for measuring output verbosity, persona inflation, refusal cost, and hidden reasoning tokens. Full 21-model × 16-task run costs at most ~$0.75 (worst case) with likely actual cost ~$0.20-0.55. See [`docs/tokenizer-efficiency-experiment.md §8`](docs/tokenizer-efficiency-experiment.md).

## Appraisal Table Template — Primary View

**Primary benchmarks** (always shown): SWE-bench Pro, Terminal-Bench 2.1 — these are the most relevant for agentic coding workflows. SWE-bench Verified shown when available.

Show top 3 per tier by default. When asked "show all models" or "full breakdown", show every model in the database.

| Model | Tier | SWE-bench Pro | TB 2.1 | Input $/M | Output $/M | Blend 7:2:1 | Blend w/ Think | AAII | Thinking Tax | Beats your stack? |
|-------|:---:|:-----------:|:-----:|:--------:|:--------:|:----------:|:-------------:|:---:|:------------:|:---------------:|
|       |      |             |       |          |          |            |               |      |              |                  |

- **SWE-bench Pro**: Primary coding benchmark. Scores: [swebench.com](https://swebench.com). N/A if untested.
- **TB 2.1**: Terminal-Bench 2.1. Primary agentic benchmark. Scores: [tbench.ai](https://tbench.ai). N/A if untested.
- **Blend 7:2:1**: Standard blended price (cache:input:output = 7:2:1). **Apples-to-apples across all models.**
- **Blend w/ Think**: Thinking-adjusted blend (7:2:(1+R)). Shows true cost when a model burns hidden chain-of-thought tokens. Same as blend 7:2:1 for non-reasoning models.
- **Thinking Tax**: Ratio of hidden thinking tokens per visible output token. "—" = none/negligible. "4×" = 4 thinking tokens per 1 visible. Models flagged with a tax cost more than their raw output price suggests.
- **Beats your stack?**: "Yes" / "Maybe" / "No" based on whether this model outperforms the equivalent-tier pick in your current strategy at similar or lower cost (considering thinking-adjusted blend).

### Additional Benchmark Views

Ask for specific views: "show me OSWorld scores", "compare GPQA Diamond", "show HLE", "full benchmark breakdown", etc.

## Full Benchmark Schema

All benchmarks stored in `models.json` per model. A dash `-` means no score available.

| Field | Benchmark | Category | What it measures | Best score in DB |
|-------|-----------|----------|-----------------|:----------------:|
| `swe_bench_pro` | SWE-bench Pro | Coding | Harder GitHub issue resolution | Claude Fable 5: 80.3% |
| `swe_bench_verified` | SWE-bench Verified | Coding | Human-validated GitHub issue resolution | Claude Fable 5: 95.0% |
| `terminal_bench_2_1` | Terminal-Bench 2.1 | Agentic | Terminal-based SE, sysadmin, ML, security tasks | Claude Fable 5: 88.0% |
| `os_world_verified` | OSWorld-Verified | RPA / Vision | Operating real computer environments via screenshots | GPT-5.5: 78.7% |
| `browse_comp` | BrowseComp | Web Search | Persistent web search for hard-to-find info | GPT-5.5 Pro: 90.1% |
| `gpqa_diamond` | GPQA Diamond | Research | Graduate-level science reasoning | Gemini 3.1 Pro: 98.0% (ARC-1) |
| `hle_no_tools` | HLE (no tools) | Research | Humanity's Last Exam without tool use | Claude Opus 4.7: 46.9% |
| `hle_with_tools` | HLE (with tools) | Research | Humanity's Last Exam with browsing/code tools | GPT-5.4 Pro: 58.7% |
| `arc_agi_1` | ARC-AGI-1 Verified | Reasoning | Abstract visual reasoning puzzles (easy) | Gemini 3.1 Pro: 98.0% |
| `arc_agi_2` | ARC-AGI-2 Verified | Reasoning | Abstract visual reasoning puzzles (hard) | GPT-5.5: 85.0% |
| `tau2_bench_telecom` | Tau²-Bench Telecom | Tool Use | Complex customer-service tool workflows | GPT-5.5: 98.0% |
| `mcp_atlas` | MCP Atlas | Tool Use | Multi-MCP-server tool orchestration (Scale AI) | Claude Opus 4.7: 79.1% |
| `toolathlon` | Toolathlon | Tool Use | Real-world API tool calling across multi-step tasks | GPT-5.5: 55.6% |
| `frontier_math_t1_3` | FrontierMath T1-3 | Math | Competition-level math (easier tiers) | GPT-5.5 Pro: 52.4% |
| `frontier_math_t4` | FrontierMath T4 | Math | Frontier math (hardest tier) | GPT-5.5 Pro: 39.6% |
| `aa_intelligence_index` | AA Intelligence Index | Composite | Weighted avg of 10 evals by Artificial Analysis | Claude Fable 5: 56 |

### Use-Case-to-Benchmark Mapping

| If you are building... | You should look at... | What it proves |
|------------------------|----------------------|----------------|
| Autonomous RPA / Web Scrapers | WebArena, OSWorld | Can the model navigate visual interfaces and multi-step UI flows? |
| Deep Research / Strategy Agents | HLE, GPQA Diamond | Can the model reason at a postgraduate level without hallucinating? |
| Algorithmic Generators | LiveCodeBench | Can the model solve novel logic problems it has never seen before? |
| Complex Tool Orchestrators | Tau²-Bench, GAIA | Does the model crash when an API returns an unexpected error? |

## Research Protocol

When asked to appraise:

1. **Load models.json** for baseline data
2. **Fetch live Zen models** — check `GET https://opencode.ai/zen/v1/models` for new models, price changes, deprecations
3. **Check OpenRouter** for new Max variants or models not on Zen
4. **Cross-reference benchmarks** — visit swebench.com, tbench.ai, artificialanalysis.ai for updated scores
5. **Compare vs models.json** — flag:
   - New models not in the database
   - Price changes (up or down)
   - Deprecated/sunset models
   - Unexpectedly strong benchmark results
 6. **Classify into tiers** by output $/M token. For reasoning models with `thinking_token_ratio > 0`, also note the **effective tier** (output $/M × (1+R)) — a model may appear Taskrunner by raw price but actually land in Daily tier when thinking tax is applied.
 7. **Produce the table** — top 3 per tier by default (or all if asked). Include both Blend 7:2:1 and Blend w/ Think columns.
 8. **Strategy assessment** — for each tier, say whether any model beats the user's current pick. Use thinking-adjusted blend for reasoning models.
 9. **Update models.json** with verified findings

## Per-Model Appraisal Pipeline

**Trigger:** "Appraise model X" / "A new model just dropped" / "Benchmark <ModelName>." This is the **event-driven, single-model** flow — distinct from the market-wide Research Protocol above. One model in → one News post + one data commit + push out.

The comparison set (the models the new model is measured *against*) is **not** re-measured. Their values are read from `models.json`. Only the new model is benchmarked live. This keeps each appraisal to ~$0.02–0.10 and a few minutes.

### Steps

1. **Identify** the model. Confirm the OpenRouter id (`GET https://openrouter.ai/api/v1/models`), family, canonical kebab-case slug, whether it supports `reasoning_effort` (xhigh), and current pricing. Derive the slug by lowercasing the display name and replacing non-alphanumerics with hyphens (e.g. "GLM 5.3" → `glm-5-3`, "DeepSeek V5 Flash" → `deepseek-v5-flash`). "Max" variants append `-max` and reuse the base model id with `reasoning_effort=xhigh`.

2. **Measure live** → run the harness once:
   ```
   uv run llmcc appraise <slug>
   ```
   This writes `data/appraise/<slug>-<YYYY-MM-DD>.csv` and prints only a one-line run summary (`Appraisal run <id> finished with status '<status>'. Wrote N rows to <path>.`) — it does **not** print headline metrics. The `appraisal` experiment runs tokenizer samples (code / prose / blended), a speed check (`speed_max_tokens = 3300`), and a reasoning check for the requested model slug; reasoning-token output is captured when the model exposes a reasoning effort control (DeepSeek Pro/Flash Max, o-series, R1, etc.). The headline values (`tokenizer_efficiency`, `thinking_token_ratio`, `speed_tok_per_s`) are aggregated from those rows by `BenchmarkExporter` (`uv run llmcc export --format json`) — see `data/appraise/README.md`.

3. **Research SWE** — SWE-bench Verified + SWE-bench Pro from published leaderboards ([swebench.com](https://swebench.com), [artificialanalysis.ai](https://artificialanalysis.ai)). Each score is stored as `{ score, source, date }`. Use `null` if the model is untested — matches the existing `models.json` convention. There is no local SWE harness; these are externally-published, attributed, dated scores.

4. **Update `models.json`** — add (or refresh) the model's entry under `models[<slug>]` with: identity fields (`name`, `family`, `version`, `tier`, `context_window`, `parameters`, `open_weights`, `license`), `zen_pricing` / `openrouter_pricing`, the three measured values, and the `benchmarks` block. Also bump the top-level `last_updated` changelog string. If this model is a new flagship for a watched family, update the corresponding `appraise_slots.watching` pointer (e.g. `latest_sonnet`, `latest_m3`). Note: `models.json` is the hand-edited site-facing artifact; the CLI's catalog source of truth is `catalogs/models.yaml`. Keep the two in sync when pricing or availability changes (the CLI never reads `models.json` — see ARCHITECTURE.md "Model-data files: catalog vs site artifact").

5. **Build the comparison table** — one row for the new model plus one row per model in `appraise_slots.active_stack` (your daily drivers) and `appraise_slots.watching` (flagships you track). Every value except the new model's measured ones is read from `models.json`. Columns match the **Appraisal Table Template** above: SWE-bench Pro, TB 2.1, Input/Output $/M, Blend 7:2:1, Blend w/ Think, AAII, Thinking Tax, "Beats your stack?". For the new model, compute both blend columns using its freshly-measured `thinking_token_ratio` and `tokenizer_efficiency`.

6. **Write the News post** — create `clocklobster.com/blog/news/<YYYY-MM-DD>-<slug>/` containing `index.md` (source) and `index.html` (rendered standalone page). **Clone the shared chrome** from `clocklobster.com/blog/_base-template/post-base.{html,md}` and **apply the News skin deltas** from `clocklobster.com/blog/_skins/article-news.md` (section label `News`, active nav on the News `<li>`, the Appraise-Model body structure). Depth-3 page → assets at `../../../`. See `blog/_base-template/README.md` for the full placeholder index and depth rule. Header block convention (no YAML): `**Series:** News — Model Appraisal`, `**Published:** YYYY-MM-DD`, `**Dataset:** github.com/victorsalmon/LLM-bench-data`, `**Author:** <byline>`. Body: verdict up front, the comparison table (as `class="sortable"`), the measured numbers, cost analysis, and a clear recommendation. Then **append a card** to `clocklobster.com/blog/news/index.html` linking the new post.

7. **Commit + push data repo** — `git add data/appraise/<slug>-<date>.csv models.json` (plus any SKILL.md/AGENTS.md changes) → `git commit -m "feat(data): appraise <ModelName> — tokenizer, thinking, speed, SWE"` → `git push origin main`.

8. **Commit + push site repo** — in `clocklobster.com/`: `git add blog/news/` (new post + landing update) → `git commit -m "feat: add News post — <ModelName> appraisal"` → `git push origin main`. The site's CI is validate-only; deploys to dotCanada (LiteSpeed) are done locally via the `dotcanada` branch pushed to the `dotCanada` remote.

### Cross-repo layout

The repo and the site live under separate roots:
- This repo: `github.com/victorsalmon/LLM-bench-data`
- The site: `C:\Sites\clocklobster.com` → `worktree.ca/clocklobster/clocklobster.com`

The site repo lives at `C:\Sites\clocklobster.com` (not a sibling of this repo). The site's `AGENTS.md` documents the reverse path and mandates auto-commit/push to `main`; this repo's `AGENTS.md` does the same.

### When to update the watch list

`appraise_slots.watching` is data, not code. Update a slot whenever a new flagship drops in that family — e.g. when M4 supersedes M3, set `latest_m3` (rename the slot if the family name changes) to the new slug. `active_stack` changes only when the user's daily-driver stack changes. null means "no model currently tracked."

## Data Files

| File | Purpose |
|------|---------|
| `models.json` | Canonical model database with pricing, benchmarks, features, `appraise_slots` watch list (site-facing; distinct from `catalogs/models.yaml`) |
| `SKILL.md` | This file — skill instructions (market-wide research + per-model appraisal pipeline) |
| `AGENTS.md` | Repo context + completion protocol (commit/push to main) for AI assistants |
| `docs/tokenizer-efficiency-experiment.md` | Full experiment write-up: hypothesis, standardized conditions, method, results, discussion, proposed output/reasoning extension |
| `data/experiment-session5-raw.csv` | Raw measurement data: 69 calls, per-call prompt_tokens, E values, status |
| `data/experiment-session5-consolidated.csv` | Cleaned & corrected results for all 21 measurable models |
| `data/experiment-session5-summary.csv` | Ranked E values with 60:40 and 33:33:33 blend scores |
| `data/appraise/` | Per-model appraisal raw CSVs (one per model: `<slug>-<date>.csv`) — written by `uv run llmcc appraise <slug>` |
| `data/samples/code-sample.txt` | Canonical TypeScript code sample (306 words) |
| `data/samples/prose-sample.txt` | Canonical prose sample (235 words) |
| `data/samples/blended-sample.txt` | Canonical blended documentation sample (250 words) |
| `llmcc` | Python CLI entry point (`uv run llmcc --help`) |
| `.env` | Gitignored user config file (OpenRouter API key) — copy from `.env.example` |

## Pricing Methodology

All pricing in `models.json` stores **raw Input $/M, Output $/M, Cached $/M** as three independent columns — the provider's advertised rates. For comparisons, apply the **Blended Pricing Model** above which normalizes across usage patterns (7:2:1 baseline, 7:2:(1+R) for thinking models).

Each model also stores:
- `thinking_token_ratio` — hidden chain-of-thought tokens per visible output token. 0 for direct-response models, >0 for reasoning models (DeepSeek V4 Pro, o-series, R1).
- `tokenizer_efficiency` — composite blend value (60:40 code:prose weighted average, from family table above).

**Normalized cost-per-task formula** (combines all three factors):

```
C_total = (W_in × E × Pin/10^6) + ((W_out × E + T_think) × Pout/10^6)
```

Where:
- `W_in`, `W_out` = baseline input/output in words
- `E` = tokenizer efficiency blend (tok/word, from `models.json`). For pure-code output, substitute `E_code` from the family table; for prose-heavy input, substitute `E_prose`.
- `T_think` = W_out × E × thinking_token_ratio
- `P_in`, `P_out` = provider price per million tokens

For task-based costing: pick a specific task type, estimate typical word counts, apply the formula.

## Provider Notes

- **OpenCode Zen**: PAYG via $20 top-up. Zero markup — prices = provider cost + processing fee. Auto-reload at $5 balance. Free models available (usage data may train models).
- **OpenRouter**: PAYG with 5.5% platform fee. Used for Max variants (DeepSeek V4 Flash Max, V4 Pro Max) and any model not on Zen.
- **Direct API**: Fallback only. Noted explicitly in the database.
