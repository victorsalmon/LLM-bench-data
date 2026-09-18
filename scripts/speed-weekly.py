"""Weekly speed consistency benchmark for non-frontier coding/agentic LLMs.

Runs a small tokenization + coding challenge against a configurable model list
for a configurable number of rounds. The default manual run is 24 hourly
rounds; the Windows Scheduled Task runs one round per trigger, eight triggers
per 8-day snapshot. Writes a resumable time-of-day CSV. Supports multi-provider
benchmarking (OpenRouter, DeepInfra, OpenCode/Alibaba) so provider speed/cost
can be compared.

Designed to be invoked:

- manually for a one-off 24h run:
    uv run python scripts/speed-weekly.py
- via the Windows Scheduled Task (one round per trigger):
    uv run python scripts/speed-weekly.py --rounds 1 --no-wait
- to generate or refresh the model list:
    uv run python scripts/speed-weekly.py --generate-config
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from llm_bench_data.clients.alibaba import AlibabaClient
from llm_bench_data.clients.deepinfra import DeepInfraClient
from llm_bench_data.clients.openrouter import OpenRouterClient
from llm_bench_data.core.config import Settings
from llm_bench_data.core.models import ChatRequest, Message, Model, ProviderPricing


DEFAULT_PROMPT = """A code tokenizer splits this Python snippet into tokens:

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

1. Estimate the token count and include it as a comment at the top.
2. Write a small Python module with these three functions:
   - `fibonacci(n)` returning the nth Fibonacci number
   - `is_palindrome(s)` returning True/False
   - `factorial_iterative(n)` returning n!
3. Add a short `if __name__ == "__main__":` block that prints the first 50 Fibonacci numbers.
Return only the code and the token-count comment, no explanations."""

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalogs" / "models.yaml"
MODELS_JSON_PATH = REPO_ROOT / "models.json"
DEFAULT_CONFIG_PATH = REPO_ROOT / "data" / "speed-weekly" / "models.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "speed-weekly"
DEFAULT_PROVIDERS = ["openrouter", "deepinfra", "alibaba"]
# Slug -> set of providers to skip when generating the default weekly config.
# This is a short-term override so a model remains in the catalog but is not
# benchmarked on a particular provider right now.
DEFAULT_PROVIDER_EXCLUSIONS: dict[str, set[str]] = {
    "deepseek-v4-flash": {"alibaba"},
}
PROVIDER_CLIENTS = {
    "openrouter": OpenRouterClient,
    "deepinfra": DeepInfraClient,
    "alibaba": AlibabaClient,
}
PROVIDER_LABELS = {
    "openrouter": "openrouter",
    "deepinfra": "deepinfra",
    "alibaba": "opencode",
}
CSV_COLUMNS = [
    "run_date",
    "hour_pst",
    "hour_utc",
    "slug",
    "provider",
    "model_id",
    "model_name",
    "tier",
    "max_tokens",
    "prompt_tokens",
    "output_tokens",
    "elapsed_ms",
    "tokens_per_sec",
    "cost",
    "status",
    "error",
    "measured_at",
]


def load_models(config_path: Path) -> list[dict[str, Any]]:
    """Load the weekly model list from JSON."""
    with config_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        models = data.get("models", [])
    elif isinstance(data, list):
        models = data
    else:
        raise ValueError(f"Unexpected shape in {config_path}")

    # Backward compat: migrate flat openrouter-only entries to providers dict.
    for m in models:
        if "providers" not in m and "openrouter_id" in m:
            m["providers"] = {
                "openrouter": {
                    "model_id": m["openrouter_id"],
                    "in_price": m.get("in_price"),
                    "out_price": m.get("out_price"),
                }
            }
    return models


def _pricing_to_float(pricing: ProviderPricing | dict[str, Any] | None, direction: str) -> float | None:
    if pricing is None:
        return None
    if isinstance(pricing, ProviderPricing):
        val = getattr(pricing, direction)
        return float(val) if val is not None else None
    if isinstance(pricing, dict):
        val = pricing.get(direction)
        return float(val) if val is not None else None
    return None


def _provider_price(
    provider: str,
    catalog_model,
    mjson_model: dict[str, Any] | None,
) -> tuple[float | None, float | None]:
    """Return (input_price, output_price) for a provider."""
    in_price: float | None = None
    out_price: float | None = None

    # 1. Catalog pricing for the provider.
    catalog_pricing = catalog_model.pricing.get(provider) if catalog_model.pricing else None
    if catalog_pricing:
        in_price = _pricing_to_float(catalog_pricing, "input")
        out_price = _pricing_to_float(catalog_pricing, "output")

    # 2. models.json provider-specific pricing (e.g. openrouter_pricing, deepinfra_pricing).
    if mjson_model:
        for prov in (provider, "zen"):
            key = f"{prov}_pricing"
            if in_price is None:
                in_price = _pricing_to_float(mjson_model.get(key), "input")
            if out_price is None:
                out_price = _pricing_to_float(mjson_model.get(key), "output")

    # 3. Alibaba maps to Zen/OpenCode pricing.
    if provider == "alibaba" and catalog_model.zen_available and in_price is None and out_price is None:
        zen_pricing = catalog_model.pricing.get("zen") if catalog_model.pricing else None
        if zen_pricing:
            in_price = _pricing_to_float(zen_pricing, "input")
            out_price = _pricing_to_float(zen_pricing, "output")

    return in_price, out_price


def _has_provider_id(catalog_model, provider: str) -> bool:
    attr = f"{provider}_id"
    return bool(getattr(catalog_model, attr, None))


def build_default_config(output_path: Path) -> list[dict[str, Any]]:
    """Derive the default weekly model list from models.json + catalogs/models.yaml."""
    models_json = json.loads(MODELS_JSON_PATH.read_text(encoding="utf-8"))
    mjson_models = models_json.get("models", {})
    catalog_raw = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_models = [Model.model_validate(m) for m in catalog_raw.get("models", [])]

    def score(bench: dict[str, Any], key: str) -> float | None:
        v = bench.get(key)
        return v.get("score") if isinstance(v, dict) else None

    code_keywords = {
        "coding",
        "code",
        "agent",
        "agentic",
        "swe",
        "software",
        "task",
        "implementation",
        "refactor",
        "review",
        "engineering",
        "programming",
        "long-term",
        "long context",
        "reasoning",
    }

    selected: list[dict[str, Any]] = []
    for catalog_model in catalog_models:
        if catalog_model.tier == "complex":
            continue

        mjson_model = mjson_models.get(catalog_model.slug)
        if not mjson_model:
            continue

        bench = mjson_model.get("benchmarks", {})
        swe = score(bench, "swe_bench_pro")
        tb = score(bench, "terminal_bench_2_1")
        text = f"{mjson_model.get('specialty', '')} {mjson_model.get('strategy_note', '')}".lower()
        is_code = any(kw in text for kw in code_keywords)

        if not ((swe is not None and swe >= 50) or (tb is not None and tb >= 60) or is_code):
            continue

        providers: dict[str, dict[str, Any]] = {}
        for provider in DEFAULT_PROVIDERS:
            if provider in DEFAULT_PROVIDER_EXCLUSIONS.get(catalog_model.slug, set()):
                continue
            if not _has_provider_id(catalog_model, provider):
                continue
            in_price, out_price = _provider_price(provider, catalog_model, mjson_model)
            if in_price is None or out_price is None:
                continue
            providers[provider] = {
                "model_id": getattr(catalog_model, f"{provider}_id"),
                "in_price": in_price,
                "out_price": out_price,
                "label": PROVIDER_LABELS.get(provider, provider),
            }

        if not providers:
            continue

        selected.append(
            {
                "slug": catalog_model.slug,
                "name": mjson_model.get("name"),
                "tier": catalog_model.tier,
                "providers": providers,
                "swe_bench_pro": swe,
                "terminal_bench_2_1": tb,
                "context_window": mjson_model.get("context_window"),
                "reasoning_effort": catalog_model.reasoning_effort,
            }
        )

    # Sort by cheapest provider output price (then slug for stability).
    selected.sort(
        key=lambda x: (
            min((p["out_price"] for p in x["providers"].values()), default=999),
            x["slug"],
        )
    )
    return selected


def write_config(models: list[dict[str, Any]], output_path: Path) -> None:
    """Write the model list config to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": "Edit this list to add or remove models/providers from the weekly speed benchmark.",
        "models": models,
    }
    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(output_path)


def estimate_cost(
    models: Sequence[dict[str, Any]],
    prompt_tokens: int,
    output_tokens: int,
    rounds: int,
) -> float:
    """Estimate the total cost for a weekly run in USD."""
    total = 0.0
    for m in models:
        for provider, p in m.get("providers", {}).items():
            in_price = p.get("in_price") or 0.0
            out_price = p.get("out_price") or 0.0
            total += rounds * (prompt_tokens * in_price + output_tokens * out_price) / 1e6
    return total


def load_existing_rows(csv_path: Path) -> list[dict[str, Any]]:
    """Load any rows already written today so the run can resume."""
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def row_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (row.get("hour_utc", ""), row.get("slug", ""), row.get("provider", ""))


def atomic_csv_write(rows: Sequence[dict[str, Any]], csv_path: Path) -> None:
    """Write the CSV atomically."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp.replace(csv_path)


def client_for_provider(provider: str, settings: Settings) -> OpenRouterClient | None:
    """Return a client for *provider*, or None if credentials are missing."""
    try:
        cls = PROVIDER_CLIENTS[provider]
        return cls(settings)
    except ValueError:
        return None


def run_round(
    clients: dict[str, OpenRouterClient],
    items: Sequence[dict[str, Any]],
    prompt: str,
    max_tokens: int,
    sleep_s: float,
    hour_pst: int,
    hour_utc: int,
    run_date: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Benchmark every model/provider once for a single hour."""
    rows: list[dict[str, Any]] = []
    for item in items:
        provider = item["provider"]
        model_id = item["model_id"]
        if dry_run:
            print(f"  [dry-run] {item['slug']} :: {provider} ({model_id})")
            continue

        client = clients.get(provider)
        if not client:
            rows.append(
                {
                    "run_date": run_date,
                    "hour_pst": f"{hour_pst:02d}",
                    "hour_utc": f"{hour_utc:02d}",
                    "slug": item["slug"],
                    "provider": PROVIDER_LABELS.get(provider, provider),
                    "model_id": model_id,
                    "model_name": item["name"],
                    "tier": item["tier"],
                    "max_tokens": max_tokens,
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "elapsed_ms": 0,
                    "tokens_per_sec": 0.0,
                    "cost": "0.000000",
                    "status": "error",
                    "error": f"No client available for {provider}",
                    "measured_at": datetime.now(UTC).isoformat(),
                }
            )
            continue

        request = ChatRequest(
            model_id=model_id,
            messages=[Message(role="user", content=prompt)],
            max_tokens=max_tokens,
            temperature=0.0,
            reasoning_effort=item.get("reasoning_effort"),
        )
        try:
            response = client.chat(request)
            elapsed = max(response.elapsed_ms, 1)
            tokens_per_sec = response.completion_tokens * 1000 / elapsed
            in_price = item.get("in_price") or 0.0
            out_price = item.get("out_price") or 0.0
            cost = (response.prompt_tokens * in_price + response.completion_tokens * out_price) / 1e6
            rows.append(
                {
                    "run_date": run_date,
                    "hour_pst": f"{hour_pst:02d}",
                    "hour_utc": f"{hour_utc:02d}",
                    "slug": item["slug"],
                    "provider": PROVIDER_LABELS.get(provider, provider),
                    "model_id": response.model_id,
                    "model_name": item["name"],
                    "tier": item["tier"],
                    "max_tokens": max_tokens,
                    "prompt_tokens": response.prompt_tokens,
                    "output_tokens": response.completion_tokens,
                    "elapsed_ms": response.elapsed_ms,
                    "tokens_per_sec": round(tokens_per_sec, 1),
                    "cost": f"{cost:.6f}",
                    "status": "success",
                    "error": "",
                    "measured_at": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "run_date": run_date,
                    "hour_pst": f"{hour_pst:02d}",
                    "hour_utc": f"{hour_utc:02d}",
                    "slug": item["slug"],
                    "provider": PROVIDER_LABELS.get(provider, provider),
                    "model_id": model_id,
                    "model_name": item["name"],
                    "tier": item["tier"],
                    "max_tokens": max_tokens,
                    "prompt_tokens": 0,
                    "output_tokens": 0,
                    "elapsed_ms": 0,
                    "tokens_per_sec": 0.0,
                    "cost": "0.000000",
                    "status": "error",
                    "error": str(exc)[:200],
                    "measured_at": datetime.now(UTC).isoformat(),
                }
            )
        if sleep_s > 0:
            time.sleep(sleep_s)
    return rows


def expand_items(
    models: Sequence[dict[str, Any]],
    selected_providers: Sequence[str],
) -> list[dict[str, Any]]:
    """Expand models into one dict per (model, provider) that is configured."""
    items: list[dict[str, Any]] = []
    for m in models:
        for provider in selected_providers:
            p = m.get("providers", {}).get(provider)
            if not p:
                continue
            items.append(
                {
                    "slug": m["slug"],
                    "name": m.get("name"),
                    "tier": m["tier"],
                    "provider": provider,
                    "model_id": p["model_id"],
                    "in_price": p.get("in_price"),
                    "out_price": p.get("out_price"),
                    "reasoning_effort": m.get("reasoning_effort"),
                }
            )
    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the model list JSON. (default: data/speed-weekly/models.json)",
    )
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help="Write the default model list and cost estimate, then exit.",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_PROMPT,
        help="Prompt to send to every model.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=250,
        help="Maximum completion tokens per call (default: 250).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=24,
        help="Number of hourly rounds to run (default: 24).",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Run all rounds immediately without sleeping between hours. Useful for cron.",
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=200,
        help="Milliseconds to sleep between model calls within a round (default: 200).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for the daily CSV (default: data/speed-weekly).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an existing daily CSV, skipping completed (hour, model, provider) triples.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and estimated cost without calling any APIs.",
    )
    parser.add_argument(
        "--providers",
        type=str,
        default=",".join(DEFAULT_PROVIDERS),
        help="Comma-separated providers to benchmark (default: openrouter,deepinfra,alibaba).",
    )
    args = parser.parse_args(argv)

    selected_providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    bad = [p for p in selected_providers if p not in PROVIDER_CLIENTS]
    if bad:
        print(f"Unknown providers: {bad}. Valid: {list(PROVIDER_CLIENTS)}")
        return 1

    if args.generate_config:
        models = build_default_config(args.models)
        write_config(models, args.models)
        provider_counts = {p: sum(1 for m in models if p in m.get("providers", {})) for p in DEFAULT_PROVIDERS}
        print(f"Wrote {len(models)} models ({sum(provider_counts.values())} model/provider pairs) to {args.models}")
        for out_tok, label in ((250, "consistency"), (500, "default"), (750, "accuracy")):
            # 24 rounds = hourly for 24h; 8 rounds = every 3h for 24h
            cost_8 = estimate_cost(models, 140, out_tok, 8)
            cost_24 = estimate_cost(models, 140, out_tok, 24)
            print(f"  ~{out_tok} output tokens ({label}): 8 rounds ${cost_8:.2f}/week, 24 rounds ${cost_24:.2f}/week")
        return 0

    if not args.models.exists():
        print(f"Model list not found: {args.models}")
        print("Run with --generate-config to create the default list.")
        return 1

    models = load_models(args.models)
    if not models:
        print(f"No models in {args.models}")
        return 1

    items = expand_items(models, selected_providers)
    if not items:
        print(f"No model/provider pairs to run for providers: {selected_providers}")
        return 1

    print(f"Loaded {len(items)} model/provider pairs for weekly speed benchmark")
    if args.dry_run:
        print(f"Prompt tokens (estimated): 140")
        print(f"Max output tokens: {args.max_tokens}")
        print(f"Rounds: {args.rounds}")
        print("Model/provider pairs:")
        for item in items:
            print(
                f"  {item['slug']} :: {item['provider']} -> {item['model_id']} "
                f"(out ${item.get('out_price', 0)}/M)"
            )
        cost_250 = estimate_cost(models, 140, 250, args.rounds)
        cost_500 = estimate_cost(models, 140, 500, args.rounds)
        cost_750 = estimate_cost(models, 140, 750, args.rounds)
        print(f"Estimated cost at 250 output tokens: ${cost_250:.2f}")
        print(f"Estimated cost at 500 output tokens: ${cost_500:.2f}")
        print(f"Estimated cost at 750 output tokens: ${cost_750:.2f}")
        return 0

    # Determine today's output file.
    start_time = datetime.now(UTC)
    run_date = start_time.strftime("%Y-%m-%d")
    csv_path = args.output_dir / f"speed-weekly-{run_date}.csv"

    settings = Settings()
    clients: dict[str, OpenRouterClient] = {}
    for provider in selected_providers:
        client = client_for_provider(provider, settings)
        if client:
            clients[provider] = client
        else:
            print(f"Warning: no API credentials for {provider}; skipping all {provider} calls")

    if not clients:
        print("No provider clients could be initialized. Check .env for API keys.")
        return 1

    items = [item for item in items if item["provider"] in clients]
    if not items:
        print("No model/provider pairs with available credentials.")
        return 1

    try:
        existing_rows = load_existing_rows(csv_path) if args.resume else []
        completed = {row_key(r) for r in existing_rows}
        all_rows: list[dict[str, Any]] = list(existing_rows)

        sleep_s = args.sleep / 1000.0
        prompt = args.prompt

        for round_idx in range(args.rounds):
            # Target the top of the current/future hour.
            if args.no_wait:
                target = start_time + timedelta(hours=round_idx)
            else:
                base = start_time.replace(minute=0, second=0, microsecond=0)
                target = base + timedelta(hours=round_idx)

            hour_utc = target.hour
            hour_pst = target.astimezone(ZoneInfo("America/Los_Angeles")).hour

            if not args.no_wait:
                now = datetime.now(UTC)
                if target > now:
                    wait = (target - now).total_seconds()
                    print(f"Round {round_idx + 1}/{args.rounds}: waiting {wait:.0f}s until {target.isoformat()} UTC")
                    time.sleep(max(0, wait))

            print(f"Round {round_idx + 1}/{args.rounds} UTC hour {hour_utc:02d} / PST hour {hour_pst:02d}")

            # Filter (hour, slug, provider) triples already completed.
            to_run = [
                item
                for item in items
                if (f"{hour_utc:02d}", item["slug"], item["provider"]) not in completed
            ]
            if not to_run:
                print("  All model/provider pairs already recorded for this hour; skipping.")
                continue

            rows = run_round(
                clients,
                to_run,
                prompt,
                args.max_tokens,
                sleep_s,
                hour_pst,
                hour_utc,
                run_date,
                dry_run=False,
            )
            all_rows.extend(rows)
            for r in rows:
                completed.add((r["hour_utc"], r["slug"], r["provider"]))
            atomic_csv_write(all_rows, csv_path)
            print(f"  Wrote {len(rows)} rows to {csv_path}")

        print(f"Done. {len(all_rows)} total rows in {csv_path}")
        return 0
    finally:
        for client in clients.values():
            client.close()


if __name__ == "__main__":
    sys.exit(main())
