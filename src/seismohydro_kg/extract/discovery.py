"""Open extraction before the schema is frozen, to find what seeds miss. Planned for M3.

Sampling and model come from config/extraction.yaml. See docs/adr/0006-discovery-before-schema.md.
"""

from __future__ import annotations

from pathlib import Path


def run_discovery(graph_dir: Path, out_path: Path, max_usd: float) -> None:
    raise NotImplementedError("Milestone M3: open extraction on 4,000 stratified abstracts.")
