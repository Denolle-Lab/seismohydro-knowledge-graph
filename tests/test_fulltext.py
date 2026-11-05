"""Full-text download: caps, resume, validity, and keeping the key out of output."""

import os
import stat

import httpx
import pytest
from typer.testing import CliRunner

import seismohydro_kg.openalex.client as client_module
from seismohydro_kg.cli import EXIT_API_ERROR, EXIT_STOPPED_AT_CAP, app
from seismohydro_kg.ingest.fulltext import download_fulltext, select_works

TEI = b"<TEI>synthetic placeholder</TEI>"


def handler_for(work_ids, bodies=None, calls=None):
    """A mock of both hosts: the works list and the content API."""

    def handler(request):
        if calls is not None:
            calls.append(request)
        if request.url.host == "content.openalex.org":
            work = request.url.path.rsplit("/", 1)[-1].split(".")[0]
            body = (bodies or {}).get(work, TEI)
            return httpx.Response(404) if body is None else httpx.Response(200, content=body)
        results = [{"id": f"https://openalex.org/{work}"} for work in work_ids]
        return httpx.Response(
            200, json={"meta": {"next_cursor": None, "cost_usd": 0.0001}, "results": results}
        )

    return handler


def test_selection_asks_for_held_works_sorted_by_citations(make_client):
    calls = []
    client = make_client(handler_for(["W1", "W2", "W3"], calls=calls))
    assert select_works(client, "type:article", "xml", 2) == ["W1", "W2"]
    assert "has_content.grobid_xml:true" in calls[0].url.params["filter"]
    assert calls[0].url.params["sort"] == "cited_by_count:desc"


def test_downloads_write_files_and_charge_per_file(make_client, tmp_path):
    client = make_client(handler_for(["W1", "W2"]))
    result = download_fulltext(client, "demo", "type:article", "xml", 2, tmp_path)
    assert result.downloaded == 2
    assert (tmp_path / "demo" / "xml" / "W1.xml").read_bytes() == TEI
    assert client.guard.spent_run_usd == pytest.approx(0.0001 + 2 * 0.01)


def test_cap_stops_and_a_resume_never_pays_twice(make_client, tmp_path):
    capped = make_client(handler_for(["W1", "W2", "W3"]), run_cap=0.015)
    first = download_fulltext(capped, "demo", "type:article", "xml", 3, tmp_path)
    assert first.stopped_at_cap and first.downloaded == 1

    calls = []
    resumed = make_client(handler_for(["W1", "W2", "W3"], calls=calls))
    second = download_fulltext(resumed, "demo", "type:article", "xml", 3, tmp_path)
    assert (second.already_present, second.downloaded) == (1, 2)
    fetched = [c.url.path for c in calls if c.url.host == "content.openalex.org"]
    assert "/works/W1.grobid-xml" not in fetched
    assert not [c for c in calls if c.url.host != "content.openalex.org"]


def test_missing_file_is_not_charged_and_bad_file_is_not_kept(make_client, tmp_path):
    bodies = {"W1": None, "W2": b"<html-free junk"[6:], "W3": TEI}
    client = make_client(handler_for(["W1", "W2", "W3"], bodies=bodies))
    result = download_fulltext(client, "demo", "type:article", "xml", 3, tmp_path)
    assert (result.unavailable, result.invalid, result.downloaded) == (1, 1, 1)
    assert not (tmp_path / "demo" / "xml" / "W2.xml").exists()


def test_pdf_validity_check(make_client, tmp_path):
    bodies = {"W1": b"%PDF-1.7 synthetic", "W2": b"<html>not a pdf</html>"}
    client = make_client(handler_for(["W1", "W2"], bodies=bodies))
    result = download_fulltext(client, "demo", "type:article", "pdf", 2, tmp_path)
    assert (result.downloaded, result.invalid) == (1, 1)


def test_larger_limit_reselects_and_keeps_existing_files(make_client, tmp_path):
    make_pilot = make_client(handler_for(["W1", "W2"]))
    download_fulltext(make_pilot, "demo", "type:article", "xml", 1, tmp_path)
    larger = make_client(handler_for(["W1", "W2"]))
    result = download_fulltext(larger, "demo", "type:article", "xml", 2, tmp_path)
    assert (result.already_present, result.downloaded) == (1, 1)


def test_changed_filter_is_refused(make_client, tmp_path):
    download_fulltext(make_client(handler_for(["W1"])), "demo", "type:article", "xml", 1, tmp_path)
    with pytest.raises(ValueError, match="different filter"):
        download_fulltext(
            make_client(handler_for(["W1"])), "demo", "type:review", "xml", 1, tmp_path
        )


def run_cli(monkeypatch, client, *extra):
    monkeypatch.setattr(client_module, "build_client", lambda *_a, **_k: client)
    arguments = ["fulltext", "--set", "bridge_keyword_and", "--limit", "2", "--max-usd", "1"]
    return CliRunner().invoke(app, [*arguments, *extra])


def test_cli_without_a_key_spends_nothing(monkeypatch, make_client):
    calls = []
    client = make_client(handler_for(["W1"], calls=calls), api_key=None)
    result = run_cli(monkeypatch, client)
    assert result.exit_code == EXIT_API_ERROR
    assert calls == []


def test_cli_errors_never_show_the_key(monkeypatch, make_client):
    def handler(request):
        if request.url.host == "content.openalex.org":
            return httpx.Response(401, text="bad key")
        return handler_for(["W1"])(request)

    result = run_cli(monkeypatch, make_client(handler, api_key="secret-value"))
    assert result.exit_code == EXIT_API_ERROR
    assert "secret-value" not in result.output


def test_cli_budget_stop_has_its_own_exit_code(monkeypatch, make_client):
    client = make_client(handler_for(["W1", "W2"]), run_cap=0.015)
    assert run_cli(monkeypatch, client).exit_code == EXIT_STOPPED_AT_CAP


def test_cli_refuses_audit_sets(monkeypatch, make_client):
    monkeypatch.setattr(
        client_module, "build_client", lambda *_a, **_k: make_client(handler_for([]))
    )
    arguments = ["fulltext", "--set", "seismo_keyword_audit", "--limit", "1", "--max-usd", "1"]
    assert CliRunner().invoke(app, arguments).exit_code != 0


def test_files_are_private_to_the_user(monkeypatch, make_client, tmp_path):
    previous = os.umask(0o022)
    try:
        client = make_client(handler_for(["W1"]))
        result = run_cli(monkeypatch, client, "--out", str(tmp_path))
        assert result.exit_code == 0, result.output
        written = tmp_path / "bridge_keyword_and" / "xml" / "W1.xml"
        assert stat.S_IMODE(written.stat().st_mode) == 0o600
        assert stat.S_IMODE(written.parent.stat().st_mode) == 0o700
    finally:
        os.umask(previous)
