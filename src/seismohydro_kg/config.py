"""Repository paths and YAML config loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
ONTOLOGY_DIR = REPO_ROOT / "ontology"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


def data_dir() -> Path:
    """Root for all generated data. Gitignored, because raw records hold abstract indexes."""
    return Path(os.environ.get("SHKG_DATA_DIR", REPO_ROOT / "data"))


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_budget() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "budget.yaml")


def load_scope() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "scope.yaml")
