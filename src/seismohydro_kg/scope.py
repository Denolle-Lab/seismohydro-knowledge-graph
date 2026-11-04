"""Turn config/scope.yaml into OpenAlex filters, and count what they would return."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seismohydro_kg.openalex.budget import BudgetExceeded
from seismohydro_kg.openalex.client import PER_PAGE_MAX, OpenAlexClient, cost_class


def build_filter(name: str, scope: dict[str, Any], from_publication_date: str | None = None) -> str:
    definition = scope["sets"][name]
    parts: list[str] = []
    if definition.get("topics"):
        ids = scope["topic_groups"][definition["topics"]]
        parts.append("primary_topic.id:" + "|".join(ids))
    for topic in scope["topic_groups"].get(definition.get("exclude_topics", ""), []):
        parts.append(f"primary_topic.id:!{topic}")
    if definition.get("search"):
        parts.append(
            "title_and_abstract.search:" + definition["search"].format(**scope["keywords"])
        )
    parts.append("type:" + "|".join(scope["work_types"]))
    if from_publication_date:
        parts.append(f"from_publication_date:{from_publication_date}")
    return ",".join(parts)


def ingest_sets(scope: dict[str, Any]) -> list[str]:
    return [name for name, spec in scope["sets"].items() if spec["role"] in ("core", "bridge")]


@dataclass
class SetReport:
    name: str
    role: str
    count: int
    with_abstract: int
    abstract_share: float
    ingest_calls: int
    ingest_usd: float
    baseline_count: int | None
    baseline_delta: float | None


def scope_report(client: OpenAlexClient, scope: dict[str, Any]) -> dict[str, Any]:
    """Count every set. Stops cleanly at the budget cap and returns what it has so far."""
    rows: list[SetReport] = []
    stopped: str | None = None
    for name, spec in scope["sets"].items():
        filter_ = build_filter(name, scope)
        try:
            groups = client.group_counts(filter_, "has_abstract")
        except BudgetExceeded as exc:
            stopped = str(exc)
            break
        count = sum(groups.values())
        with_abstract = groups.get("true", 0)
        calls = math.ceil(count / PER_PAGE_MAX)
        baseline = spec.get("baseline", {}).get("count")
        rows.append(
            SetReport(
                name=name,
                role=spec["role"],
                count=count,
                with_abstract=with_abstract,
                abstract_share=round(with_abstract / count, 3) if count else 0.0,
                ingest_calls=calls,
                ingest_usd=round(calls * client.rates[cost_class({"filter": filter_})], 4),
                baseline_count=baseline,
                baseline_delta=round(count / baseline - 1, 4) if baseline else None,
            )
        )
    ingest_rows = [row for row in rows if row.role in ("core", "bridge")]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "sets": [asdict(row) for row in rows],
        "ingest_usd_upper_bound": round(sum(row.ingest_usd for row in ingest_rows), 4),
        "usd_spent": round(client.guard.spent_run_usd, 6),
        "stopped_at_cap": stopped,
    }


def write_report(report: dict[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"scope-report-{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path
