import httpx
import pytest
from typer.testing import CliRunner

from seismohydro_kg.cli import app
from seismohydro_kg.config import load_scope
from seismohydro_kg.scope import build_filter, ingest_sets, scope_report


def test_core_set_filter_uses_topics_and_types():
    filter_ = build_filter("seismology_core", load_scope())
    assert filter_.startswith("primary_topic.id:T10110|")
    assert filter_.endswith("type:article|review|preprint")
    assert ".search" not in filter_


def test_bridge_filter_expands_both_keyword_lists():
    filter_ = build_filter("bridge_keyword_and", load_scope())
    assert "(seismology OR seismic" in filter_ and ") AND (hydrology OR" in filter_


def test_exclusions_become_negated_filters():
    filter_ = build_filter("seismo_keyword_no_engineering_audit", load_scope())
    assert "primary_topic.id:!T10160" in filter_


def test_publication_window_is_appended():
    filter_ = build_filter("hydrology_core", load_scope(), from_publication_date="2025-01-01")
    assert filter_.endswith("from_publication_date:2025-01-01")


def test_audit_sets_are_never_ingested():
    names = ingest_sets(load_scope())
    assert "seismology_core" in names
    assert not [name for name in names if name.endswith("_audit")]


def groups(true_count, false_count):
    return httpx.Response(
        200,
        json={
            "meta": {"cost_usd": 0.0001},
            "group_by": [
                {"key": "true", "key_display_name": "true", "count": true_count},
                {"key": "false", "key_display_name": "false", "count": false_count},
            ],
        },
    )


def test_report_computes_costs_and_baseline_delta(make_client):
    scope = {
        "work_types": ["article"],
        "keywords": {"seismo": "seismic"},
        "topic_groups": {"t": ["T1"]},
        "sets": {
            "core": {"role": "core", "topics": "t", "baseline": {"count": 1000}},
            "audit": {"role": "audit", "search": "{seismo}"},
        },
    }
    report = scope_report(make_client(lambda _r: groups(600, 500)), scope)
    core, audit = report["sets"]
    assert core["count"] == 1100
    assert core["abstract_share"] == pytest.approx(0.545)
    assert core["ingest_calls"] == 11
    assert core["ingest_usd"] == pytest.approx(0.0011)
    assert core["baseline_delta"] == pytest.approx(0.1)
    assert audit["baseline_delta"] is None
    assert report["ingest_usd_upper_bound"] == pytest.approx(0.0011)
    assert report["stopped_at_cap"] is None


def test_report_stops_at_the_cap_and_keeps_partial_results(make_client):
    scope = {
        "work_types": ["article"],
        "keywords": {"seismo": "seismic"},
        "topic_groups": {"t": ["T1"]},
        "sets": {
            "core": {"role": "core", "topics": "t"},
            "audit": {"role": "audit", "search": "{seismo}"},
        },
    }
    report = scope_report(make_client(lambda _r: groups(1, 1), run_cap=0.0005), scope)
    assert [row["name"] for row in report["sets"]] == ["core"]
    assert "run cap" in report["stopped_at_cap"]


@pytest.mark.parametrize(
    ("command", "milestone"),
    [
        (["extract", "discovery", "--max-usd", "1"], "M3"),
        (["opportunities"], "M6"),
        (["holdout"], "M6"),
    ],
)
def test_stubs_name_their_milestone(command, milestone):
    result = CliRunner().invoke(app, command)
    assert isinstance(result.exception, NotImplementedError)
    assert milestone in str(result.exception)
