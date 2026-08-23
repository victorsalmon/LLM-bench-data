# DeepInfra provider

The benchmark CLI supports DeepInfra through its OpenAI-compatible chat
completions endpoint. Set `DEEPINFRA_API_KEY` in `.env`, then select the
provider explicitly:

```powershell
uv run llmcc appraise deepseek-v4-flash-max --provider deepinfra
```

DeepInfra configuration:

- Base URL: `https://api.deepinfra.com/v1/openai`
- Authentication: `Authorization: Bearer $DEEPINFRA_API_KEY`
- Model ID: `deepseek-ai/DeepSeek-V4-Flash-0731`
- Catalog slug: `deepseek-v4-flash-max`
- Published pricing: $0.08/M input, $0.18/M output, $0.016/M cached input

The model ID is deliberately kept separate from the OpenRouter ID. The same
catalog model can therefore be benchmarked through either provider without
changing the experiment definition.

DeepInfra's API returns OpenAI-compatible `usage` fields, which the benchmark
pipeline uses for token counts and cost calculations. The API key is loaded
from the environment as a secret and is never written to measurement files.

See [DeepInfra's quickstart](https://docs.deepinfra.com/quickstart) for the
provider endpoint and [the model catalog](https://deepinfra.com/) for current
availability and pricing.
