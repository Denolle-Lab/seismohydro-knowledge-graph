"""Run manifests: what each stage read, produced and spent."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seismohydro_kg.config import REPO_ROOT, data_dir


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def config_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


@contextmanager
def stage_manifest(
    stage: str, config_paths: Iterable[Path] = (), out_dir: Path | None = None
) -> Iterator[dict[str, Any]]:
    """Record a stage run. Callers add to `counts` and set `usd_spent` on the yielded dict.

    The manifest is written even when the stage fails or stops at a budget cap, because a
    partial run still spent money.
    """
    started = datetime.now(UTC)
    manifest: dict[str, Any] = {
        "stage": stage,
        "started_at": started.isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "config_hash": config_hash(config_paths),
        "counts": {},
        "usd_spent": 0.0,
        "status": "running",
    }
    try:
        yield manifest
        if manifest["status"] == "running":
            manifest["status"] = "ok"
    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["error"] = type(exc).__name__
        raise
    finally:
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        target = out_dir or data_dir() / "manifests"
        target.mkdir(parents=True, exist_ok=True)
        name = f"{stage.replace(' ', '-')}-{started.strftime('%Y%m%dT%H%M%S%f')}.json"
        (target / name).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
