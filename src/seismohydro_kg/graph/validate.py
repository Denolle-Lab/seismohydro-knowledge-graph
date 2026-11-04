"""Checks a graph must pass before anyone uses or publishes it.

Two rules carry the project: every L2 and L3 edge has provenance, and no public table holds
abstract text. See docs/adr/0005-abstract-handling.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import duckdb

from seismohydro_kg.graph.schema import LAYERS, TIERS

# Column names that have no place in a public table.
FORBIDDEN_COLUMNS = {
    "abstract",
    "abstract_text",
    "abstract_inverted_index",
    "evidence_text",
    "fulltext",
    "full_text",
    "sentence",
    "snippet",
}
# Word limits per cell. Labels hold titles, attrs hold short JSON. Nothing else is free text.
CELL_WORD_LIMITS = {"label": 120, "attrs": 80}
DEFAULT_CELL_WORD_LIMIT = 40
SHINGLE_WORDS = 12


def _sql_list(values: Iterable[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def validate_graph(graph_dir: Path) -> list[str]:
    """Return human-readable violations. An empty list means the graph passes."""
    nodes = graph_dir / "nodes.parquet"
    edges = graph_dir / "edges.parquet"
    missing = [path.name for path in (nodes, edges) if not path.exists()]
    if missing:
        return [f"missing table: {name}" for name in missing]

    con = duckdb.connect()
    violations: list[str] = []

    def check(message: str, sql: str) -> None:
        count = con.execute(sql).fetchone()[0]
        if count:
            violations.append(f"{message}: {count}")

    check(
        "duplicate node_id",
        f"SELECT count(*) FROM (SELECT node_id FROM '{nodes}' GROUP BY 1 HAVING count(*) > 1)",
    )
    check(
        "edge endpoint not in nodes",
        f"""SELECT count(*) FROM '{edges}' e WHERE e.source NOT IN (SELECT node_id FROM '{nodes}')
            OR e.target NOT IN (SELECT node_id FROM '{nodes}')""",
    )
    check(
        "unknown layer",
        f"SELECT count(*) FROM '{edges}' WHERE layer NOT IN ({_sql_list(LAYERS)}) OR layer IS NULL",
    )
    check(
        "unknown or missing tier",
        f"SELECT count(*) FROM '{edges}' WHERE tier NOT IN ({_sql_list(TIERS)}) OR tier IS NULL",
    )
    provenance = f"SELECT count(*) FROM '{edges}' WHERE layer IN ('L2', 'L3') AND"
    check("L2/L3 edge without work_id", f"{provenance} work_id IS NULL")
    check(
        "L2/L3 edge citing a work not in nodes",
        f"{provenance} work_id NOT IN (SELECT node_id FROM '{nodes}')",
    )
    check(
        "L2/L3 edge without valid character offsets",
        f"""{provenance} (char_start IS NULL OR char_end IS NULL
            OR char_start < 0 OR char_end <= char_start)""",
    )
    check("L2/L3 edge without extractor_version", f"{provenance} extractor_version IS NULL")
    check(
        "L2/L3 edge without confidence in [0, 1]",
        f"{provenance} (confidence IS NULL OR confidence < 0 OR confidence > 1)",
    )
    check("L2/L3 edge claiming tier openalex", f"{provenance} tier = 'openalex'")
    con.close()

    violations.extend(check_no_abstract_text(graph_dir))
    return violations


def check_no_abstract_text(table_dir: Path, abstracts: Iterable[str] | None = None) -> list[str]:
    """Scan every Parquet file for abstract text.

    Column names and cell lengths are always checked. Passing `abstracts` adds an exact check: any
    run of 12 consecutive abstract words found in a table fails, whatever the column is called.
    Work titles are skipped for that check, since an abstract can repeat its own title.
    """
    violations: list[str] = []
    shingles = _shingles(abstracts) if abstracts is not None else None
    con = duckdb.connect()
    for path in sorted(Path(table_dir).glob("*.parquet")):
        columns = con.execute(f"DESCRIBE SELECT * FROM '{path}'").fetchall()
        for column, column_type, *_ in columns:
            if column.lower() in FORBIDDEN_COLUMNS:
                violations.append(f"{path.name}: forbidden column {column!r}")
            if column_type != "VARCHAR":
                continue
            limit = CELL_WORD_LIMITS.get(column, DEFAULT_CELL_WORD_LIMIT)
            over = con.execute(
                f"""SELECT count(*) FROM '{path}'
                    WHERE len(string_split("{column}", ' ')) > {limit}"""
            ).fetchone()[0]
            if over:
                violations.append(
                    f"{path.name}: {over} cells in {column!r} longer than {limit} words"
                )
            if shingles and column != "label":
                rows = con.execute(
                    f"""SELECT "{column}" FROM '{path}' WHERE "{column}" IS NOT NULL"""
                ).fetchall()
                if any(_shingles([value]) & shingles for (value,) in rows):
                    violations.append(f"{path.name}: {column!r} contains abstract text")
    con.close()
    return violations


def _shingles(texts: Iterable[str]) -> set[tuple[str, ...]]:
    found: set[tuple[str, ...]] = set()
    for text in texts:
        words = text.lower().split()
        found.update(
            tuple(words[i : i + SHINGLE_WORDS]) for i in range(len(words) - SHINGLE_WORDS + 1)
        )
    return found
