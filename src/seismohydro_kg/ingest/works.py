"""Resumable download of one scope set into gzipped JSON Lines.

Output: <raw_root>/<set>/part-00000.jsonl.gz plus _checkpoint.json. A crash or a budget stop loses
at most one unflushed part. The checkpoint only moves after a part is safely on disk, so a resume
may refetch a little but never skips records. The graph build deduplicates by work ID.

Raw files hold abstract indexes. They must stay in gitignored data/ and must never be uploaded as
public artifacts.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seismohydro_kg.openalex.budget import BudgetExceeded
from seismohydro_kg.openalex.client import OpenAlexClient

SELECT_FIELDS = [
    "id",
    "doi",
    "title",
    "publication_year",
    "type",
    "language",
    "cited_by_count",
    "updated_date",
    "primary_topic",
    "topics",
    "keywords",
    "primary_location",
    "authorships",
    "referenced_works",
    "related_works",
    "abstract_inverted_index",
]
PAGES_PER_PART = 100


@dataclass
class IngestResult:
    set_name: str
    works_written: int
    done: bool
    stopped_at_cap: str | None


def _write_part(path: Path, records: list[dict[str, Any]]) -> None:
    temp = path.with_suffix(".tmp")
    with gzip.open(temp, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def ingest_set(client: OpenAlexClient, set_name: str, filter_: str, raw_root: Path) -> IngestResult:
    out_dir = raw_root / set_name
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "_checkpoint.json"
    filter_hash = hashlib.sha256(filter_.encode()).hexdigest()[:16]
    state = {"cursor": "*", "next_part": 0, "works_written": 0, "done": False}
    if checkpoint_path.exists():
        saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if saved["filter_hash"] != filter_hash:
            raise ValueError(
                f"{out_dir} was downloaded with a different filter. "
                "Use a new --raw-dir, or remove that directory to start over."
            )
        state = {key: saved[key] for key in state}
    if state["done"]:
        return IngestResult(set_name, state["works_written"], True, None)

    buffer: list[dict[str, Any]] = []
    pages_buffered = 0
    pending_cursor: str | None = state["cursor"]

    def flush() -> None:
        nonlocal buffer, pages_buffered
        if buffer:
            _write_part(out_dir / f"part-{state['next_part']:05d}.jsonl.gz", buffer)
            state["next_part"] += 1
            state["works_written"] += len(buffer)
        state["cursor"] = pending_cursor
        state["done"] = pending_cursor is None
        payload = {**state, "filter_hash": filter_hash, "filter": filter_}
        checkpoint_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        buffer, pages_buffered = [], 0

    stopped: str | None = None
    try:
        for results, next_cursor in client.iter_pages(filter_, SELECT_FIELDS, state["cursor"]):
            buffer.extend(results)
            pages_buffered += 1
            pending_cursor = next_cursor
            if pages_buffered >= PAGES_PER_PART:
                flush()
    except BudgetExceeded as exc:
        stopped = str(exc)
    finally:
        # Also runs on API errors: what was paid for is kept, with the cursor that follows it.
        flush()
    return IngestResult(set_name, state["works_written"], state["done"], stopped)
