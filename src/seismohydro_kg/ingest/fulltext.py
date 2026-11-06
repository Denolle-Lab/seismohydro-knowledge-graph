"""Download full text from OpenAlex's cached copies, within a spending cap.

Output: <out_root>/<set>/<format>/<work_id>.<format>, plus _selection.json. Resuming skips files
already on disk, so nothing is paid for twice. The selection is the most-cited works in the set
that OpenAlex holds in this format, which favors older and review papers.

A charged file that fails the format check is kept as <work_id>.<format>.rejected, so a resume
skips it instead of paying again, and it can be inspected. Delete those files to retry them. If
the first REJECT_STOP downloads are all rejected, the run stops: the check, not the files, is the
likely problem.

Full text stays in gitignored data/ and must never be committed, published or uploaded as a
workflow artifact (ADR 0005).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from seismohydro_kg.openalex.budget import BudgetExceeded
from seismohydro_kg.openalex.client import OpenAlexClient

# GROBID writes a TEI document: an optional XML declaration and comments, then a <TEI> root,
# possibly prefixed. An HTML error page or any other XML fails.
_TEI_ROOT = re.compile(rb"\A\s*(<\?xml[^>]*\?>\s*)?(<!--.*?-->\s*)*<([\w.-]+:)?TEI[\s>/]", re.S)


def _is_tei(body: bytes) -> bool:
    return bool(_TEI_ROOT.match(body[:4096]))


def _is_pdf(body: bytes) -> bool:
    return body.lstrip().startswith(b"%PDF")


# format: (content API extension, has_content field, file suffix, validity check)
FORMATS: dict[str, tuple[str, str, str, Callable[[bytes], bool]]] = {
    "xml": ("grobid-xml", "grobid_xml", ".xml", _is_tei),
    "pdf": ("pdf", "pdf", ".pdf", _is_pdf),
}
SORT = "cited_by_count:desc"
REJECTED = ".rejected"
REJECT_STOP = 5


@dataclass
class FulltextResult:
    selected: int
    downloaded: int
    already_present: int
    unavailable: int
    invalid: int
    stopped_at_cap: str | None
    previously_rejected: int = 0
    stopped_reason: str | None = None


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
    extension, _field, suffix, is_valid = FORMATS[format_]
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

    downloaded = present = unavailable = invalid = previously_rejected = 0
    stopped: str | None = None
    reason: str | None = None
    for work_id in work_ids:
        path = out_dir / f"{work_id}{suffix}"
        rejected = path.with_suffix(path.suffix + REJECTED)
        if path.exists():
            present += 1
            continue
        if rejected.exists():
            previously_rejected += 1
            continue
        try:
            body = client.download(work_id, extension)
        except BudgetExceeded as exc:
            stopped = str(exc)
            break
        if body is None:
            unavailable += 1
            continue
        target = path if is_valid(body) else rejected
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_bytes(body)
        os.replace(temp, target)
        if target is path:
            downloaded += 1
        else:
            invalid += 1
            if invalid >= REJECT_STOP and downloaded == 0 and present == 0:
                reason = (
                    f"the first {invalid} files all failed the {format_} format check. "
                    f"Inspect a *{suffix}{REJECTED} file in {out_dir} before running again"
                )
                break
    return FulltextResult(
        len(work_ids),
        downloaded,
        present,
        unavailable,
        invalid,
        stopped,
        previously_rejected,
        reason,
    )
