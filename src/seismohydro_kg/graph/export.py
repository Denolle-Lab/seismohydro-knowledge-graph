"""Exports for other tools. Parquet stays the canonical store.

Turtle for the ontology layers comes in M3, generated from the LinkML schema.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import quoteattr

import duckdb


def export_neo4j(graph_dir: Path, out_dir: Path) -> list[Path]:
    """CSV files with headers for `neo4j-admin database import`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes_csv = out_dir / "nodes.csv"
    edges_csv = out_dir / "edges.csv"
    con = duckdb.connect()
    con.execute(
        f"""COPY (
            SELECT node_id AS "node_id:ID", label, domain, layer, attrs, node_type AS ":LABEL"
            FROM '{graph_dir}/nodes.parquet'
        ) TO '{nodes_csv}' (HEADER, DELIMITER ',')"""
    )
    con.execute(
        f"""COPY (
            SELECT source AS ":START_ID", target AS ":END_ID", edge_type AS ":TYPE", layer,
                   work_id, char_start, char_end, extractor_version, confidence, tier
            FROM '{graph_dir}/edges.parquet'
        ) TO '{edges_csv}' (HEADER, DELIMITER ',')"""
    )
    con.close()
    return [nodes_csv, edges_csv]


def export_graphml(graph_dir: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        handle.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        handle.write('<key id="label" for="node" attr.name="label" attr.type="string"/>\n')
        handle.write('<key id="type" for="node" attr.name="type" attr.type="string"/>\n')
        handle.write('<key id="layer" for="node" attr.name="layer" attr.type="string"/>\n')
        handle.write('<key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>\n')
        handle.write('<graph edgedefault="directed">\n')
        for node_id, node_type, layer, label in con.execute(
            f"SELECT node_id, node_type, layer, label FROM '{graph_dir}/nodes.parquet'"
        ).fetchall():
            handle.write(f"<node id={quoteattr(node_id)}>")
            handle.write(f'<data key="type">{_text(node_type)}</data>')
            handle.write(f'<data key="layer">{_text(layer)}</data>')
            handle.write(f'<data key="label">{_text(label)}</data></node>\n')
        for source, target, edge_type in con.execute(
            f"SELECT source, target, edge_type FROM '{graph_dir}/edges.parquet'"
        ).fetchall():
            handle.write(f"<edge source={quoteattr(source)} target={quoteattr(target)}>")
            handle.write(f'<data key="edge_type">{_text(edge_type)}</data></edge>\n')
        handle.write("</graph>\n</graphml>\n")
    con.close()
    return out_path


def _text(value: str | None) -> str:
    if value is None:
        return ""
    return quoteattr(value)[1:-1]
