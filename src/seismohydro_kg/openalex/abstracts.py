"""Rebuild plaintext abstracts from OpenAlex inverted indexes.

OpenAlex does not ship plaintext abstracts, for legal reasons. Reconstructed text is for local
processing only and must never reach a public table. See docs/adr/0005-abstract-handling.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def reconstruct_abstract(index: Mapping[str, Sequence[int]] | None) -> str | None:
    """Return the abstract text, or None when the work has no abstract."""
    if not index:
        return None
    positions = {pos: word for word, places in index.items() for pos in places}
    if not positions:
        return None
    return " ".join(positions[pos] for pos in sorted(positions))
