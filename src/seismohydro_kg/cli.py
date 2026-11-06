"""`shkg` command line. Each stage is idempotent and writes a manifest to data/manifests/."""

from __future__ import annotations

import csv
import itertools
import json
import os
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer

from seismohydro_kg.config import (
    CONFIG_DIR,
    FIXTURE_DIR,
    ONTOLOGY_DIR,
    REPO_ROOT,
    data_dir,
    load_budget,
    load_scope,
)
from seismohydro_kg.manifest import stage_manifest

# Tracebacks must not print local variables. CI logs on a public repository are public, and locals
# can hold request headers or abstract text.
app = typer.Typer(
    no_args_is_help=True,
    help="Seismohydro knowledge graph pipeline.",
    pretty_exceptions_show_locals=False,
)
graph_app = typer.Typer(no_args_is_help=True, help="Build, validate and export the graph.")
ontology_app = typer.Typer(no_args_is_help=True, help="Check the schema and vocabularies.")
extract_app = typer.Typer(no_args_is_help=True, help="Literature extraction (M3, M4).")
app.add_typer(graph_app, name="graph")
app.add_typer(ontology_app, name="ontology")
app.add_typer(extract_app, name="extract")

EXIT_VIOLATIONS = 1
EXIT_STOPPED_AT_CAP = 2
EXIT_API_ERROR = 3


@app.callback()
def main() -> None:
    """Seismohydro knowledge graph pipeline."""
    # Everything shkg writes is private to the user who ran it. Raw records and full text must not
    # be readable by others on a shared machine. Share derived tables deliberately, with chmod.
    os.umask(0o077)


def _load_env() -> None:
    """Read REPO_ROOT/.env into the environment without overriding values already set."""
    path = REPO_ROOT / ".env"
    if not path.exists():
        return
    if path.stat().st_mode & 0o077:
        typer.echo(f"WARNING: other users can read {path}. Run: chmod 600 {path}", err=True)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _default_graph_dir(fixture: bool) -> Path:
    return data_dir() / ("fixture_graph" if fixture else "graph")


def _report_violations(violations: list[str]) -> None:
    if violations:
        for violation in violations:
            typer.echo(f"FAIL  {violation}", err=True)
        raise typer.Exit(EXIT_VIOLATIONS)


@app.command("scope-report")
def scope_report_command(
    max_usd: Annotated[float | None, typer.Option(help="Cap for this run.")] = None,
) -> None:
    """Count every scope set live, compare with the baseline and estimate ingest cost."""
    from seismohydro_kg.openalex.client import build_client
    from seismohydro_kg.scope import scope_report, write_report

    _load_env()
    cap = max_usd if max_usd is not None else load_budget()["openalex"]["run_usd"]["scope_report"]
    client = build_client(cap)
    paths = [CONFIG_DIR / "scope.yaml", CONFIG_DIR / "budget.yaml"]
    with stage_manifest("scope-report", paths) as manifest:
        report = scope_report(client, load_scope())
        manifest["usd_spent"] = report["usd_spent"]
        manifest["counts"] = {row["name"]: row["count"] for row in report["sets"]}
        path = write_report(report, data_dir() / "reports")

    header = f"{'set':38s}{'role':8s}{'count':>9s}{'abstract':>10s}{'ingest $':>10s}{'vs base':>9s}"
    typer.echo(header)
    for row in report["sets"]:
        delta = row["baseline_delta"]
        delta_text = "" if delta is None else f"{delta:+.2%}"
        typer.echo(
            f"{row['name']:38s}{row['role']:8s}{row['count']:>9d}"
            f"{row['abstract_share']:>10.1%}{row['ingest_usd']:>10.4f}{delta_text:>9s}"
        )
    typer.echo(f"Ingest upper bound ${report['ingest_usd_upper_bound']:.2f} (sets may overlap).")
    typer.echo(f"Spent ${report['usd_spent']:.4f}. Report: {path}")
    if report["stopped_at_cap"]:
        typer.echo(f"Stopped at cap: {report['stopped_at_cap']}", err=True)
        raise typer.Exit(EXIT_STOPPED_AT_CAP)


@app.command()
def ingest(
    set_name: Annotated[str, typer.Option("--set", help="Scope set name, or 'all'.")] = "all",
    max_usd: Annotated[float | None, typer.Option(help="Cap for this run.")] = None,
    window_months: Annotated[
        int | None, typer.Option(help="Only works published in the trailing N months.")
    ] = None,
    raw_dir: Annotated[Path | None, typer.Option(help="Output root.")] = None,
) -> None:
    """Download scope sets, resuming from checkpoints. Needs OPENALEX_API_KEY."""
    from seismohydro_kg.ingest.works import ingest_set
    from seismohydro_kg.openalex.client import OpenAlexError, build_client
    from seismohydro_kg.scope import build_filter, ingest_sets

    _load_env()
    scope = load_scope()
    budget_key = "refresh" if window_months else "ingest"
    cap = max_usd if max_usd is not None else load_budget()["openalex"]["run_usd"][budget_key]
    client = build_client(cap)
    from_date = None
    if window_months:
        from_date = (datetime.now(UTC) - timedelta(days=window_months * 31)).strftime("%Y-%m-%d")
    names = ingest_sets(scope) if set_name == "all" else [set_name]
    root = raw_dir or data_dir() / "raw"

    stopped = None
    failure = None
    with stage_manifest("ingest", [CONFIG_DIR / "scope.yaml"]) as manifest:
        try:
            for name in names:
                filter_ = build_filter(name, scope, from_publication_date=from_date)
                result = ingest_set(client, name, filter_, root)
                manifest["counts"][name] = result.works_written
                typer.echo(f"{name}: {result.works_written} works, done={result.done}")
                if result.stopped_at_cap:
                    stopped = result.stopped_at_cap
                    break
        except OpenAlexError as exc:
            # Pages already paid for are on disk. Rerunning resumes from the checkpoint.
            manifest["status"] = "api_error"
            manifest["error"] = type(exc).__name__
            failure = str(exc)
        finally:
            manifest["usd_spent"] = round(client.guard.spent_run_usd, 6)
        if stopped:
            manifest["status"] = "stopped_at_cap"
    typer.echo(f"Spent ${client.guard.spent_run_usd:.4f}.")
    if failure:
        typer.echo(f"Stopped on an API error: {failure}", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    if stopped:
        typer.echo(f"Stopped at cap: {stopped}. Run again to resume.", err=True)
        raise typer.Exit(EXIT_STOPPED_AT_CAP)


@app.command("ingest-ids")
def ingest_ids_command(
    csv_path: Annotated[Path, typer.Option("--csv", help="CSV with an openalex_id column.")],
    set_name: Annotated[str, typer.Option("--set", help="Name for this set of works.")],
    max_usd: Annotated[float, typer.Option(help="Required spending cap for this run.")],
    raw_dir: Annotated[Path | None, typer.Option(help="Raw works root.")] = None,
) -> None:
    """Fetch a hand-picked list of works, for example docs/starter-set-100.csv."""
    from seismohydro_kg.ingest.works import ingest_ids
    from seismohydro_kg.openalex.client import OpenAlexError, build_client

    _load_env()
    with open(csv_path, encoding="utf-8", newline="") as handle:
        work_ids = [row["openalex_id"] for row in csv.DictReader(handle)]
    client = build_client(max_usd)
    failure = None
    result = None
    with stage_manifest("ingest-ids", [csv_path]) as manifest:
        try:
            result = ingest_ids(client, set_name, work_ids, raw_dir or data_dir() / "raw")
            manifest["counts"] = {"requested": len(work_ids), "written": result.works_written}
            if result.stopped_at_cap:
                manifest["status"] = "stopped_at_cap"
        except OpenAlexError as exc:
            manifest["status"] = "api_error"
            manifest["error"] = type(exc).__name__
            failure = str(exc)
        finally:
            manifest["usd_spent"] = round(client.guard.spent_run_usd, 6)
    if result:
        typer.echo(f"{set_name}: {result.works_written} of {len(work_ids)} works written.")
    typer.echo(f"Spent ${client.guard.spent_run_usd:.4f}.")
    if failure:
        typer.echo(f"Stopped on an API error: {failure}", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    if result and result.stopped_at_cap:
        typer.echo(f"Stopped at cap: {result.stopped_at_cap}", err=True)
        raise typer.Exit(EXIT_STOPPED_AT_CAP)


@app.command()
def fulltext(
    set_name: Annotated[str, typer.Option("--set", help="Scope set to take works from.")],
    limit: Annotated[int, typer.Option(help="Number of most-cited works to fetch.")],
    max_usd: Annotated[float, typer.Option(help="Required spending cap for this run.")],
    format_: Annotated[str, typer.Option("--format", help="xml (TEI) or pdf.")] = "xml",
    out: Annotated[Path | None, typer.Option(help="Output root.")] = None,
) -> None:
    """Download full text from OpenAlex at $0.01 per file. Needs OPENALEX_API_KEY."""
    from seismohydro_kg.ingest.fulltext import FORMATS, download_fulltext
    from seismohydro_kg.openalex.client import OpenAlexError, build_client
    from seismohydro_kg.scope import build_filter, ingest_sets

    _load_env()
    scope = load_scope()
    if set_name not in ingest_sets(scope):
        raise typer.BadParameter(f"choose from {', '.join(ingest_sets(scope))}")
    if format_ not in FORMATS:
        raise typer.BadParameter("use xml or pdf")
    client = build_client(max_usd)
    if not client.has_key:
        typer.echo("Full text needs a key: set OPENALEX_API_KEY. Nothing was spent.", err=True)
        raise typer.Exit(EXIT_API_ERROR)

    failure = None
    result = None
    with stage_manifest("fulltext", [CONFIG_DIR / "scope.yaml"]) as manifest:
        try:
            result = download_fulltext(
                client,
                set_name,
                build_filter(set_name, scope),
                format_,
                limit,
                out or data_dir() / "fulltext",
            )
            manifest["counts"] = {
                "selected": result.selected,
                "downloaded": result.downloaded,
                "already_present": result.already_present,
                "unavailable": result.unavailable,
                "invalid": result.invalid,
                "previously_rejected": result.previously_rejected,
            }
            if result.stopped_at_cap:
                manifest["status"] = "stopped_at_cap"
            elif result.stopped_reason:
                manifest["status"] = "stopped_all_rejected"
        except OpenAlexError as exc:
            manifest["status"] = "api_error"
            manifest["error"] = type(exc).__name__
            failure = str(exc)
        finally:
            manifest["usd_spent"] = round(client.guard.spent_run_usd, 6)
    if result:
        typer.echo(
            f"{set_name} {format_}: {result.downloaded} downloaded, "
            f"{result.already_present} already present, {result.unavailable} unavailable, "
            f"{result.invalid} rejected, {result.previously_rejected} rejected earlier "
            f"(not paid again), of {result.selected} selected."
        )
    typer.echo(f"Spent ${client.guard.spent_run_usd:.4f}.")
    if failure:
        typer.echo(f"Stopped on an API error: {failure}. Run again to resume.", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    if result and result.stopped_reason:
        typer.echo(f"Stopped: {result.stopped_reason}.", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    if result and result.stopped_at_cap:
        typer.echo(f"Stopped at cap: {result.stopped_at_cap}. Run again to resume.", err=True)
        raise typer.Exit(EXIT_STOPPED_AT_CAP)


@graph_app.command("build")
def graph_build(
    fixture: Annotated[bool, typer.Option(help="Use the synthetic test fixture.")] = False,
    raw_dir: Annotated[Path | None, typer.Option(help="Raw works root.")] = None,
    assertions: Annotated[
        list[Path] | None, typer.Option(help="Assertion JSONL files (L2, L3 edges).")
    ] = None,
    out: Annotated[Path | None, typer.Option(help="Output directory.")] = None,
) -> None:
    """Build nodes.parquet, edges.parquet and work_sets.parquet."""
    from seismohydro_kg.graph.build import build_graph

    out_dir = out or _default_graph_dir(fixture)
    assertion_paths = list(assertions or [])
    if fixture:
        raw_by_set = {"fixture": [FIXTURE_DIR / "works_synthetic.jsonl"]}
        assertion_paths = assertion_paths or [FIXTURE_DIR / "assertions_synthetic.jsonl"]
    else:
        root = raw_dir or data_dir() / "raw"
        if not root.is_dir():
            typer.echo(f"No raw works at {root}. Run `shkg ingest` first.", err=True)
            raise typer.Exit(EXIT_API_ERROR)
        raw_by_set = {
            path.name: sorted(path.glob("part-*.jsonl.gz"))
            for path in sorted(root.iterdir())
            if path.is_dir()
        }
    with stage_manifest("graph-build", [CONFIG_DIR / "scope.yaml"]) as manifest:
        counts = build_graph(raw_by_set, assertion_paths, out_dir)
        manifest["counts"] = counts
    typer.echo(f"{out_dir}: {counts}")


@graph_app.command("validate")
def graph_validate(
    path: Annotated[Path | None, typer.Option(help="Graph directory.")] = None,
    fixture: Annotated[bool, typer.Option(help="Validate the fixture graph.")] = False,
) -> None:
    """Check integrity, provenance and the no-abstract rule."""
    from seismohydro_kg.graph.validate import validate_graph

    graph_dir = path or _default_graph_dir(fixture)
    violations = validate_graph(graph_dir)
    _report_violations(violations)
    typer.echo(f"{graph_dir}: passed")


@graph_app.command("report")
def graph_report_command(
    path: Annotated[Path | None, typer.Option(help="Graph directory.")] = None,
    fixture: Annotated[bool, typer.Option(help="Report on the fixture graph.")] = False,
) -> None:
    """Summarize what a graph holds and how connected it is."""
    from seismohydro_kg.graph.report import format_report, graph_report

    typer.echo(format_report(graph_report(path or _default_graph_dir(fixture))))


@graph_app.command("export")
def graph_export(
    format_: Annotated[str, typer.Option("--format", help="neo4j or graphml.")] = "graphml",
    path: Annotated[Path | None, typer.Option(help="Graph directory.")] = None,
    fixture: Annotated[bool, typer.Option(help="Export the fixture graph.")] = False,
    core: Annotated[
        bool, typer.Option(help="GraphML only: works in the set and the concepts they mention.")
    ] = False,
) -> None:
    """Export for Neo4j or GraphML tools."""
    from seismohydro_kg.graph.export import export_graphml, export_neo4j

    graph_dir = path or _default_graph_dir(fixture)
    if format_ == "neo4j":
        written = export_neo4j(graph_dir, graph_dir / "export" / "neo4j")
    elif format_ == "graphml":
        name = "graph-core.graphml" if core else "graph.graphml"
        written = [export_graphml(graph_dir, graph_dir / "export" / name, core=core)]
    else:
        raise typer.BadParameter("use neo4j or graphml")
    typer.echo("\n".join(str(item) for item in written))


@ontology_app.command("validate")
def ontology_validate() -> None:
    """Validate vocabularies, mechanisms and mappings against the LinkML schema."""
    from seismohydro_kg.ontology import validate_ontology

    _report_violations(validate_ontology())
    typer.echo(f"{ONTOLOGY_DIR}: passed")


@extract_app.command("discovery")
def extract_discovery(
    max_usd: Annotated[float, typer.Option(help="Required spending cap for this run.")],
) -> None:
    """Open extraction before the schema is frozen. Not built until M3."""
    from seismohydro_kg.extract.discovery import run_discovery

    run_discovery(_default_graph_dir(False), data_dir() / "discovery" / "candidates.jsonl", max_usd)


@extract_app.command("gazetteer")
def extract_gazetteer(
    raw_dir: Annotated[Path | None, typer.Option(help="Raw works root.")] = None,
    out: Annotated[Path | None, typer.Option(help="Output JSON Lines file.")] = None,
) -> None:
    """Tier 1: match vocabulary terms in titles and abstracts. Local and free."""
    from seismohydro_kg.extract.gazetteer import run_gazetteer
    from seismohydro_kg.extract.text import raw_parts

    parts = raw_parts(raw_dir or data_dir() / "raw")
    if not parts:
        typer.echo("No raw works found. Run `shkg ingest` or `shkg ingest-ids` first.", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    out_path = out or data_dir() / "assertions" / "gazetteer.jsonl"
    with stage_manifest("extract-gazetteer", ONTOLOGY_DIR.glob("vocab/*.yaml")) as manifest:
        manifest["counts"] = run_gazetteer(parts, out_path)
    typer.echo(f"{out_path}: {manifest['counts']}")


@extract_app.command("sample")
def extract_sample(
    assertions: Annotated[Path, typer.Option(help="Assertion JSON Lines file.")],
    raw_dir: Annotated[Path | None, typer.Option(help="Raw works root.")] = None,
    n: Annotated[int, typer.Option(help="How many edges to show.")] = 20,
    seed: Annotated[int, typer.Option(help="Random seed, so a sample can be repeated.")] = 1,
) -> None:
    """Print random edges with surrounding text, to judge by eye. Terminal only: do not share it."""
    from seismohydro_kg.extract.text import iter_works, raw_parts, work_text

    with open(assertions, encoding="utf-8") as handle:
        edges = [json.loads(line) for line in handle if line.strip()]
    texts = {
        work_id: work_text(record)
        for work_id, record in iter_works(raw_parts(raw_dir or data_dir() / "raw"))
    }
    for edge in random.Random(seed).sample(edges, min(n, len(edges))):
        text = texts.get(edge["work_id"]) or ""
        start, end = edge["char_start"], edge["char_end"]
        before, hit, after = text[max(0, start - 60) : start], text[start:end], text[end : end + 60]
        context = f"{before}[[{hit}]]{after}".replace("\n", " ")
        typer.echo(f"{edge['work_id']} {edge['edge_type']} {edge['target']}\n    {context}")


@extract_app.command("llm")
def extract_llm(
    provider: Annotated[
        str | None, typer.Option(help="A name under `providers` in config/extraction.yaml.")
    ] = None,
    raw_dir: Annotated[Path | None, typer.Option(help="Raw works root.")] = None,
    out_dir: Annotated[Path | None, typer.Option(help="Output root.")] = None,
    max_usd: Annotated[float | None, typer.Option(help="Cap in USD, if metered.")] = None,
    limit: Annotated[int | None, typer.Option(help="Stop after this many calls.")] = None,
) -> None:
    """Tier 3: LLM extraction with a pluggable model, one call per work."""
    from seismohydro_kg.extract.llm import run_extraction
    from seismohydro_kg.extract.providers import extraction_config, load_provider
    from seismohydro_kg.extract.providers.base import ProviderError
    from seismohydro_kg.extract.text import iter_works, raw_parts
    from seismohydro_kg.openalex.budget import BudgetGuard

    _load_env()
    config = extraction_config()
    parts = raw_parts(raw_dir or data_dir() / "raw")
    if not parts:
        typer.echo("No raw works found. Run `shkg ingest` or `shkg ingest-ids` first.", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    try:
        model = load_provider(provider, config)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None

    cap = load_budget()["llm"]["run_usd_cap"]
    if model.metered:
        if max_usd is None:
            typer.echo(f"{model.name} costs money: pass --max-usd. Nothing was spent.", err=True)
            raise typer.Exit(EXIT_STOPPED_AT_CAP)
        if max_usd > cap:
            typer.echo(f"--max-usd is above the ${cap:.2f} cap in config/budget.yaml.", err=True)
            raise typer.Exit(EXIT_STOPPED_AT_CAP)
        # Count no further than the limit: on a full corpus a complete count is slow.
        planned = limit or sum(
            1 for _ in itertools.islice(iter_works(parts), config["realtime_work_limit"] + 1)
        )
        if planned > config["realtime_work_limit"]:
            typer.echo(
                f"{planned} works is too many for real-time calls at full price. "
                "Use --limit, or wait for Message Batches in M4.",
                err=True,
            )
            raise typer.Exit(EXIT_STOPPED_AT_CAP)
    guard = BudgetGuard(
        run_cap_usd=max_usd if model.metered else 0.0,
        daily_cap_usd=cap if model.metered else 0.0,
        ledger_path=data_dir() / "llm_ledger.json" if model.metered else None,
    )

    failure = None
    result = None
    config_paths = [CONFIG_DIR / "extraction.yaml", *ONTOLOGY_DIR.glob("vocab/*.yaml")]
    with stage_manifest("extract-llm", config_paths) as manifest:
        manifest["provider"], manifest["model"] = model.name, model.model
        try:
            result = run_extraction(
                model, guard, parts, out_dir or data_dir() / "extractions", config, limit
            )
            manifest["counts"] = result.counts
            manifest["rejected"] = result.rejected
            if result.stopped_at_cap:
                manifest["status"] = "stopped_at_cap"
        except ProviderError as exc:
            manifest["status"] = "api_error"
            manifest["error"] = type(exc).__name__
            failure = str(exc)
        finally:
            manifest["usd_spent"] = round(guard.spent_run_usd, 6)
    if result:
        typer.echo(f"{result.out_dir}\ncounts: {result.counts}\nrejected: {result.rejected}")
    typer.echo(f"Spent ${guard.spent_run_usd:.4f}.")
    if failure:
        typer.echo(f"Stopped: {failure}", err=True)
        raise typer.Exit(EXIT_API_ERROR)
    if result and result.stopped_at_cap:
        typer.echo(f"Stopped at cap: {result.stopped_at_cap}. Run again to resume.", err=True)
        raise typer.Exit(EXIT_STOPPED_AT_CAP)


@app.command()
def opportunities() -> None:
    """Opportunity scoring. Not built until M6."""
    from seismohydro_kg.analyze.opportunities import score_opportunities

    score_opportunities(_default_graph_dir(False), data_dir() / "opportunities.parquet")


@app.command()
def holdout() -> None:
    """Time-sliced evaluation. Not built until M6."""
    from seismohydro_kg.evaluate.holdout import run_holdout

    run_holdout(_default_graph_dir(False))


if __name__ == "__main__":
    app()
