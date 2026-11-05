"""Tier 1: match vocabulary terms in titles and reconstructed abstracts. No LLM, no cost.

Each work gets one `mentions` edge per concept, with the offsets of the first match in `work_text`.
Confidence 1.0 means an exact string match. The sense of the word is not checked, so "discharge"
in an electrical paper would match: that is what the LLM tier and the gold set are for.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from seismohydro_kg.config import ONTOLOGY_DIR, load_yaml
from seismohydro_kg.extract.text import iter_works, work_text

MIN_TERM_CHARS = 2
# A study's approach is judged from its main result, so the word alone does not establish it.
SKIP_CONCEPT_TYPES = {"ResearchApproach"}
_SEPARATOR = r"[\s\-]+"


def load_concepts(root: Path = ONTOLOGY_DIR) -> list[dict]:
    """Every vocabulary concept, in a stable order so that prompts cache and hashes repeat."""
    concepts = [
        concept
        for path in sorted((root / "vocab").glob("*.yaml"))
        for concept in load_yaml(path)["concepts"]
    ]
    return sorted(concepts, key=lambda concept: concept["id"])


def _is_case_sensitive(term: str) -> bool:
    """Short terms with capitals are symbols or acronyms: Vs, DAS, GRACE."""
    return len(term) <= 6 and any(char.isupper() for char in term)


def _pattern(term: str) -> str:
    words = re.split(_SEPARATOR, term.strip())
    if _is_case_sensitive(term):
        return _SEPARATOR.join(re.escape(word) for word in words)
    last = words[-1]
    if last.endswith("y") and len(last) > 3:
        last = re.escape(last[:-1]) + "(?:y|ies)"
    elif last[-1].isalpha():
        last = re.escape(last) + "(?:s|es)?"
    else:
        last = re.escape(last)
    return "(?i:" + _SEPARATOR.join([*(re.escape(word) for word in words[:-1]), last]) + ")"


@dataclass(frozen=True)
class Gazetteer:
    pattern: re.Pattern[str]
    group_to_concept: dict[str, str]
    ambiguous_terms: tuple[str, ...]
    version: str

    def match(self, text: str) -> dict[str, tuple[int, int]]:
        """Concept ID to the offsets of its first match. Longer terms win over shorter ones."""
        found: dict[str, tuple[int, int]] = {}
        for match in self.pattern.finditer(text):
            found.setdefault(self.group_to_concept[match.lastgroup], match.span())
        return found


def build_gazetteer(concepts: Iterable[dict]) -> Gazetteer:
    """Compile the vocabulary. A term claimed by two concepts is left out, for the LLM tier."""
    claims: dict[str, set[str]] = {}
    spelling: dict[str, str] = {}
    for concept in concepts:
        if concept["concept_type"] in SKIP_CONCEPT_TYPES:
            continue
        for term in (concept["label"], *concept.get("synonyms", [])):
            if len(term.strip()) < MIN_TERM_CHARS:
                continue
            key = term.strip().casefold()
            claims.setdefault(key, set()).add(concept["id"])
            spelling.setdefault(key, term.strip())
    ambiguous = tuple(sorted(key for key, owners in claims.items() if len(owners) > 1))
    terms = sorted(
        ((spelling[key], next(iter(owners))) for key, owners in claims.items() if len(owners) == 1),
        key=lambda item: (-len(item[0]), item[0]),
    )
    groups = {f"t{index}": concept_id for index, (_term, concept_id) in enumerate(terms)}
    body = "|".join(f"(?P<t{index}>{_pattern(term)})" for index, (term, _) in enumerate(terms))
    digest = hashlib.sha256(json.dumps(terms).encode()).hexdigest()[:8]
    return Gazetteer(
        re.compile(rf"(?<![\w])(?:{body})(?![\w])"), groups, ambiguous, f"gazetteer-{digest}"
    )


def run_gazetteer(raw_paths: Iterable[Path], out_path: Path) -> dict[str, int]:
    """Write `mentions` assertions as JSON Lines. They hold offsets only, never text."""
    gazetteer = build_gazetteer(load_concepts())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"works": 0, "works_with_match": 0, "edges": 0}
    with open(out_path, "w", encoding="utf-8") as handle:
        for work_id, record in iter_works(raw_paths):
            counts["works"] += 1
            matches = gazetteer.match(work_text(record) or "")
            counts["works_with_match"] += bool(matches)
            for concept_id, (start, end) in sorted(matches.items()):
                edge = {
                    "source": work_id,
                    "target": concept_id,
                    "edge_type": "mentions",
                    "layer": "L2",
                    "work_id": work_id,
                    "char_start": start,
                    "char_end": end,
                    "extractor_version": gazetteer.version,
                    "confidence": 1.0,
                    "tier": "gazetteer",
                }
                handle.write(json.dumps(edge) + "\n")
                counts["edges"] += 1
    counts["ambiguous_terms_skipped"] = len(gazetteer.ambiguous_terms)
    return counts
