"""Gold annotations store offsets rather than text, so the set can be published.

An annotator's view of the text is rebuilt locally from the OpenAlex abstract index.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldSpan:
    work_id: str
    char_start: int
    char_end: int
    concept_id: str
    annotator: str


def rehydrate(span: GoldSpan, abstract: str) -> str:
    """Return the annotated text. For local use only: do not store the result in a public table."""
    if not 0 <= span.char_start < span.char_end <= len(abstract):
        raise ValueError(
            f"{span.work_id}: offsets {span.char_start}-{span.char_end} do not fit an abstract of "
            f"{len(abstract)} characters. The upstream abstract may have changed."
        )
    return abstract[span.char_start : span.char_end]
