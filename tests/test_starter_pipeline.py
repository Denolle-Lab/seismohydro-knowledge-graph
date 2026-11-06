"""Fetch by ID, match, build, validate, report, export: the first graph a student builds."""

import csv
import json

import httpx
from typer.testing import CliRunner

import seismohydro_kg.openalex.client as client_module
from seismohydro_kg.cli import app
from seismohydro_kg.config import FIXTURE_DIR
from seismohydro_kg.ingest.works import ID_CHUNK, ingest_ids


def fixture_records():
    lines = (FIXTURE_DIR / "works_synthetic.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_ids_are_fetched_in_chunks_without_paging(tmp_path, make_client):
    seen = []

    def handler(request):
        seen.append(request.url.params)
        return httpx.Response(200, json={"meta": {}, "results": [{"id": "x"}]})

    client = make_client(handler, api_key=None)
    ids = [f"W{index}" for index in range(ID_CHUNK + 1)]
    result = ingest_ids(client, "picked", ids, tmp_path)
    assert len(seen) == 2
    assert all("cursor" not in params for params in seen)
    assert seen[0]["filter"].startswith("ids.openalex:W0|W1|")
    assert result.works_written == 2 and result.done
    assert (tmp_path / "picked" / "part-00000.jsonl.gz").exists()


def test_budget_stop_keeps_what_was_paid_for(tmp_path, make_client):
    client = make_client(
        lambda _r: httpx.Response(
            200, json={"meta": {"cost_usd": 0.0001}, "results": [{"id": "x"}]}
        ),
        run_cap=0.0001,
    )
    result = ingest_ids(client, "picked", [f"W{i}" for i in range(ID_CHUNK + 1)], tmp_path)
    assert result.works_written == 1 and not result.done
    assert "run cap" in result.stopped_at_cap


def test_whole_path_builds_a_valid_graph(tmp_path, make_client, monkeypatch):
    records = fixture_records()

    def handler(_request):
        return httpx.Response(200, json={"meta": {"cost_usd": 0.0001}, "results": records})

    client = make_client(handler, api_key=None)
    monkeypatch.setattr(client_module, "build_client", lambda *_a, **_k: client)
    picked = tmp_path / "picked.csv"
    with open(picked, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["openalex_id"])
        writer.writerows([record["id"].rsplit("/", 1)[-1]] for record in records)
    raw, graph = tmp_path / "raw", tmp_path / "graph"
    assertions = tmp_path / "gazetteer.jsonl"
    runner = CliRunner()
    steps = [
        ["ingest-ids", "--csv", str(picked), "--set", "s", "--raw-dir", str(raw), "--max-usd", "1"],
        ["extract", "gazetteer", "--raw-dir", str(raw), "--out", str(assertions)],
        [
            "graph",
            "build",
            "--raw-dir",
            str(raw),
            "--assertions",
            str(assertions),
            "--out",
            str(graph),
        ],
        ["graph", "validate", "--path", str(graph)],
        ["graph", "report", "--path", str(graph)],
        ["graph", "export", "--path", str(graph), "--core"],
    ]
    for step in steps:
        result = runner.invoke(app, step)
        assert result.exit_code == 0, f"{step}: {result.output}"
    core = (graph / "export" / "graph-core.graphml").read_text(encoding="utf-8")
    sample = runner.invoke(
        app,
        ["extract", "sample", "--assertions", str(assertions), "--raw-dir", str(raw), "--n", "1"],
    )
    assert sample.exit_code == 0 and "[[" in sample.output
    assert "edge_type" in core and "W900000099" not in core  # a cited work outside the set
