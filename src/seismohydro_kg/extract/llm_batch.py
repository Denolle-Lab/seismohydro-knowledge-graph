"""Tier 3: LLM extraction through Message Batches, with schema-constrained output. Planned for M4.

Model choice comes from config/extraction.yaml: Haiku 5.5, checked against the gold set in M4.
"""

from __future__ import annotations

from collections.abc import Iterable


def submit_batch(work_ids: Iterable[str], model: str, max_usd: float) -> str:
    raise NotImplementedError("Milestone M4: LLM batch extraction with the gold-set check.")
