"""Time-sliced holdout against the preferential-attachment baseline. Planned for M6."""

from __future__ import annotations

from pathlib import Path


def run_holdout(graph_dir: Path, cutoffs: tuple[int, ...] = (2010, 2015, 2020)) -> None:
    raise NotImplementedError("Milestone M6: holdout at each cutoff, tested on the next 5 years.")
