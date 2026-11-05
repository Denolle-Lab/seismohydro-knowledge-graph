"""Guards on the workflow files: public artifacts stay clean, and paid runs stay gated."""

import subprocess
import sys

import pytest
import yaml

from seismohydro_kg.config import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


def load(name):
    return yaml.safe_load((REPO_ROOT / ".github" / "workflows" / name).read_text("utf-8"))


def steps(workflow):
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_uploads_never_include_raw_data(path):
    for step in steps(yaml.safe_load(path.read_text("utf-8"))):
        if "upload-artifact" in step.get("uses", ""):
            uploaded = step["with"]["path"]
            assert "raw" not in uploaded
            assert "fulltext" not in uploaded
            assert "data/\n" not in uploaded and uploaded.strip() != "data"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_inputs_never_expand_inside_a_shell_command(path):
    for step in steps(yaml.safe_load(path.read_text("utf-8"))):
        assert "${{" not in step.get("run", "")


def test_extract_is_manual_and_requires_the_reviewed_environment():
    workflow = load("extract.yml")
    triggers = workflow.get(True, workflow.get("on"))  # YAML reads a bare `on` key as True.
    assert list(triggers) == ["workflow_dispatch"]
    assert workflow["jobs"]["extract"]["environment"] == "paid-runs"
    assert triggers["workflow_dispatch"]["inputs"]["max_usd"]["required"] is True


@pytest.mark.parametrize(("name", "job"), [("refresh.yml", "refresh"), ("rebuild.yml", "rebuild")])
def test_scheduled_runs_are_off_by_default(name, job):
    assert "vars.ENABLE_SCHEDULED_RUNS == 'true'" in load(name)["jobs"][job]["if"]


def test_bootstrap_dry_run_lists_every_milestone_and_changes_nothing():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bootstrap_github.py"), "--offline"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.count("milestone ") == 8
    assert "Would apply" in result.stdout
