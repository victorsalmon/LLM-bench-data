"""YAML catalog loader."""

from pathlib import Path

import yaml

from llm_bench_data.core.exceptions import CatalogError
from llm_bench_data.core.models import Catalog


def load_catalog(catalog_dir: Path | str, root_path: Path | str | None = None) -> Catalog:
    """Load all YAML catalogs from *catalog_dir* and return a validated Catalog.

    Args:
        catalog_dir: Directory containing YAML catalog files.
        root_path: Optional repository root used to resolve relative sample paths.
    """
    catalog_dir = Path(catalog_dir)
    if not catalog_dir.is_dir():
        raise CatalogError(f"Catalog directory not found: {catalog_dir}")

    data: dict[str, object] = {}
    for yaml_file in sorted(catalog_dir.glob("*.yaml")):
        with yaml_file.open("r", encoding="utf-8") as fh:
            file_data = yaml.safe_load(fh) or {}
            if not isinstance(file_data, dict):
                raise CatalogError(f"Catalog file {yaml_file} must contain a YAML mapping")
            for key, value in file_data.items():
                if key in data:
                    raise CatalogError(f"Duplicate catalog key '{key}' in {yaml_file}")
                data[key] = value

    if root_path is None:
        root_path = catalog_dir.parent
    data["root_path"] = Path(root_path)

    return Catalog.model_validate(data)
