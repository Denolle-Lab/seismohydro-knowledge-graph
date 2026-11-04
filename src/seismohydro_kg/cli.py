"""`shkg` command line. Each stage is idempotent and writes a manifest to data/manifests/."""

from __future__ import annotations

import os
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


def _load_env() -> None:
    """Read REPO_ROOT/.env into the environment without overriding values already set."""
    path = REPO_ROOT / ".env"
    if not path.exists():
        return
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


@graph_app.command("export")
def graph_export(
    format_: Annotated[str, typer.Option("--format", help="neo4j or graphml.")] = "graphml",
    path: Annotated[Path | None, typer.Option(help="Graph directory.")] = None,
    fixture: Annotated[bool, typer.Option(help="Export the fixture graph.")] = False,
) -> None:
    """Export for Neo4j or GraphML tools."""
    from seismohydro_kg.graph.export import export_graphml, export_neo4j

    graph_dir = path or _default_graph_dir(fixture)
    if format_ == "neo4j":
        written = export_neo4j(graph_dir, graph_dir / "export" / "neo4j")
    elif format_ == "graphml":
        written = [export_graphml(graph_dir, graph_dir / "export" / "graph.graphml")]
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
def extract_gazetteer() -> None:
    """Tier 1 extraction. Not built until M4."""
    from seismohydro_kg.extract.gazetteer import run_gazetteer

    run_gazetteer([], data_dir() / "assertions" / "gazetteer.jsonl")


@extract_app.command("llm")
def extract_llm(
    max_usd: Annotated[float, typer.Option(help="Required spending cap for this run.")],
) -> None:
    """Tier 3 extraction. Not built until M4."""
    from seismohydro_kg.extract.llm_batch import submit_batch

    submit_batch([], "see config/extraction.yaml", max_usd)


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
