"""A plain summary of a built graph: what it holds, and how connected it is.

Prints titles and concept labels only. Nothing here reads abstract text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


def _largest_component(pairs: list[tuple[str, str]], nodes: list[str]) -> int:
    parent = {node: node for node in nodes}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in pairs:
        parent[find(left)] = find(right)
    sizes: dict[str, int] = {}
    for node in nodes:
        root = find(node)
        sizes[root] = sizes.get(root, 0) + 1
    return max(sizes.values(), default=0)


def graph_report(graph_dir: Path, top: int = 15) -> dict[str, Any]:
    nodes, edges = graph_dir / "nodes.parquet", graph_dir / "edges.parquet"
    con = duckdb.connect()
    con.execute(
        f"""
        CREATE TEMP VIEW works AS SELECT node_id, label,
            json_extract(attrs, '$.has_abstract')::BOOLEAN AS has_abstract
        FROM '{nodes}' WHERE node_type = 'Work'
            AND json_extract(attrs, '$.in_corpus')::BOOLEAN;
        CREATE TEMP VIEW concepts AS SELECT node_id, node_type, label, domain
        FROM '{nodes}' WHERE layer = 'L1';
        CREATE TEMP VIEW mentions AS SELECT DISTINCT e.source AS work, e.target AS concept
        FROM '{edges}' e WHERE e.edge_type = 'mentions' AND e.layer = 'L2';
        """
    )

    def scalar(sql: str) -> int:
        return con.execute(sql).fetchone()[0] or 0

    work_ids = [row[0] for row in con.execute("SELECT node_id FROM works").fetchall()]
    citations = con.execute(
        f"""SELECT source, target FROM '{edges}' WHERE edge_type = 'cites'
            AND source IN (SELECT node_id FROM works) AND target IN (SELECT node_id FROM works)"""
    ).fetchall()
    mention_pairs = con.execute("SELECT work, concept FROM mentions").fetchall()
    matched = sorted({concept for _work, concept in mention_pairs})
    linked = _largest_component(citations + mention_pairs, work_ids + matched)
    report: dict[str, Any] = {
        "works": len(work_ids),
        "works_with_abstract": scalar("SELECT count(*) FROM works WHERE has_abstract"),
        "works_with_2plus_concepts": scalar(
            """SELECT count(*) FROM
               (SELECT work FROM mentions GROUP BY work HAVING count(*) >= 2)"""
        ),
        "citations_within_set": len(citations),
        "citations_leaving_set": scalar(
            f"""SELECT count(*) FROM '{edges}' WHERE edge_type = 'cites'
                AND target NOT IN (SELECT node_id FROM works)"""
        ),
        "concepts_in_vocabulary": scalar("SELECT count(*) FROM concepts"),
        "concepts_matched": len(matched),
        "work_concept_edges": len(mention_pairs),
        "largest_connected_share": round(linked / max(len(work_ids) + len(matched), 1), 3),
    }
    report["by_extractor"] = con.execute(
        f"""SELECT tier, edge_type, count(*) FROM '{edges}' WHERE layer = 'L2'
            GROUP BY 1, 2 ORDER BY 3 DESC"""
    ).fetchall()
    report["matched_by_type"] = con.execute(
        """SELECT c.node_type, count(DISTINCT m.concept), count(DISTINCT c.node_id)
           FROM concepts c LEFT JOIN mentions m ON m.concept = c.node_id
           GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    report["top_concepts"] = con.execute(
        f"""SELECT c.label, c.domain, count(*) AS works FROM mentions m
            JOIN concepts c ON c.node_id = m.concept
            GROUP BY 1, 2 ORDER BY works DESC, c.label LIMIT {top}"""
    ).fetchall()
    # Seismology and hydrology concepts named in the same work. This is co-occurrence, not a claim.
    pair_sql = """
        FROM mentions a JOIN mentions b ON a.work = b.work
        JOIN concepts ca ON ca.node_id = a.concept AND ca.domain = 'seismology'
        JOIN concepts cb ON cb.node_id = b.concept AND cb.domain = 'hydrology'"""
    report["works_joining_both_vocabularies"] = scalar(f"SELECT count(DISTINCT a.work) {pair_sql}")
    report["top_cross_domain_pairs"] = con.execute(
        f"""SELECT ca.label, cb.label, count(DISTINCT a.work) AS works {pair_sql}
            GROUP BY 1, 2 ORDER BY works DESC, 1, 2 LIMIT {top}"""
    ).fetchall()
    report["concepts_never_matched"] = [
        row[0]
        for row in con.execute(
            """SELECT c.node_id FROM concepts c WHERE c.node_id NOT IN
               (SELECT concept FROM mentions) ORDER BY 1"""
        ).fetchall()
    ]
    con.close()
    return report


def format_report(report: dict[str, Any]) -> str:
    lines = [f"{key}: {report[key]}" for key in report if isinstance(report[key], int | float)]
    lines.append("\nL2 edges (tier, type, count):")
    lines += [f"  {tier:10} {kind:18} {count}" for tier, kind, count in report["by_extractor"]]
    lines.append("\nConcepts matched by type (matched / in vocabulary):")
    lines += [f"  {name:18} {hit} / {total}" for name, hit, total in report["matched_by_type"]]
    lines.append("\nMost-mentioned concepts (works):")
    lines += [f"  {count:3}  {label} [{domain}]" for label, domain, count in report["top_concepts"]]
    lines.append("\nSeismology and hydrology concepts in the same work (works):")
    lines += [f"  {count:3}  {a} + {b}" for a, b, count in report["top_cross_domain_pairs"]]
    never = report["concepts_never_matched"]
    lines.append(f"\nConcepts never matched: {len(never)}")
    return "\n".join(lines)
