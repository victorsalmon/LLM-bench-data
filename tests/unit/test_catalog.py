from decimal import Decimal
from pathlib import Path

import pytest

from llm_cost_comparison.core.catalog import load_catalog
from llm_cost_comparison.core.exceptions import CatalogError


def test_load_catalog_from_repo_root(tmp_path: Path) -> None:
    """Loading from the actual catalogs directory succeeds for all known types."""
    catalog_dir = Path("catalogs")
    catalog = load_catalog(catalog_dir)

    assert len(catalog.models) > 0
    assert len(catalog.tasks) == 16
    assert len(catalog.samples) == 3
    assert len(catalog.methods) == 5
    assert len(catalog.experiments) == 5
    assert len(catalog.tiers) == 5


def test_model_lookup() -> None:
    """Catalog resolves model slugs and OpenRouter provider ids."""
    catalog = load_catalog("catalogs")

    flash = catalog.get_model("deepseek-v4-flash")
    assert flash.name == "DeepSeek V4 Flash"
    assert flash.openrouter_id == "deepseek/deepseek-v4-flash"
    assert flash.max_variants[0].slug == "deepseek-v4-flash-max"

    # Resolve from provider id.
    by_id = catalog.get_model_by_openrouter_id("anthropic/claude-fable-5")
    assert by_id.slug == "claude-fable-5"

    ga_flash = catalog.get_model("deepseek-v4-flash-max")
    assert ga_flash.deepinfra_id == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert ga_flash.pricing["deepinfra"].output == Decimal("0.18")


def test_task_and_method_lookup() -> None:
    """Catalog resolves tasks and compression methods."""
    catalog = load_catalog("catalogs")

    assert catalog.get_task("reasoning").category == "reasoning"
    assert catalog.get_method("diff-only").id == "diff-only"


def test_resolve_refs() -> None:
    """The 'all' reference expands to the full collection."""
    catalog = load_catalog("catalogs")

    tokenizer = catalog.get_experiment("tokenizer-efficiency")
    assert len(catalog.resolve_sample_refs(tokenizer.sample_refs)) == 3
    assert len(catalog.resolve_model_refs(tokenizer.model_refs)) == len(catalog.models)


def test_missing_model_raises() -> None:
    """Missing lookups raise a clear domain error."""
    catalog = load_catalog("catalogs")

    with pytest.raises(CatalogError):
        catalog.get_model("not-a-model")
