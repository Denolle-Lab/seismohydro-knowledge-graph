#!/usr/bin/env python3
"""Pull the candidate pool for the 100-paper starter set in docs/starter-set-100.csv.

Top-cited works, all-time and since 2016, for each coupling mechanism and core topic, plus
top-cited works for each application set. Output goes to gitignored data/reports/. Abstracts are
not requested.
Selection from this pool is a manual title screen: see docs/starter-set-100.md.
"""

from __future__ import annotations

import argparse
import json

from seismohydro_kg.config import ONTOLOGY_DIR, data_dir, load_scope, load_yaml
from seismohydro_kg.openalex.budget import BudgetExceeded
from seismohydro_kg.openalex.client import build_client
from seismohydro_kg.scope import build_filter

SELECT = "id,doi,title,publication_year,cited_by_count,primary_location,primary_topic"
RECENT_FROM = "2016-01-01"
PER_QUERY = {"mechanism": 15, "topic": 6, "application": 10}
APPLICATION_SETS = [
    "resource_management_x_keywords",
    "disaster_management_x_keywords",
    "landslides_x_keywords",
    "subsurface_operations_x_keywords",
]
SKIP_TOPICS = {"T10572", "T13885"}  # Mostly not seismology, per config/scope.yaml comments.


def queries(scope: dict) -> list[tuple[str, str, str, int]]:
    """(stratum, label, filter, per_page), cheapest calls first so a cap stops the costly ones."""
    types = "type:" + "|".join(scope["work_types"])
    found = []
    for stratum, group in (("seismology", "seismology_core"), ("hydrology", "hydrology_core")):
        for topic in scope["topic_groups"][group]:
            if topic in SKIP_TOPICS:
                continue
            base = f"primary_topic.id:{topic},{types},has_doi:true"
            found.append((stratum, topic, base, PER_QUERY["topic"]))
            found.append(
                (stratum, topic, f"{base},from_publication_date:{RECENT_FROM}", PER_QUERY["topic"])
            )
    for name in APPLICATION_SETS:
        found.append(
            (
                "application",
                name,
                f"{build_filter(name, scope)},has_doi:true",
                PER_QUERY["application"],
            )
        )
    for mechanism in load_yaml(ONTOLOGY_DIR / "coupling" / "mechanisms.yaml")["mechanisms"]:
        base = f"title_and_abstract.search:{mechanism['probe_query']},{types},has_doi:true"
        found.append(("seismohydrology", mechanism["id"], base, PER_QUERY["mechanism"]))
        found.append(
            (
                "seismohydrology",
                mechanism["id"],
                f"{base},from_publication_date:{RECENT_FROM}",
                PER_QUERY["mechanism"],
            )
        )
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-usd", type=float, required=True)
    args = parser.parse_args()

    client = build_client(args.max_usd)
    seen: dict[str, dict] = {}
    stopped = None
    for stratum, label, filter_, per_page in queries(load_scope()):
        try:
            payload = client.get(
                "/works",
                {
                    "filter": filter_,
                    "select": SELECT,
                    "sort": "cited_by_count:desc",
                    "per_page": per_page,
                },
            )
        except BudgetExceeded as exc:
            stopped = str(exc)
            break
        for work in payload["results"]:
            record = seen.setdefault(
                work["id"],
                {
                    "openalex_id": work["id"].rsplit("/", 1)[-1],
                    "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
                    "title": work.get("title"),
                    "year": work.get("publication_year"),
                    "cited_by": work.get("cited_by_count"),
                    "venue": ((work.get("primary_location") or {}).get("source") or {}).get(
                        "display_name"
                    ),
                    "topic": (work.get("primary_topic") or {}).get("display_name"),
                    "found_by": [],
                },
            )
            if (stratum, label) not in [tuple(item) for item in record["found_by"]]:
                record["found_by"].append([stratum, label])

    out = data_dir() / "reports" / "starter_candidates.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        for index, record in enumerate(seen.values()):
            handle.write(json.dumps({"index": index, **record}, ensure_ascii=False) + "\n")
    print(f"{len(seen)} candidates in {out}. Spent ${client.guard.spent_run_usd:.4f}.")
    if stopped:
        print(f"Stopped at cap: {stopped}")


if __name__ == "__main__":
    main()
