import json
import xml.etree.ElementTree as ET

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from typer.testing import CliRunner

from seismohydro_kg.cli import app
from seismohydro_kg.config import FIXTURE_DIR
from seismohydro_kg.graph.build import build_graph, work_rows
from seismohydro_kg.graph.export import export_graphml, export_neo4j
from seismohydro_kg.graph.validate import validate_graph
from seismohydro_kg.openalex.abstracts import reconstruct_abstract

WORKS = FIXTURE_DIR / "works_synthetic.jsonl"
GOOD = FIXTURE_DIR / "assertions_synthetic.jsonl"
BAD = FIXTURE_DIR / "assertions_missing_provenance.jsonl"


@pytest.fixture
def graph_dir(tmp_path):
    build_graph({"fixture": [WORKS]}, [GOOD], tmp_path)
    return tmp_path


def rows(sql):
    return duckdb.sql(sql).fetchall()


def test_fixture_graph_passes(graph_dir):
    assert validate_graph(graph_dir) == []


def test_fixture_offsets_point_at_the_claimed_text():
    works = {
        json.loads(line)["id"].rsplit("/", 1)[-1]: json.loads(line)
        for line in WORKS.read_text().splitlines()
    }
    first, second, third = [json.loads(line) for line in GOOD.read_text().splitlines()]
    abstract = reconstruct_abstract(works["W900000001"]["abstract_inverted_index"])
    assert abstract[first["char_start"] : first["char_end"]] == "dv/v"
    assert abstract[second["char_start"] : second["char_end"]] == "dv/v and groundwater storage"
    other = reconstruct_abstract(works["W900000003"]["abstract_inverted_index"])
    assert other[third["char_start"] : third["char_end"]] == "Placeholder words on bedload"[:27]


def test_edge_without_provenance_fails(tmp_path):
    build_graph({"fixture": [WORKS]}, [BAD], tmp_path)
    violations = "\n".join(validate_graph(tmp_path))
    assert "without work_id" in violations
    assert "without valid character offsets" in violations
    assert "without extractor_version" in violations
    assert "without confidence" in violations


def test_dangling_edge_fails(tmp_path):
    bad = tmp_path / "dangling.jsonl"
    record = json.loads(GOOD.read_text().splitlines()[0])
    bad.write_text(json.dumps({**record, "target": "seis:not_a_concept"}) + "\n")
    out = tmp_path / "graph"
    build_graph({"fixture": [WORKS]}, [bad], out)
    assert any("endpoint not in nodes" in item for item in validate_graph(out))


def test_out_of_corpus_citation_becomes_a_stub(graph_dir):
    found = rows(f"SELECT attrs FROM '{graph_dir}/nodes.parquet' WHERE node_id = 'W900000099'")
    assert json.loads(found[0][0]) == {"in_corpus": False}


def test_citation_edges_reconcile_with_referenced_works(graph_dir):
    expected = sum(
        len(json.loads(line)["referenced_works"]) for line in WORKS.read_text().splitlines()
    )
    actual = rows(f"SELECT count(*) FROM '{graph_dir}/edges.parquet' WHERE edge_type = 'cites'")
    assert actual[0][0] == expected


def test_repeated_work_across_sets_is_deduplicated(tmp_path):
    counts = build_graph({"a": [WORKS], "b": [WORKS]}, [GOOD], tmp_path)
    assert counts["works_in_corpus"] == 3
    assert validate_graph(tmp_path) == []
    memberships = rows(f"SELECT count(*) FROM '{tmp_path}/work_sets.parquet'")
    assert memberships[0][0] == 6


def test_abstract_becomes_a_flag_only(graph_dir):
    attrs = rows(f"SELECT attrs FROM '{graph_dir}/nodes.parquet' WHERE node_id = 'W900000001'")
    assert json.loads(attrs[0][0])["has_abstract"] is True
    tables = "".join(str(rows(f"SELECT * FROM '{path}'")) for path in graph_dir.glob("*.parquet"))
    assert "placeholder" not in tables


def test_vocabulary_and_mechanisms_become_nodes(graph_dir):
    layers = dict(rows(f"SELECT layer, count(*) FROM '{graph_dir}/nodes.parquet' GROUP BY 1"))
    assert layers["L1"] > 50
    assert layers["L3"] == 11


def test_curated_links_become_l1_edges(graph_dir):
    found = rows(
        f"""SELECT source, edge_type, target FROM '{graph_dir}/edges.parquet'
            WHERE layer = 'L1' AND tier = 'human'"""
    )
    assert ("shared:river_channel", "broader", "shared:surface_water") in found
    assert ("hydro:well_water_level", "proxy_for", "hydro:hydraulic_head") in found
    assert ("seis:full_waveform_inversion", "typical_approach", "shared:hybrid") in found


def test_soil_moisture_and_approaches_have_the_intended_types(graph_dir):
    found = dict(
        rows(
            f"""SELECT node_id, node_type FROM '{graph_dir}/nodes.parquet'
                WHERE node_id IN ('hydro:soil_moisture', 'shared:surface_water',
                                  'shared:groundwater', 'shared:model_driven', 'hydro:flood')"""
        )
    )
    assert found == {
        "hydro:soil_moisture": "StateVariable",
        "shared:surface_water": "Compartment",
        "shared:groundwater": "Compartment",
        "shared:model_driven": "ResearchApproach",
        "hydro:flood": "Hazard",
    }


def test_work_without_author_id_or_source_still_builds():
    record = json.loads(WORKS.read_text().splitlines()[2])
    nodes, edges = work_rows(record)
    assert {node["node_type"] for node in nodes} == {"Work", "Author", "Institution"}
    assert all(edge["source"] != "None" for edge in edges)


def test_exports(graph_dir):
    nodes_csv, edges_csv = export_neo4j(graph_dir, graph_dir / "neo4j")
    assert nodes_csv.read_text().startswith("node_id:ID")
    assert ":START_ID" in edges_csv.read_text().splitlines()[0]
    tree = ET.parse(export_graphml(graph_dir, graph_dir / "graph.graphml"))
    namespace = "{http://graphml.graphdrawing.org/xmlns}"
    assert len(tree.findall(f".//{namespace}edge")) > 0


def test_missing_table_is_reported(tmp_path):
    pq.write_table(pa.table({"node_id": ["a"]}), tmp_path / "nodes.parquet")
    assert validate_graph(tmp_path) == ["missing table: edges.parquet"]


def test_cli_build_and_validate_fixture():
    runner = CliRunner()
    built = runner.invoke(app, ["graph", "build", "--fixture"])
    assert built.exit_code == 0, built.output
    assert runner.invoke(app, ["graph", "validate", "--fixture"]).exit_code == 0


def test_cli_validate_exits_nonzero_on_missing_provenance(tmp_path):
    runner = CliRunner()
    out = str(tmp_path / "bad")
    built = runner.invoke(
        app, ["graph", "build", "--fixture", "--assertions", str(BAD), "--out", out]
    )
    assert built.exit_code == 0, built.output
    assert runner.invoke(app, ["graph", "validate", "--path", out]).exit_code == 1


def test_core_export_keeps_concepts_that_are_only_edge_sources(tmp_path):
    # A concept-to-concept claim whose source concept no paper mentions (Copilot review, PR #1).
    claim = [line for line in GOOD.read_text().splitlines() if '"responds_to"' in line]
    assertions = tmp_path / "claims.jsonl"
    assertions.write_text("\n".join(claim) + "\n")
    build_graph({"fixture": [WORKS]}, [assertions], tmp_path / "graph")
    tree = ET.parse(export_graphml(tmp_path / "graph", tmp_path / "core.graphml", core=True))
    namespace = "{http://graphml.graphdrawing.org/xmlns}"
    nodes = {node.get("id") for node in tree.iter(f"{namespace}node")}
    edges = list(tree.iter(f"{namespace}edge"))
    assert "seis:dv_v" in nodes
    assert edges and all(e.get("source") in nodes and e.get("target") in nodes for e in edges)
