"""Errors must stay readable and must not expose secrets, since CI logs on this repo are public."""

import httpx
from typer.testing import CliRunner

import seismohydro_kg.openalex.client as client_module
from seismohydro_kg.cli import EXIT_API_ERROR, EXIT_STOPPED_AT_CAP, app


def test_tracebacks_do_not_print_local_variables():
    assert app.pretty_exceptions_show_locals is False


def run_ingest(monkeypatch, make_client, handler, **kwargs):
    client = make_client(handler, api_key="secret-value", **kwargs)
    monkeypatch.setattr(client_module, "build_client", lambda *_args, **_kwargs: client)
    return CliRunner().invoke(app, ["ingest", "--set", "seismology_core", "--max-usd", "1"])


def test_api_error_exits_cleanly_without_the_key(monkeypatch, make_client):
    result = run_ingest(
        monkeypatch, make_client, lambda _request: httpx.Response(401, text="key required")
    )
    assert result.exit_code == EXIT_API_ERROR
    assert "OPENALEX_API_KEY" in result.output
    assert "secret-value" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_budget_stop_has_its_own_exit_code(monkeypatch, make_client):
    result = run_ingest(
        monkeypatch,
        make_client,
        lambda _request: httpx.Response(200, json={"meta": {}, "results": []}),
        run_cap=0.0,
    )
    assert result.exit_code == EXIT_STOPPED_AT_CAP
