#!/usr/bin/env python3
"""Create GitHub labels, milestones and issues from roadmap/milestones.yaml.

Prints what it would do unless given --apply. Safe to rerun: existing titles are skipped.
Requires the gh CLI, authenticated with write access to the repository.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "Denolle-Lab/seismohydro-knowledge-graph"


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def existing_titles(repo: str) -> tuple[set[str], set[str], set[str]]:
    labels = {
        item["name"]
        for item in json.loads(gh("label", "list", "-R", repo, "--limit", "200", "--json", "name"))
    }
    milestones = {
        item["title"]
        for item in json.loads(gh("api", "--paginate", f"repos/{repo}/milestones?state=all"))
    }
    issues = {
        item["title"]
        for item in json.loads(
            gh("issue", "list", "-R", repo, "--state", "all", "--limit", "500", "--json", "title")
        )
    }
    return labels, milestones, issues


def plan(roadmap: dict, labels: set[str], milestones: set[str], issues: set[str]) -> list[dict]:
    """The actions still needed, as plain data, so that dry runs and tests share this code."""
    actions: list[dict] = []
    for label in roadmap["labels"]:
        if label["name"] not in labels:
            actions.append({"kind": "label", **label})
    for milestone in roadmap["milestones"]:
        if milestone["title"] not in milestones:
            actions.append(
                {
                    "kind": "milestone",
                    "title": milestone["title"],
                    "description": milestone["description"],
                }
            )
        for issue in milestone["issues"]:
            if issue["title"] not in issues:
                actions.append({"kind": "issue", "milestone": milestone["title"], **issue})
    return actions


def apply_action(action: dict, repo: str) -> None:
    if action["kind"] == "label":
        gh(
            "label", "create", action["name"], "-R", repo,
            "--color", action["color"], "--description", action["description"],
        )  # fmt: skip
    elif action["kind"] == "milestone":
        gh(
            "api", f"repos/{repo}/milestones", "--method", "POST",
            "-f", f"title={action['title']}", "-f", f"description={action['description']}",
        )  # fmt: skip
    else:
        command = [
            "issue", "create", "-R", repo, "--title", action["title"],
            "--body", action["body"], "--milestone", action["milestone"],
        ]  # fmt: skip
        for label in action.get("labels", []):
            command += ["--label", label]
        gh(*command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--apply", action="store_true", help="Create them. Default: only print.")
    parser.add_argument(
        "--offline", action="store_true", help="Assume an empty repo, without calling gh."
    )
    args = parser.parse_args()

    roadmap = yaml.safe_load((REPO_ROOT / "roadmap" / "milestones.yaml").read_text("utf-8"))
    current = (set(), set(), set()) if args.offline else existing_titles(args.repo)
    actions = plan(roadmap, *current)
    for action in actions:
        name = action.get("title") or action.get("name")
        print(f"{action['kind']:10s}{name}")
        if args.apply:
            apply_action(action, args.repo)
    verb = "Applied" if args.apply else "Would apply"
    print(f"{verb} {len(actions)} actions on {args.repo}.")


if __name__ == "__main__":
    main()
