"""Budget guard and client behaviour. Responses are synthetic, in the shape of live responses."""

import gzip
import json

import httpx
import pytest

from seismohydro_kg.ingest.works import ingest_set
from seismohydro_kg.openalex.budget import BudgetExceeded, BudgetGuard
from seismohydro_kg.openalex.client import ApiKeyRequired, PlanUpgradeRequired, cost_class


def page(cursor, works=("W1",), cost=0.0001):
    return httpx.Response(
        200,
        json={
            "meta": {"count": 1000, "next_cursor": cursor, "cost_usd": cost},
            "results": [{"id": f"https://openalex.org/{work}"} for work in works],
        },
    )


def test_stops_before_a_call_would_pass_the_run_cap(make_client):
    calls = []

    def handler(request):
        calls.append(request)
        return page("next")

    client = make_client(handler, run_cap=0.00025)
    with pytest.raises(BudgetExceeded, match="run cap"):
        for _ in client.iter_pages("type:article", ["id"]):
            pass
    assert len(calls) == 2
    assert client.guard.spent_run_usd == pytest.approx(0.0002)


def test_search_filter_pays_the_search_rate_at_the_cap(make_client):
    calls = []

    def handler(request):
        calls.append(request)
        return page(None, cost=0.001)

    client = make_client(handler, run_cap=0.0005)
    with pytest.raises(BudgetExceeded):
        client.get("/works", {"filter": "title_and_abstract.search:seismic"})
    assert calls == []
    assert cost_class({"filter": "title_and_abstract.search:x"}) == "search"
    assert cost_class({"filter": "primary_topic.id:T1"}) == "list"


def test_daily_cap_carries_across_runs_through_the_ledger(make_client, tmp_path):
    ledger = tmp_path / "ledger.json"
    first = make_client(lambda _r: page(None), run_cap=1.0, daily_cap=0.00015, ledger=ledger)
    first.get("/works", {"filter": "type:article"})
    second = make_client(lambda _r: page(None), run_cap=1.0, daily_cap=0.00015, ledger=ledger)
    with pytest.raises(BudgetExceeded, match="daily cap"):
        second.get("/works", {"filter": "type:article"})


def test_cost_falls_back_from_meta_to_credit_header_to_estimate(make_client):
    responses = [
        httpx.Response(200, json={"meta": {"cost_usd": 0.0007}}),
        httpx.Response(200, json={"meta": {}}, headers={"X-RateLimit-Credits-Used": "10"}),
        httpx.Response(200, json={"meta": {}}),
    ]
    client = make_client(lambda _r: responses.pop(0))
    client.get("/works", {"filter": "type:article"})
    assert client.guard.spent_run_usd == pytest.approx(0.0007)
    client.get("/works", {"filter": "type:article"})
    assert client.guard.spent_run_usd == pytest.approx(0.0017)
    client.get("/works", {"filter": "type:article"})
    assert client.guard.spent_run_usd == pytest.approx(0.0018)


def test_key_goes_in_the_header_and_never_in_the_url(make_client):
    seen = []

    def handler(request):
        seen.append(request)
        return page(None)

    make_client(handler, api_key="secret-value").get("/works", {"filter": "type:article"})
    assert seen[0].headers["Authorization"] == "Bearer secret-value"
    assert "secret-value" not in str(seen[0].url)


def test_cursor_without_a_key_raises_a_clear_error(make_client):
    responses = [page("next"), httpx.Response(401, text="unauthorized")]
    client = make_client(lambda _r: responses.pop(0), api_key=None)
    with pytest.raises(ApiKeyRequired):
        list(client.iter_pages("type:article", ["id"]))


def test_paid_filter_429_is_not_retried(make_client):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": "Plan upgrade required"})

    with pytest.raises(PlanUpgradeRequired):
        make_client(handler).get("/works", {"filter": "from_updated_date:2026-10-01"})
    assert len(calls) == 1


def test_rate_limit_429_is_retried_and_failures_are_not_charged(make_client):
    responses = [httpx.Response(429, text="slow down"), httpx.Response(503), page(None)]
    client = make_client(lambda _r: responses.pop(0))
    client.get("/works", {"filter": "type:article"})
    assert client.guard.spent_run_usd == pytest.approx(0.0001)


def read_ids(directory):
    ids = []
    for path in sorted(directory.glob("part-*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            ids.extend(json.loads(line)["id"].rsplit("/", 1)[-1] for line in handle)
    return ids


def test_ingest_stops_at_the_cap_keeps_what_it_paid_for_and_resumes(make_client, tmp_path):
    pages = {"*": ("c1", "W1"), "c1": ("c2", "W2"), "c2": (None, "W3")}

    def handler(request):
        next_cursor, work = pages[request.url.params["cursor"]]
        return page(next_cursor, works=(work,))

    capped = make_client(handler, run_cap=0.00025)
    first = ingest_set(capped, "demo", "type:article", tmp_path)
    assert first.stopped_at_cap and not first.done
    assert read_ids(tmp_path / "demo") == ["W1", "W2"]

    resumed = ingest_set(make_client(handler), "demo", "type:article", tmp_path)
    assert resumed.done and resumed.stopped_at_cap is None
    assert read_ids(tmp_path / "demo") == ["W1", "W2", "W3"]

    again = make_client(lambda _r: pytest.fail("a finished set must not call the API"))
    assert ingest_set(again, "demo", "type:article", tmp_path).works_written == 3


def test_ingest_refuses_to_mix_filters_in_one_directory(make_client, tmp_path):
    ingest_set(make_client(lambda _r: page(None)), "demo", "type:article", tmp_path)
    with pytest.raises(ValueError, match="different filter"):
        ingest_set(make_client(lambda _r: page(None)), "demo", "type:review", tmp_path)


def test_guard_rejects_zero_room():
    guard = BudgetGuard(run_cap_usd=0.0, daily_cap_usd=1.0)
    with pytest.raises(BudgetExceeded):
        guard.check(0.0001)
