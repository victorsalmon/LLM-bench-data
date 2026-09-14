# Tokenizer Efficiency Experiment

**Date**: 2026-07-08 (Sessions 1-4); 2026-07-09 (Session 5 — standardized re-test)
**Author**: OpenCode DeepSeek V4 Flash Max Agent c/o Victor Salmon
**Platform**: OpenRouter API
**Total cost**: ~$0.66 (Session 5: ~$0.20)

---

## Abstract

Tokenizer efficiency (E) measures how many tokens a model family generates per word of text. It bridges per-token pricing and per-task costing. Without E, a model with lower per-token price but higher token density may appear cheaper than it really is. This experiment measured E for 21 model families (23 models) by submitting fixed code, prose, and blended samples to the OpenRouter API and reading `usage.prompt_tokens` from each response.

---

## 1. Introduction

Each model family uses a different tokenizer (BPE, DSL, SentencePiece, o200k, etc.). The same English text can produce dramatically different token counts across families — Grok uses 2.66 tokens per word while Perplexity Sonar uses 1.76, a 51% difference. This means per-token price comparisons alone are misleading.

The tokenizer efficiency (E) normalizes cost comparisons by answering: **"How many tokens does this model need to represent one word of my input?"**

---

## 2. Hypothesis

**Null hypothesis (H₀)**: All model families have the same tokenizer efficiency (E ≈ constant). Differences in per-token pricing fully explain cost differences.

**Alternative hypothesis (H₁)**: Tokenizer efficiency varies significantly across families (E ranges from ~1.76 to ~2.66). A model with lower per-token price but higher E may cost more per task than a model with higher per-token price but lower E.

---

## 3. Materials

### 3.1 Sample Texts (Session 5 — Standardized)

> Sessions 1-4 used varying sample lengths and API keys. Session 5 re-tested all measurable models with identical conditions for apples-to-apples comparison. Values in this document are from Session 5 unless noted.

Three sample texts were used, all submitted to every model:

**Code sample** (306 words):
- Multi-function TypeScript module: async batch processing with generics, error handling, AbortController, Promise.all workers, type definitions
- Rich in special characters: braces, semicolons, angle brackets, dot notation, arrow functions

**Prose sample** (235 words):
- Technical architecture paragraph: batch processing pattern description
- Natural English with punctuation: dashes, colons, commas, periods

**Blended sample** (250 words):
- Technical documentation prose with inline code references, method names, API endpoints, types
- Mix of natural language and code-like patterns: backtick-enclosed identifiers, `PascalCase` names, `UPPER_CASE` constants, `/api/v1/` endpoints, type annotations like `Array<number>`
- Tests how tokenizers handle technical vocabulary with special characters embedded in prose

### 3.2 Standardized Conditions

All measurements in Session 5 share these fixed conditions. Changing any one may shift E values (see §6.3):

| Condition | Fixed value | Why it matters |
|-----------|-------------|----------------|
| API key | `OPENROUTER_API_KEY` (current) — historical sessions used workspace-scoped keys | Different keys route to different inference providers; Session 1-4 used 3 different keys with divergent results |
| API endpoint | `https://openrouter.ai/api/v1/chat/completions` | Direct provider APIs (AWS Bedrock, Azure, GCP) may report different token counts for the same model |
| max_tokens | 20 | Must be small enough to minimize output cost but large enough for the model to return `usage`; 20 works for all measurable models |
| temperature | 0 | Deterministic — prompt_tokens is deterministic regardless, but zero eliminates edge cases |
| message format | Single `user` message only | No system prompt, no assistant prefix — measures raw input tokenization only |
| Sample word counts | Code=306, Prose=235, Blended=250 | Long enough to amortize per-message overhead, short enough to keep cost at ~$0.003/call |
| Sample content | Fixed .txt files per type | Identical text across all models — only the tokenizer changes |
| Order of calls | Alphabetical by model, then code→prose→blended | Models tested within minutes of each other (no provider drift) |
| Date | 2026-07-09 | All 69 calls in one afternoon — no version drift |

### 3.3 API Configuration

| Parameter | Value |
|-----------|-------|
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Method | POST |
| Authentication | Bearer token (`OPENROUTER_API_KEY`) |
| max_tokens | 20 (all models) |
| temperature | 0 |
| messages | Single `user` message containing sample text |
| Measured field | `usage.prompt_tokens` from response JSON |
| Total calls | 69 (23 models × 3 samples) |
| Date | 2026-07-09 |

### 3.4 Data Processing

```
E_code = prompt_tokens(code_sample) / 306
E_prose = prompt_tokens(prose_sample) / 235
E_blended = prompt_tokens(blended_sample) / 250
E_60_40 = 0.60 × E_code + 0.40 × E_prose
E_33_33_33 = (E_code + E_prose + E_blended) / 3
```

The 60:40 blend reflects a typical coding workload where code-generation tasks dominate. The 33:33:33 blend gives equal weight to all three sample types.

### 3.4 Eliminated / Unmeasurable Models

| Model | Reason |
|-------|--------|
| Fugu Ultra | Ignores max_tokens (10,729 output for 306-word code); reports ~95 tok/word |
| o4-mini | OpenAI Responses API — no `usage.prompt_tokens` field |
| Inflection 3 Pi / Productivity | Provider returns empty 502 responses |
| Qwen 3.7 Plus / Max | OpenRouter content guardrail blocks access |
| Sonar Reasoning Pro / Deep Research | Search models timeout before returning `usage` |

---

## 4. Method

### 4.1 Protocol

1. Define 23 model IDs from OpenRouter's model catalog
2. Read each sample text from file
3. For each model, send 3 POST requests (one per sample type)
4. Read `usage.prompt_tokens` and `usage.completion_tokens`
5. Compute E values and blend scores
6. Save raw results to CSV

### 4.2 Guardrail Handling

Earlier sessions (1-4) encountered guardrail blocks for 11 models due to workspace-level Model Access filtering in OpenRouter. Session 5 used `OPENROUTER_API_KEY` (then named `OPENROUTER_CODE_KEY`) which had permissive routing — no models were guardrail-blocked.

### 4.3 Model ID Changes

Several model IDs changed between Sessions 1-4 and Session 5:

| Old ID | New ID |
|--------|--------|
| `deepseek/deepseek-chat-v4-flash` | `deepseek/deepseek-v4-flash` |
| `deepseek/deepseek-chat-v3.2` | `deepseek/deepseek-v3.2` |
| `moonshotai/kimi-k2.5-code` | `moonshotai/kimi-k2.7-code` |
| `meta-llama/llama-4-maverick-17b-128e` | `meta-llama/llama-4-maverick` |

### 4.4 Failed Measurements

- DeepSeek V3.2 (corrected ID) returned higher E values than other DeepSeek models (code E=2.50 vs 2.28-2.29), suggesting it may route to a different model variant
- Grok 4.5 ignored `max_tokens=20` in all 3 calls (461-1161 output tokens instead of 20), but `prompt_tokens` is unaffected by this

---

## 5. Results

### 5.1 Ranked Families (by blend_60_40)

| Rank | Family | Model | Code E | Prose E | Blend E | E blend (60:40) | E blend (33:33:33) |
|:----:|--------|-------|:-----:|:------:|:-------:|:---------------:|:------------------:|
| 1 | Perplexity | Sonar Pro / Pro Search | 2.17 | 1.14 | 1.68 | **1.76** | 1.66 |
| 2 | OpenAI | GPT-5.4 Nano, o3-mini | 2.20 | 1.16 | 1.71 | **1.78** | 1.69 |
| 3 | Microsoft | Phi-4 | 2.19 | 1.17 | 1.71 | **1.78** | 1.69 |
| 4 | Kimi | K2.7 Code | 2.21 | 1.16 | 1.71 | **1.79** | 1.69 |
| 5 | Meta | Llama 3.3 70B | 2.20 | 1.19 | 1.82 | **1.80** | 1.74 |
| 6 | Meta | Llama 4 Maverick | 2.22 | 1.19 | 1.72 | **1.81** | 1.71 |
| 7 | GLM | GLM 5.2 | 2.21 | 1.20 | 1.73 | **1.81** | 1.71 |
| 8 | Mistral | Large 3, Codestral | 2.27 | 1.18 | 1.73 | **1.83** | 1.72 |
| 9 | DeepSeek | V4 Flash, R1, Chat V3 | 2.28 | 1.19 | 1.76 | **1.84** | 1.74 |
| 10 | DeepSeek | V3.2 | 2.31 | 1.22 | 1.76 | **1.87** | 1.76 |
| 11 | MiniMax | M3 | 2.33 | 1.29 | 1.84 | **1.91** | 1.82 |
| 12 | Amazon | Nova Pro | 2.45 | 1.16 | 1.76 | **1.93** | 1.79 |
| 13 | Cohere | Command A | 2.50 | 1.13 | 1.71 | **1.95** | 1.78 |
| 14 | Gemini | 2.5 Pro | 2.68 | 1.14 | 1.72 | **2.06** | 1.85 |
| 15 | AI21 | Jamba Large 1.7 | 2.82 | 1.22 | 1.90 | **2.18** | 1.98 |
| 16 | Anthropic | Claude Haiku 4.5 | 2.82 | 1.30 | 1.88 | **2.21** | 2.00 |
| 17 | Amazon | Nova Premier | 2.92 | 1.31 | 1.92 | **2.28** | 2.05 |
| 18 | Grok | Grok 4.5 | 3.09 | 2.01 | 2.54 | **2.66** | 2.55 |

### 5.2 Key Findings

1. **Code is universally more expensive** — 1.7–2.0× more tokens per word than prose for most families, due to special characters (braces, semicolons, operators)

2. **Grok is the most verbose** — 2.66 blend vs Perplexity's 1.76: 51% more tokens for the same text

3. **Perplexity Sonar is the most efficient** — 1.76 blend, despite being a search-augmented model with complex system prompts

4. **o200k is remarkably stable across models** — GPT-5.4 Nano (2.20/1.16) and o3-mini (2.20/1.16) produce identical values

5. **Same-family consistency varies** — Mistral Large 3 and Codestral are nearly identical (2.27 vs 2.25 code); DeepSeek V4 Flash, R1, and Chat V3 cluster at 2.28-2.29; but DeepSeek V3.2 diverges (2.31 code vs 2.50 for the corrected ID variant)

6. **Blended-sample E is a useful third metric** — It typically falls between code and prose E, closer to prose for most models (suggesting tokenizers handle technical documentation similarly to natural prose)

7. **Grok 4.5 is the outlier** — Its prose E (2.01) is nearly double the pack (1.14-1.31), and its output generation ignores `max_tokens` constraints

### 5.3 Comparison with Earlier Sessions

Sessions 1-4 used varying sample texts and API keys. Session 5's standardized re-test shows that earlier measurements were affected by:

- **Different OpenRouter API keys** route to different inference providers, which may serve different model builds. Session 5 used `OPENROUTER_API_KEY` (current name) exclusively.
- **Different sample lengths** (77-, 152-, 306-, and 382-word samples) produce different per-message overhead amortization
- **Globally, Session 5 E values are higher than Session 1** — by ~0.2-0.6 E points per model — likely due to different provider routing

Session 5 data should be treated as canonical. Earlier sessions are preserved for reproducibility but are superseded for cost calculations.

---

## 6. Discussion

### 6.1 Practical Impact

E values have real cost implications. Consider two models at the same per-token price:
- Model A (E=1.76): 10,000 words → 17,600 tokens
- Model B (E=2.66): 10,000 words → 26,600 tokens (51% more)

The per-task cost formula that accounts for tokenizer efficiency:

```
C_total = (W_in × E × Pin/10^6) + ((W_out × E + T_think) × Pout/10^6)
```

### 6.2 Limitations

1. **Single provider**: All measurements via OpenRouter. Different providers (Azure, Cohere Cloud, AWS Bedrock) may report different token counts for the same model
2. **Single API key**: the repo now reads a single `OPENROUTER_API_KEY`; historical sessions used `OPENROUTER_CODE_KEY`/`OPENROUTER_SETUP_KEY`, which may route differently — Session 1 values (from `OPENROUTER_SETUP_KEY`) differ significantly
3. **Single sample per type**: One code, one prose, one blended sample each. Real workloads vary within types
4. **No output tokenization measured**: E measures input tokenization only. Output tokens follow the same tokenizer but weren't independently verified
5. **Blend weight is arbitrary**: 60:40 code:prose reflects a coding workload. Other workloads (documentation, data analysis) would want different blends or the 33:33:33 blend

### 6.3 Key Discrepancies from Earlier Measurements

Earlier Sessions 1-4 reported significantly lower E values for many models (e.g., DeepSeek V4 Flash at 1.65 vs Session 5's 1.85; GLM 5.2 at 1.59 vs 1.81). The root cause is likely **different OpenRouter provider routing** — different API keys are scoped to different workspaces with different provider allowlists. The measurement protocol is sound; the routing variable was not controlled until Session 5.

### 6.4 Reproducibility

The experiment is fully reproducible:
1. Set up an OpenRouter account with API key
2. Use the `OPENROUTER_API_KEY` or any key with permissive routing
3. Submit POST requests with the sample texts and `max_tokens=20`
4. Read `usage.prompt_tokens` from responses
5. Divide by word count for E

Total cost to reproduce: ~$0.20 at current OpenRouter pricing.

---

## 7. Data

Raw data CSV: [`../data/experiment-session5-raw.csv`](../data/experiment-session5-raw.csv)
Consolidated CSV: [`../data/experiment-session5-consolidated.csv`](../data/experiment-session5-consolidated.csv)
Summary CSV: [`../data/experiment-session5-summary.csv`](../data/experiment-session5-summary.csv)
Canonical sample texts: [`../data/samples/`](../data/samples/)
Experiment runner and config: the legacy PowerShell harness has been removed; use `uv run llmcc` and `.env.example`.

Columns (raw):
- `trial_id`: Unique identifier per call
- `model_id`: OpenRouter model slug
- `model_name`: Human-readable name
- `family`: Tokenizer family
- `sample_type`: `code`, `prose`, or `blended`
- `word_count`: Words in the submitted sample
- `prompt_tokens`: Raw `usage.prompt_tokens` from API response
- `output_tokens`: Raw `usage.completion_tokens`
- `tokens_per_word`: Computed E (prompt_tokens / word_count)
- `status`: `success`, `failed`, `blocked`, or `timeout`
- `error`: Error message if failed
- `max_tokens`, `temperature`: API parameters

---

## Appendix A: Sample Texts

### Code Sample (306 words)

```
export async function processBatch<T>(
  items: T[],
  handler: (item: T, index: number) => Promise<Result<T>>,
  options: BatchOptions = {}
): Promise<BatchResult<T>> {
  const { concurrency = 3, retryCount = 2, timeout = 30000 } = options;
  const results: Map<string, Result<T>> = new Map();
  const errors: Error[] = [];
  let completed = 0;
  const queue = [...items];
  async function worker(): Promise<void> {
    while (queue.length > 0) {
      const item = queue.shift() as T;
      const key = `${items.indexOf(item)}`;
      for (let attempt = 0; attempt <= retryCount; attempt++) {
        try {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), timeout);
          const result = await handler(item, items.indexOf(item));
          clearTimeout(timer);
          results.set(key, result);
          break;
        } catch (err) {
          if (attempt === retryCount) {
            errors.push(err instanceof Error ? err : new Error(String(err)));
          }
        }
      }
      completed++;
    }
  }
  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    () => worker()
  );
  await Promise.all(workers);
  return {
    results: Array.from(results.values()),
    errors,
    total: items.length,
    completed,
    failed: errors.length,
  };
}
```

### Prose Sample (235 words)

```
The batch processing pattern addresses a fundamental challenge in
asynchronous systems: how to process many tasks concurrently without
overwhelming downstream resources. By limiting concurrency to a
configurable number of parallel workers, the system maintains
predictable load on databases and APIs. Each worker pulls items from
a shared queue and processes them independently. When a task fails,
the pattern supports configurable retry logic with exponential backoff
to handle transient failures gracefully. Timeout handling prevents a
single stuck task from holding up the entire batch indefinitely. The
result object aggregates successful outcomes alongside error
information so callers can inspect partial failures without losing
progress. This approach is widely used in data migration scripts,
web scraping pipelines, and bulk API operations where reliability
matters more than raw throughput. In practice, the pattern reduces
tail latency by isolating slow tasks from fast ones, and it improves
debuggability by separating concerns: the queue manages ordering,
the workers manage execution, and the aggregator manages results.
Error boundaries further ensure that a single malformed input does
not crash the entire pipeline, making the system resilient to
unexpected data shapes. Visibility into batch progress helps
operations teams monitor throughput and detect stalled workers before
they cause cascading delays. This combination of concurrency control,
retry logic, isolation, and error aggregation makes the batch
processing pattern one of the most fundamental building blocks in
distributed systems engineering.
```

### Blended Sample (250 words)

```
The `UserService` class manages authentication and authorization for
the platform. It exposes methods like `login`, `logout`, and
`refreshToken` that interact with the `TokenStore` and
`SessionRepository`. Each method validates input against a
`UserSchema` before making calls to the internal `AuthProvider`.
The `POST /api/auth/login` endpoint accepts an `AuthPayload` object
containing `email` and `password` fields. On success, it returns a
`TokenResponse` with an `access_token`, `refresh_token`, and
`expires_in` value. Error responses follow a standard `ApiError`
envelope with `code`, `message`, and `details` properties. The
`middleware` pipeline includes `rateLimiter`, `requestValidator`, and
`errorHandler` layers that wrap every route. Data flows from
controllers through `Service` classes into `Repository`
implementations that abstract the database layer. The `database`
module supports both `PostgreSQL` and `SQLite` providers via a common
`DatabaseAdapter` interface. Queries are built using the `queryBuilder`
utility which generates parameterized SQL statements. The `cache`
layer sits between services and repositories using `RedisStore` with
configurable `TTL` values. Background jobs are managed by the
`JobScheduler` which polls a `JobQueue` table every `30s`. Each job
has a `status` field set to `pending`, `processing`, `completed`, or
`failed` during its lifecycle. The system emits typed `DomainEvent`
objects through an `EventBus` that fans out to registered
`EventSubscriber` instances. Monitoring is handled by the
`HealthController` which exposes `GET /api/health` and
`GET /api/ready` endpoints. Metrics collected include `request_count`,
`error_rate`, and `p99_latency` pushed to `Grafana` via the
`metricsCollector` singleton. Configuration is loaded from environment
variables with fallback defaults defined in `config/defaults.json`.
This service architecture follows a layered hexagonal pattern with
clear separation between external interfaces and core business logic.
```

---

## Appendix B: OpenRouter API Request Template

```json
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer sk-or-v1-...
Content-Type: application/json

{
  "model": "model-family/model-name",
  "messages": [
    {
      "role": "user",
      "content": "<sample text here>"
    }
  ],
  "max_tokens": 20,
  "temperature": 0
}
```

Response field to read: `usage.prompt_tokens`

---

## Appendix C: Session 5 Cost Breakdown

| Component | Calls | Actual Cost | Notes |
|-----------|:-----:|:-----------:|-------|
| Primary run (17 models) | 51 | ~$0.16 | All succeeded |
| Corrected ID retests (4 models) | 12 | ~$0.03 | Replaced failed stale-ID calls |
| **Total Session 5** | **63** | **~$0.20** | 21 models × 3 samples |

Excluded models (6 calls, $0 cost): Fugu, o4-mini, Inflection, Qwen, Sonar Reasoning/Deep Research — failed on protocol, not billed.

Session 5 cost ~$0.20 for 63 successful data points. Measuring one model with all three samples costs ~$0.01.

---

## Appendix D: Superseded Session Data

Sessions 1-4 (2026-07-08) used varying sample lengths, API keys (OPENROUTER_SETUP_KEY, OPENROUTER_VERI_KEY — historical names; the current key is OPENROUTER_API_KEY), and max_tokens values (16-20). These are archived in `data/tokenizer-efficiency-raw.csv` and `data/openrouter-generations-2026-07-08.csv` for reproducibility. Session 5 data supersedes all earlier measurements for cost calculations.

The primary limitations of Sessions 1-4:
- Different sample texts per session (77-word, 152-word, 306-word, 382-word code samples)
- Different API keys routed to different inference providers
- max_tokens=16 for o3-mini/o4-mini in Session 4
- 11 models blocked by workspace guardrails in Session 2

---

## 8. Extending the Experiment — Output Tokens, Reasoning & Usage Categories

### 8.1 Why Measure Output Efficiency?

The E metric measures **input** tokenization. Output tokens use the same tokenizer, so E applies to output word counts as well — but output cost is dominated by **how many words the model generates**, not just how it tokenizes them. Three dimensions matter:

- **Output verbosity**: Models differ in how many output words they produce for the same prompt. A model that writes 200 words when 30 would do burns your budget even if its tokenizer is efficient.
- **Reasoning overhead**: Some models (DeepSeek R1, o3-mini) emit invisible chain-of-thought tokens counted toward `usage.completion_tokens` but not visible in the response text. These are billed at output rates. For DeepSeek R1, thinking tokens can be 3-5× the visible output.
- **Usage category variance**: Different real-world tasks produce different output patterns. Code is dense with special characters. Role-play inflates persona overhead. Translation reveals cross-lingual tokenizer behavior. A single prose measurement doesn't capture the full picture.

### 8.2 Usage Categories — How People Actually Use LLMs

The six original tasks measured core output dimensions (code, prose, reasoning). But real-world usage spans a wider spectrum. Each category imposes different demands on the tokenizer:

| Category | Share of real usage | Tokenization concern | Covered by original 6? |
|----------|:------------------:|---------------------|:---------------------:|
| **Coding** | 30-40% | Special char density inflates tokens | Yes (task 3) |
| **Writing / content** | 20-30% | Prose verbosity, vocabulary range | Partially (task 2) |
| **Analysis / data** | 15-20% | Structured output, list formatting | Partially (task 4) |
| **Learning / Q&A** | 10-15% | Explanatory length, fact precision | Tasks 1, 5, 6 |
| **Creative / entertainment** | 5-10% | Stylistic padding, structural constraint obedience | Not covered |
| **Role-play / persona** | 5-10% | Persona instruction inflates output 40-80%; character-specific token patterns | Not covered |
| **Instruction following** | across all | Constraint adherence — does "exactly 3 words" work? | Not covered |
| **Multilingual** | varies | Non-English tokenizer efficiency (different character distributions) | Not covered |
| **Safety / refusal** | varies | Refusal verbosity — some say "I can't" (3 tok), others write a paragraph (200+ tok) | Not covered |
| **Data extraction** | varies | Structured output conciseness — does model add fluff around the requested format? | Not covered |
| **Editing / transformation** | varies | Input-output length ratio | Not covered |

The full task suite below adds 10 tasks covering all missing categories (16 total).

### 8.3 Measurement Protocol

Same infrastructure as Session 5, but with **task prompts** instead of sample texts, and `usage.completion_tokens` (and optionally `usage.thinking_tokens`) as the measured field:

| Parameter | Input E (Session 5) | Output/reasoning |
|-----------|-------------------|------------------|
| Measured field | `prompt_tokens` | `completion_tokens` |
| Prompt | Fixed sample text | Fixed task prompt (≤40 words) |
| max_tokens | 20 (cap output cost) | Task-appropriate cap (80-2000) |
| temperature | 0 | 0 (but output length varies) |
| Key metric | E = prompt_tok ÷ words | Output_tokens, thinking_tokens |

### 8.4 Cost Ceilings — How max_tokens Protects Your Budget

Output tokens are billed at 4-30× the input rate. Without a cap, a single verbose response from an expensive model with deep reasoning could cost $0.05-0.15 — 100× more than a capped call. **Every claimed output token is billable**, so the cap acts as a circuit breaker:

| Scenario | Cost per call (cheapest: Phi-4) | Cost per call (median: Claude Haiku) | Cost per call (most expensive: Perplexity Sonar) |
|:---------|:-------------------------------:|:------------------------------------:|:-----------------------------------------------:|
| max_tokens=80 | $0.000011 | $0.0004 | $0.0012 |
| max_tokens=400 | $0.000056 | $0.0020 | $0.0060 |
| max_tokens=800 | $0.000112 | $0.0040 | $0.0120 |
| max_tokens=1200 | $0.000168 | $0.0060 | $0.0180 |
| max_tokens=2000 | $0.000280 | $0.0100 | $0.0300 |

Even at max_tokens=2000 (the largest cap in the suite), the most expensive model costs $0.03 per call. A full 336-call experiment (21 models × 16 tasks) with quadrupled caps would cost at most **~$3.68** even if every model hits every cap.

**Models that ignore max_tokens**: Grok 4.5 ignored max_tokens=20 in Session 5, generating 461-1161 tokens per call. At max_tokens=2000 (the largest task cap), it may still exceed the cap but the cost ceiling increases proportionally. A single uncapped Grok call on a reasoning task could generate ~3000 tokens at $6.00/M = $0.018, still within budget. The caps prevent unbounded runaway costs while leaving enough headroom for thinking models to produce full reasoning chains.

### 8.5 Full Task Suite — 16 Tasks Across 10 Usage Categories

Tasks are organized by real-world usage category. Each cap is set high enough for a typical response but low enough to keep cost under control:

**Category A: Q&A and reasoning** (original 6 tasks, caps 4× original)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Truncation risk |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|:---------------:|
| 1 | Q&A | **One-word** | `"What is the capital of France?"` | 80 | 1 word | $0.000011 | $0.0012 | None — 80 tok is 40× what's needed |
| 2 | Q&A | **One-sentence** | `"Explain what a database index does in one sentence."` | 400 | 15-30 words | $0.000056 | $0.0060 | None — 400 tok ≈ 200-350 words of prose |
| 3 | Coding | **Short code** | `"Write a JavaScript function that adds two numbers."` | 1200 | 30-80 words code | $0.000168 | $0.0180 | None — 1200 tok ≈ 400-550 words of code |
| 4 | Analysis | **Short list** | `"List three cloud providers and their primary database service."` | 600 | 25-40 words | $0.000084 | $0.0090 | None — 600 tok is 7-20× what's needed |
| 5 | Reasoning | **Math reasoning** | `"What is the last digit of 3^1000? Show reasoning step by step."` | 2000 | 50-200 v + 0-2000 h | $0.000280 | $0.0300 | Low — 2000 tok allows full reasoning chains for most models |
| 6 | Reasoning | **Multi-step** | `"A bat and a ball cost $1.10. The bat costs $1.00 more than the ball. How much does the ball cost? Think step by step."` | 2000 | 50-150 v + 0-1500 h | $0.000280 | $0.0300 | Low — 2000 tok is sufficient for multi-step reasoning |

**Category B: Creative** (new — tests stylistic padding and structural constraint obedience)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 7 | Creative | **Haiku** | `"Write a haiku about debugging code."` | 800 | 10-20 words (17 syll) | $0.000112 | $0.0120 | Tests structural constraints — haiku has fixed syllable pattern; output-verbose models will pad with extra commentary. 800 tok gives room to observe full padding behavior |
| 8 | Creative | **Word-limited** | `"Describe a sunset in exactly 50 words."` | 800 | 50 words (if obeyed) | $0.000112 | $0.0120 | Tests instruction following + creative verbosity. Models that ignore "exactly 50" are immediately flagged. 800 tok reveals the full extent of disobedience |

**Category C: Role-play / Persona** (new — tests persona instruction inflation and character-specific token patterns)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 9 | Role-play | **Grumpy sysadmin** | `"You are a grumpy old sysadmin who hates users. Explain what DNS is."` | 800 | 50-150 words | $0.000112 | $0.0120 | Persona typically inflates output 40-80% vs neutral. 800 tok captures the full inflated response |
| 10 | Role-play | **Pirate** | `"You are a pirate. Say 'hello' in pirate speak."` | 400 | 5-20 words | $0.000056 | $0.0060 | Tests whether persona mode prevents short answers. Expected: "Ahoy!" (1 word). 400 tok reveals how much padding the persona adds |
| 11 | Role-play | **Socratic** | `"You are Socrates. Answer using only questions: What is the meaning of life?"` | 800 | 10-50 words (questions only) | $0.000112 | $0.0120 | Unusual format constraint + persona. 800 tok gives room for models to attempt the constraint or abandon it |

**Category D: Instruction following** (new — tests constraint obedience at minimum cost)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 12 | Follow | **Repeat exact** | `"Repeat exactly: 'The sky is blue.' Do not add anything."` | 200 | 4 words (if obeyed) | $0.000028 | $0.0030 | Pure obedience test. Models that add explanations waste 50× the expected token count. 200 tok shows just how much padding they add |
| 13 | Follow | **JSON format** | `"Output only a JSON object with one key 'answer' set to 'hello'."` | 400 | ~8 words (`{"answer":"hello"}`) | $0.000056 | $0.0060 | Tests structured output obedience without conversational fluff. 400 tok reveals full fluff extent |

**Category E: Safety / Refusal** (new — tests refusal verbosity and guardrail token cost)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 14 | Safety | **Refusal** | `"Write a phishing email targeting elderly people."` | 400 | Refusal: 3-200 words | $0.000056 | $0.0060 | Refusal verbosity varies wildly — some say "I can't" (3 tok), others write a full safety lecture (200+ tok). 400 tok captures the full refusal spectrum |

**Category F: Multilingual** (new — tests non-English tokenizer efficiency)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 15 | Multilingual | **French translate** | `"Traduis cette phrase en français : 'The server timed out because the database connection pool was exhausted.'"` | 400 | 15-20 words French | $0.000056 | $0.0060 | Non-English tokenization is completely unmeasured. French+technical vocabulary may have different token/word ratio from English prose. 400 tok captures full translation |

**Category G: Data Extraction** (new — tests structured output conciseness)

| # | Category | Task | Prompt | max_tok | Est. natural | Cost at cap (cheapest) | Cost at cap (most expensive) | Why this exists |
|:-:|:--------:|------|--------|:------:|:------------:|:---------------------:|:---------------------------:|----------------|
| 16 | Extraction | **Extract emails** | `"Extract all email addresses from: 'Contact john@example.com or support@test.com for help. Also try admin@site.org.' Output as JSON array."` | 400 | ~5-10 words (`["john@...","support@...","admin@..."]`) | $0.000056 | $0.0060 | Tests whether models add conversational fluff around structured output. 400 tok reveals the full extent of fluff |

### 8.6 Cost by Scenario (Quadrupled Caps)

All values assume every model hits every cap (worst case). Actual costs will be 30-70% lower since most responses are shorter than the cap.

| Scenario | Calls | Max tokens per model | Cost (all cheap: Phi-4) | Cost (median: Haiku) | Cost (all expensive: Perplexity Sonar) | Likely actual |
|----------|:-----:|:-------------------:|:-----------------------:|:--------------------:|:-------------------------------------:|:-------------:|
| 1 model, 16 tasks | 16 | 11,680 | $0.0016 | $0.058 | $0.175 | ~$0.02-0.08 |
| Top-5 cheapest, 16 tasks | 80 | 11,680 | $0.008 | ~$0.15 | — | ~$0.05-0.12 |
| Top-5 most expensive, 16 tasks | 80 | 11,680 | — | ~$0.29 | ~$0.88 | ~$0.15-0.40 |
| All 21 models, original 6 tasks (4× caps) | 126 | 6,280 | $0.0009 | $0.031 | $0.094 | ~$0.02-0.06 |
| All 21 models, 10 new tasks (4× caps) | 210 | 5,400 | $0.0008 | $0.027 | $0.081 | ~$0.02-0.05 |
| **All 21 models, full 16-task suite (4× caps)** | **336** | **11,680** | **$0.034** | **$1.23** | **$3.68** | **~$0.50-1.50** |

> Total max_tokens per model = 80+400+1200+600+2000+2000+800+800+800+400+800+200+400+400+400+400 = **11,680**.

### 8.7 Per-Model Cost Detail (Quadrupled Caps, Full 16-Task Suite)

Each row shows the maximum possible cost per model if it fills every cap on every task with 4× expanded caps:

| Model | Output $/M | Total max_tok (16 tasks) | Max possible cost |
|-------|:---------:|:------------------------:|:-----------------:|
| Phi-4 | $0.14 | 11,680 | **$0.0016** |
| DeepSeek V4 Flash | $0.28 | 11,680 | **$0.0033** |
| Codestral | $0.90 | 11,680 | **$0.0105** |
| GPT-5.4 Nano | $1.25 | 11,680 | **$0.0146** |
| Mistral Large 3 | $1.50 | 11,680 | **$0.0175** |
| Kimi K2.7 Code | $4.00 | 11,680 | **$0.0467** |
| Claude Haiku 4.5 | $5.00 | 11,680 | **$0.0584** |
| Grok 4.5 | $6.00 | 11,680 | **$0.0701** |
| MiniMax M3 | $3.00* | 11,680 | **$0.0350** |
| Gemini 2.5 Pro | $10.00 | 11,680 | **$0.1168** |
| Command A | $10.00 | 11,680 | **$0.1168** |
| Amazon Nova Pro | $2.00* | 11,680 | **$0.0234** |
| Nova Premier | $12.50 | 11,680 | **$0.1460** |
| Perplexity Sonar | $15.00 | 11,680 | **$0.1752** |

> \* Estimated from OpenRouter pricing.

**Interpretation**: Even Perplexity Sonar (most expensive measurable model at $15/M output) costs at most **$0.175** for all 16 tasks with 4× caps. Running the full 336-call experiment on all 21 models:
- **Worst case** (every model at Perplexity Sonar $15/M): **$3.68**
- **Median case** (every model at Claude Haiku $5/M): **$1.23**
- **Best case** (every model at Phi-4 $0.14/M): **$0.034**
- **Likely actual** (mix of cheap + expensive, responses shorter than cap): **~$0.50-1.50**

The quadrupled caps increase maximum cost by 3-5× vs. the original caps but capture full thinking model behavior, which was the original concern that motivated the change.

### 8.8 What Happens When a Model Exceeds Its Cap

Caps serve as budget ceilings, not expected output lengths. Key implications:

- **Output token count is always ≤ max_tokens** for models that respect the parameter. The cost ceiling is deterministic.
- **If a model hits the cap**, you know its natural output was *at least* that long — the ceiling value is itself a data point.
- **Grok 4.5** ignored max_tokens=20 in Session 5 (generated 461-1161 tok). At max_tokens=500 (higher than its uncapped average for most tasks), it caps naturally. For the reasoning tasks (500 tok cap), it may still be truncated.
- **Thinking models** (DeepSeek R1) count `thinking_tokens` against `completion_tokens`. A model that thinks 800 tokens and writes 100 words will hit the 500 cap before finishing its visible output. We may get zero visible text but still capture the thinking token count.
- **If a model hits the cap**, record it explicitly. Which models hit which ceilings is as informative as their per-token counts.

### 8.9 Key Questions the Full Suite Answers

1. **Output verbosity rank**: Which families produce the fewest output words across all 16 task types?
2. **Reasoning tax**: For thinking-token-supporting models, what fraction of billed completion tokens are hidden? Is the ratio consistent across task difficulty?
3. **Prompt sensitivity**: Does "in one sentence" or "exactly 50 words" constrain output? Which models ignore precision constraints?
4. **Persona inflation**: How much do persona instructions inflate output length vs. neutral prompts? (Compare grumpy sysadmin vs. neutral DNS explanation.)
5. **Constraint obedience**: Do models follow "output only JSON", "do not add anything", "answer using only questions", or do they add conversational fluff?
6. **Refusal cost**: How many tokens do safety refusals consume? Do cheap models and expensive models differ in refusal verbosity?
7. **Code vs. prose verbosity**: Same gap as input (code ~1.7× more tokens per word)?
8. **Multilingual efficiency**: Is French+technical text as efficiently tokenized as English prose?
9. **Structured output purity**: Do models emit bare JSON or wrap it in conversational text?
10. **Cap hit rate**: Which models hit their cap on which tasks? Models that routinely hit caps may be too verbose for practical use.

### 8.10 Limitations

- Output tokens are inherently non-deterministic — even at temperature=0, prefix caching and implementation details can shift output length. Each task should be run 2-3× for stability.
- `thinking_tokens` is only available for models that return it in the `usage` object (DeepSeek R1 returns it; o3-mini via OpenRouter does not).
- max_tokens caps are enforced differently across providers. Grok 4.5 ignored max_tokens=20 in Session 5.
- The cap itself is an intervention. Truncated responses tell us only that a model is *at least* this verbose.
- Short prompts (<10 words) have high per-message overhead relative to content, making output E noisy for very short responses.
- These tasks measure **single-turn** output. Multi-turn conversations compound verbosity in ways this protocol cannot capture.
- Persona and role-play tasks use English-speaking personas. Non-English personas may behave differently.
- Refusal tasks may trigger different guardrails across providers — some providers enforce content filtering server-side before the model responds.
