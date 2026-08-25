"""Weekly speed consistency benchmark for non-frontier coding/agentic LLMs.

Runs a small tokenization + coding challenge against a configurable model list
once per hour for a configurable number of rounds (default 24). Writes a
resumable time-of-day CSV. Designed to be invoked:

- manually for a one-off 24h run:
    uv run python scripts/speed-weekly.py
- via a Tempo cron schedule every hour on the same day:
    uv run python scripts/speed-weekly.py --rounds 1 --no-wait
- to generate or refresh the model list:
    uv run python scripts/speed-weekly.py --generate-config
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from llm_cost_comparison.clients.openrouter import OpenRouterClient
from llm_cost_comparison.core.config import Settings
from llm_cost_comparison.core.models import ChatRequest, Message


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
CSV_COLUMNS = [
    "run_date",
    "hour_pst",
    "hour_utc",
    "slug",
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
        return data.get("models", [])
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected shape in {config_path}")


def build_default_config(output_path: Path) -> list[dict[str, Any]]:
    """Derive the default weekly model list from models.json + catalogs/models.yaml."""
    models = json.loads(MODELS_JSON_PATH.read_text(encoding="utf-8")).get("models", {})
    catalog = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8")).get("models", [])

    catalog_by_slug: dict[str, dict[str, Any]] = {}
    for m in catalog:
        slug = m["slug"]
        pricing = m.get("pricing", {})
        out = min(
            (p.get("output", 999) for p in pricing.values() if isinstance(p, dict)),
            default=999,
        )
        in_ = min(
            (p.get("input", 999) for p in pricing.values() if isinstance(p, dict)),
            default=999,
        )
        catalog_by_slug[slug] = {
            "openrouter_id": m.get("openrouter_id"),
            "tier": m.get("tier"),
            "in_price": in_,
            "out_price": out,
            "reasoning_effort": m.get("reasoning_effort"),
        }

    def price_out(m: dict[str, Any]) -> float | None:
        op = m.get("openrouter_pricing")
        if isinstance(op, dict) and "output" in op:
            return op["output"]
        prices = []
        for k in ("zen_pricing", "openrouter_pricing", "deepinfra_pricing", "alibaba_pricing"):
            p = m.get(k)
            if isinstance(p, dict) and "output" in p:
                prices.append(p["output"])
        return min(prices) if prices else None

    def price_in(m: dict[str, Any]) -> float | None:
        op = m.get("openrouter_pricing")
        if isinstance(op, dict) and "input" in op:
            return op["input"]
        prices = []
        for k in ("zen_pricing", "openrouter_pricing", "deepinfra_pricing", "alibaba_pricing"):
            p = m.get(k)
            if isinstance(p, dict) and "input" in p:
                prices.append(p["input"])
        return min(prices) if prices else None

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
    for slug, m in models.items():
        tier = m.get("tier")
        if tier == "complex":
            continue
        c = catalog_by_slug.get(slug)
        if not c or not c.get("openrouter_id"):
            continue

        bench = m.get("benchmarks", {})
        swe = score(bench, "swe_bench_pro")
        tb = score(bench, "terminal_bench_2_1")
        text = f"{m.get('specialty', '')} {m.get('strategy_note', '')}".lower()
        is_code = any(kw in text for kw in code_keywords)

        if (swe is not None and swe >= 50) or (tb is not None and tb >= 60) or is_code:
            in_price = price_in(m) if price_in(m) is not None else c["in_price"]
            out_price = price_out(m) if price_out(m) is not None else c["out_price"]
            selected.append(
                {
                    "slug": slug,
                    "name": m.get("name"),
                    "openrouter_id": c["openrouter_id"],
                    "tier": tier,
                    "in_price": in_price,
                    "out_price": out_price,
                    "swe_bench_pro": swe,
                    "terminal_bench_2_1": tb,
                    "context_window": m.get("context_window"),
                    "reasoning_effort": c.get("reasoning_effort"),
                }
            )

    selected.sort(key=lambda x: (x["out_price"] if x["out_price"] is not None else 999))
    return selected


def write_config(models: list[dict[str, Any]], output_path: Path) -> None:
    """Write the model list config to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": "Edit this list to add or remove models from the weekly speed benchmark.",
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
        in_price = m.get("in_price") or 0.0
        out_price = m.get("out_price") or 0.0
        total += rounds * (prompt_tokens * in_price + output_tokens * out_price) / 1e6
    return total


def load_existing_rows(csv_path: Path) -> list[dict[str, Any]]:
    """Load any rows already written today so the run can resume."""
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def row_key(row: dict[str, Any]) -> tuple[str, str]:
    return (row.get("hour_utc", ""), row.get("slug", ""))


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


def run_round(
    client: OpenRouterClient,
    models: Sequence[dict[str, Any]],
    prompt: str,
    max_tokens: int,
    sleep_s: float,
    hour_pst: int,
    hour_utc: int,
    run_date: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Benchmark every model once for a single hour."""
    rows: list[dict[str, Any]] = []
    for m in models:
        model_id = m["openrouter_id"]
        if dry_run:
            print(f"  [dry-run] {m['slug']} ({model_id})")
            continue
        request = ChatRequest(
            model_id=model_id,
            messages=[Message(role="user", content=prompt)],
            max_tokens=max_tokens,
            temperature=0.0,
            reasoning_effort=m.get("reasoning_effort"),
        )
        try:
            response = client.chat(request)
            elapsed = max(response.elapsed_ms, 1)
            tokens_per_sec = response.completion_tokens * 1000 / elapsed
            in_price = m.get("in_price") or 0.0
            out_price = m.get("out_price") or 0.0
            cost = (response.prompt_tokens * in_price + response.completion_tokens * out_price) / 1e6
            rows.append(
                {
                    "run_date": run_date,
                    "hour_pst": f"{hour_pst:02d}",
                    "hour_utc": f"{hour_utc:02d}",
                    "slug": m["slug"],
                    "model_id": response.model_id,
                    "model_name": m["name"],
                    "tier": m["tier"],
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
                    "slug": m["slug"],
                    "model_id": model_id,
                    "model_name": m["name"],
                    "tier": m["tier"],
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
        default=500,
        help="Maximum completion tokens per call (default: 500).",
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
        help="Resume an existing daily CSV, skipping completed (hour, model) pairs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan and estimated cost without calling any APIs.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openrouter",
        choices=["openrouter"],
        help="Provider to use (default: openrouter).",
    )
    args = parser.parse_args(argv)

    if args.generate_config:
        models = build_default_config(args.models)
        write_config(models, args.models)
        print(f"Wrote {len(models)} models to {args.models}")
        for out_tok, label in ((250, "consistency"), (500, "default"), (750, "accuracy")):
            for mult, mult_label in ((1, "1x"), (3, "3x")):
                cost = estimate_cost(models, 140, out_tok, 24 * mult)
                print(f"  {mult_label}/hour, ~{out_tok} output tokens ({label}): ${cost:.2f}/week")
        return 0

    if not args.models.exists():
        print(f"Model list not found: {args.models}")
        print("Run with --generate-config to create the default list.")
        return 1

    models = load_models(args.models)
    if not models:
        print(f"No models in {args.models}")
        return 1

    print(f"Loaded {len(models)} models for weekly speed benchmark")
    if args.dry_run:
        print(f"Prompt tokens (estimated): 140")
        print(f"Max output tokens: {args.max_tokens}")
        print(f"Rounds: {args.rounds}")
        print("Models:")
        for m in models:
            print(f"  {m['slug']} -> {m['openrouter_id']} (out ${m.get('out_price', 0)}/M)")
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
    client: OpenRouterClient = OpenRouterClient(settings)

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

            if args.no_wait:
                pass
            else:
                now = datetime.now(UTC)
                if target > now:
                    wait = (target - now).total_seconds()
                    print(f"Round {round_idx + 1}/{args.rounds}: waiting {wait:.0f}s until {target.isoformat()} UTC")
                    time.sleep(max(0, wait))

            print(f"Round {round_idx + 1}/{args.rounds} UTC hour {hour_utc:02d} / PST hour {hour_pst:02d}")

            # Filter models already completed for this hour.
            to_run = [m for m in models if (f"{hour_utc:02d}", m["slug"]) not in completed]
            if not to_run:
                print("  All models already recorded for this hour; skipping.")
                continue

            rows = run_round(
                client,
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
                completed.add((r["hour_utc"], r["slug"]))
            atomic_csv_write(all_rows, csv_path)
            print(f"  Wrote {len(rows)} rows to {csv_path}")

        print(f"Done. {len(all_rows)} total rows in {csv_path}")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
