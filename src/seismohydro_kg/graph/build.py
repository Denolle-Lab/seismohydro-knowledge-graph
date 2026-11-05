"""Build node and edge tables from raw works, the vocabularies and literature assertions.

Each raw work contributes L0 nodes and edges. Abstract indexes are dropped here: only a yes/no
`has_abstract` flag reaches the tables. Cited works outside the corpus become stub nodes.
"""

from __future__ import annotations

import gzip
import json
import shutil
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from seismohydro_kg.config import ONTOLOGY_DIR, load_yaml
from seismohydro_kg.graph.schema import EDGE_SCHEMA, MEMBERSHIP_SCHEMA, NODE_SCHEMA

_BATCH_ROWS = 100_000


def short_id(url: str | None) -> str | None:
    return url.rsplit("/", 1)[-1] if url else None


class _Sink:
    """Write rows to numbered Parquet files, so large builds stay out of memory."""

    def __init__(self, directory: Path, schema: pa.Schema) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.directory, self.schema = directory, schema
        self.rows: list[dict[str, Any]] = []
        self.part = 0

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)
        if len(self.rows) >= _BATCH_ROWS:
            self.flush()

    def flush(self) -> None:
        if not self.rows:
            return
        table = pa.Table.from_pylist(self.rows, schema=self.schema)
        pq.write_table(table, self.directory / f"part-{self.part:05d}.parquet")
        self.part += 1
        self.rows = []


def _node(node_id: str, node_type: str, layer: str, label: str | None, **attrs: Any) -> dict:
    domain = attrs.pop("domain", None)
    return {
        "node_id": node_id,
        "node_type": node_type,
        "layer": layer,
        "label": label,
        "domain": domain,
        "attrs": json.dumps(attrs, ensure_ascii=False) if attrs else None,
    }


def _l0_edge(source: str, target: str, edge_type: str, work: str, confidence: float = 1.0) -> dict:
    return {
        "source": source,
        "target": target,
        "edge_type": edge_type,
        "layer": "L0",
        "work_id": work,
        "char_start": None,
        "char_end": None,
        "extractor_version": "openalex",
        "confidence": confidence,
        "tier": "openalex",
    }


def work_rows(record: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """L0 nodes and edges for one OpenAlex work."""
    work = short_id(record["id"])
    nodes = [
        _node(
            work,
            "Work",
            "L0",
            record.get("title"),
            year=record.get("publication_year"),
            doi=record.get("doi"),
            cited_by_count=record.get("cited_by_count"),
            has_abstract=bool(record.get("abstract_inverted_index")),
            in_corpus=True,
        )
    ]
    edges = [
        _l0_edge(work, short_id(ref), "cites", work) for ref in record.get("referenced_works") or []
    ]

    source = (record.get("primary_location") or {}).get("source") or {}
    if source.get("id"):
        source_id = short_id(source["id"])
        nodes.append(_node(source_id, "Source", "L0", source.get("display_name")))
        edges.append(_l0_edge(work, source_id, "published_in", work))

    for topic in record.get("topics") or []:
        topic_id = short_id(topic["id"])
        nodes.append(_node(topic_id, "Topic", "L0", topic.get("display_name")))
        edges.append(_l0_edge(work, topic_id, "has_topic", work, float(topic.get("score") or 0.0)))

    for authorship in record.get("authorships") or []:
        author = authorship.get("author") or {}
        if not author.get("id"):
            continue
        author_id = short_id(author["id"])
        nodes.append(_node(author_id, "Author", "L0", author.get("display_name")))
        edges.append(_l0_edge(author_id, work, "authored", work))
        for institution in authorship.get("institutions") or []:
            if not institution.get("id"):
                continue
            inst_id = short_id(institution["id"])
            nodes.append(_node(inst_id, "Institution", "L0", institution.get("display_name")))
            edges.append(_l0_edge(author_id, inst_id, "affiliated_with", work))
    return nodes, edges


def ontology_nodes() -> Iterator[dict]:
    """L1 concepts and L3 mechanisms. Per-domain instances stay separate through `domain`."""
    for path in sorted((ONTOLOGY_DIR / "vocab").glob("*.yaml")):
        vocabulary = load_yaml(path)
        for concept in vocabulary["concepts"]:
            yield _node(
                concept["id"],
                concept["concept_type"],
                "L1",
                concept["label"],
                domain=vocabulary["domain"],
                synonyms=concept.get("synonyms", []),
            )
    for mechanism in load_yaml(ONTOLOGY_DIR / "coupling" / "mechanisms.yaml")["mechanisms"]:
        yield _node(
            mechanism["id"],
            "CouplingMechanism",
            "L3",
            mechanism["label"],
            domain="coupling",
            direction=mechanism["direction"],
            status=mechanism["status"],
        )


def ontology_edges() -> Iterator[dict]:
    """Curated L1 links. These come from review rather than from one work, so work_id is empty."""
    for path in sorted((ONTOLOGY_DIR / "vocab").glob("*.yaml")):
        for concept in load_yaml(path)["concepts"]:
            targets = [
                *(("broader", target) for target in concept.get("broader", [])),
                *(("proxy_for", target) for target in concept.get("proxy_for", [])),
            ]
            if concept.get("typical_approach"):
                targets.append(("typical_approach", concept["typical_approach"]))
            for edge_type, target in targets:
                yield {
                    "source": concept["id"],
                    "target": target,
                    "edge_type": edge_type,
                    "layer": "L1",
                    "work_id": None,
                    "char_start": None,
                    "char_end": None,
                    "extractor_version": "curated",
                    "confidence": 1.0,
                    "tier": "human",
                }


def read_raw(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def build_graph(
    raw_by_set: dict[str, Iterable[Path]], assertion_paths: Iterable[Path], out_dir: Path
) -> dict[str, int]:
    """Write nodes.parquet, edges.parquet and work_sets.parquet into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    staging = out_dir / "_staging"
    if staging.exists():
        shutil.rmtree(staging)
    nodes = _Sink(staging / "nodes", NODE_SCHEMA)
    edges = _Sink(staging / "edges", EDGE_SCHEMA)
    members = _Sink(staging / "members", MEMBERSHIP_SCHEMA)

    for set_name, paths in raw_by_set.items():
        for path in paths:
            for record in read_raw(path):
                work_nodes, work_edges = work_rows(record)
                for row in work_nodes:
                    nodes.add(row)
                for row in work_edges:
                    edges.add(row)
                members.add({"work_id": short_id(record["id"]), "set_name": set_name})

    for row in ontology_nodes():
        nodes.add(row)
    for row in ontology_edges():
        edges.add(row)
    for path in assertion_paths:
        for assertion in read_raw(path):
            edges.add({name: assertion.get(name) for name in EDGE_SCHEMA.names})
    nodes.flush()
    edges.flush()
    members.flush()
    pq.write_table(
        pa.Table.from_pylist([], schema=NODE_SCHEMA), staging / "nodes" / "empty.parquet"
    )
    pq.write_table(
        pa.Table.from_pylist([], schema=EDGE_SCHEMA), staging / "edges" / "empty.parquet"
    )
    pq.write_table(
        pa.Table.from_pylist([], schema=MEMBERSHIP_SCHEMA), staging / "members" / "empty.parquet"
    )

    con = duckdb.connect()
    # Per-node dedup keeps the in-corpus row, since a Work can repeat across scope sets.
    con.execute(
        f"""
        COPY (
            WITH corpus AS (
                SELECT * FROM read_parquet('{staging}/nodes/*.parquet')
                QUALIFY row_number() OVER (PARTITION BY node_id ORDER BY label NULLS LAST) = 1
            ),
            edges AS (
                SELECT DISTINCT * FROM read_parquet('{staging}/edges/*.parquet')
            ),
            stubs AS (
                SELECT DISTINCT target AS node_id, 'Work' AS node_type, 'L0' AS layer,
                       NULL AS label, NULL AS domain, '{{"in_corpus": false}}' AS attrs
                FROM edges
                WHERE edge_type = 'cites' AND target NOT IN (SELECT node_id FROM corpus)
            )
            SELECT * FROM corpus UNION ALL SELECT * FROM stubs
        ) TO '{out_dir}/nodes.parquet' (FORMAT parquet)
        """
    )
    con.execute(
        f"""
        COPY (SELECT DISTINCT * FROM read_parquet('{staging}/edges/*.parquet'))
        TO '{out_dir}/edges.parquet' (FORMAT parquet)
        """
    )
    con.execute(
        f"""
        COPY (SELECT DISTINCT * FROM read_parquet('{staging}/members/*.parquet'))
        TO '{out_dir}/work_sets.parquet' (FORMAT parquet)
        """
    )
    counts = {
        "nodes": con.execute(f"SELECT count(*) FROM '{out_dir}/nodes.parquet'").fetchone()[0],
        "edges": con.execute(f"SELECT count(*) FROM '{out_dir}/edges.parquet'").fetchone()[0],
        "works_in_corpus": con.execute(
            f"SELECT count(DISTINCT work_id) FROM '{out_dir}/work_sets.parquet'"
        ).fetchone()[0],
    }
    con.close()
    shutil.rmtree(staging)
    return counts
