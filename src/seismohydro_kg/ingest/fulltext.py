"""Download full text from OpenAlex's cached copies, within a spending cap.

Output: <out_root>/<set>/<format>/<work_id>.<format>, plus _selection.json. Resuming skips files
already on disk, so nothing is paid for twice. The selection is the most-cited works in the set
that OpenAlex holds in this format, which favors older and review papers.

Full text stays in gitignored data/ and must never be committed, published or uploaded as a
workflow artifact (ADR 0005).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from seismohydro_kg.openalex.budget import BudgetExceeded
from seismohydro_kg.openalex.client import OpenAlexClient

# format: (content API extension, has_content field, file suffix, leading bytes of a valid file)
FORMATS = {
    "xml": ("grobid-xml", "grobid_xml", ".xml", b"<"),
    "pdf": ("pdf", "pdf", ".pdf", b"%PDF"),
}
SORT = "cited_by_count:desc"


@dataclass
class FulltextResult:
    selected: int
    downloaded: int
    already_present: int
    unavailable: int
    invalid: int
    stopped_at_cap: str | None


def select_works(client: OpenAlexClient, filter_: str, format_: str, limit: int) -> list[str]:
    """IDs of the most-cited works in the filter that OpenAlex holds in this format."""
    field = FORMATS[format_][1]
    found: list[str] = []
    for results, _cursor in client.iter_pages(
        f"{filter_},has_content.{field}:true", ["id"], sort=SORT
    ):
        found.extend(work["id"].rsplit("/", 1)[-1] for work in results)
        if len(found) >= limit:
            break
    return found[:limit]


def _load_selection(path: Path, filter_hash: str, limit: int) -> list[str] | None:
    if not path.exists():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved["filter_hash"] != filter_hash:
        raise ValueError(
            f"{path.parent} was selected with a different filter. "
            "Use a new --out, or remove that directory to start over."
        )
    return saved["work_ids"][:limit] if len(saved["work_ids"]) >= limit else None


def download_fulltext(
    client: OpenAlexClient, set_name: str, filter_: str, format_: str, limit: int, out_root: Path
) -> FulltextResult:
    extension, _field, suffix, magic = FORMATS[format_]
    out_dir = out_root / set_name / format_
    out_dir.mkdir(parents=True, exist_ok=True)
    selection_path = out_dir / "_selection.json"
    filter_hash = hashlib.sha256(filter_.encode()).hexdigest()[:16]

    work_ids = _load_selection(selection_path, filter_hash, limit)
    try:
        if work_ids is None:
            work_ids = select_works(client, filter_, format_, limit)
            payload = {"filter_hash": filter_hash, "sort": SORT, "work_ids": work_ids}
            selection_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except BudgetExceeded as exc:
        return FulltextResult(0, 0, 0, 0, 0, str(exc))

    downloaded = present = unavailable = invalid = 0
    stopped: str | None = None
    for work_id in work_ids:
        path = out_dir / f"{work_id}{suffix}"
        if path.exists():
            present += 1
            continue
        try:
            body = client.download(work_id, extension)
        except BudgetExceeded as exc:
            stopped = str(exc)
            break
        if body is None:
            unavailable += 1
        elif not body.lstrip().startswith(magic):
            invalid += 1
        else:
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_bytes(body)
            os.replace(temp, path)
            downloaded += 1
    return FulltextResult(len(work_ids), downloaded, present, unavailable, invalid, stopped)
