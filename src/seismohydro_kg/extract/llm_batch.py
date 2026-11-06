"""Claude's half-price bulk path through Message Batches. Planned for M4.

`shkg extract llm` (extract/llm.py) already runs any provider, one real-time call per work, for
sets of up to `realtime_work_limit`. This adds batching for the 55k-abstract run. It must reuse
`check_output` so that batch results pass the same checks. Local models do not need it.
"""

from __future__ import annotations

from collections.abc import Iterable


def submit_batch(work_ids: Iterable[str], model: str, max_usd: float) -> str:
    raise NotImplementedError("Milestone M4: LLM batch extraction with the gold-set check.")
