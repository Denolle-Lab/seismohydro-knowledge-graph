"""The text every extractor reads, and the raw records it comes from.

Offsets on L2 edges index into `work_text`: the title, a blank line, then the reconstructed
abstract. A work without an abstract is its title alone. The result stays local (ADR 0005).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from seismohydro_kg.graph.build import read_raw, short_id
from seismohydro_kg.openalex.abstracts import reconstruct_abstract


def work_text(record: dict[str, Any]) -> str | None:
    title = (record.get("title") or "").strip()
    abstract = reconstruct_abstract(record.get("abstract_inverted_index"))
    return "\n\n".join(part for part in (title, abstract) if part) or None


def raw_parts(root: Path) -> list[Path]:
    """Raw part files for every set under a raw root."""
    return sorted(root.glob("*/part-*.jsonl.gz"))


def iter_works(paths: Iterable[Path]) -> Iterator[tuple[str, dict[str, Any]]]:
    """(work_id, record), once per work even when a work appears in several sets."""
    seen: set[str] = set()
    for path in paths:
        for record in read_raw(path):
            work_id = short_id(record["id"])
            if work_id not in seen:
                seen.add(work_id)
                yield work_id, record
