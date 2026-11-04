"""Validate the vocabularies and mechanism registry against the LinkML schema."""

from __future__ import annotations

import csv
from pathlib import Path

from linkml.validator import validate

from seismohydro_kg.config import ONTOLOGY_DIR, load_yaml

SCHEMA_PATH = ONTOLOGY_DIR / "schema" / "seismohydro.linkml.yaml"
REQUIRED_MAPPING_COLUMNS = ("subject_id", "predicate_id", "object_id", "mapping_justification")


def _schema_errors(instance_path: Path, target_class: str) -> list[str]:
    report = validate(load_yaml(instance_path), str(SCHEMA_PATH), target_class)
    return [f"{instance_path.name}: {result.message}" for result in report.results]


def concept_ids(vocab_dir: Path) -> set[str]:
    return {
        concept["id"]
        for path in vocab_dir.glob("*.yaml")
        for concept in load_yaml(path).get("concepts") or []
    }


def validate_ontology(root: Path = ONTOLOGY_DIR) -> list[str]:
    """Return violations across schema conformance and cross-file references."""
    errors: list[str] = []
    vocab_dir = root / "vocab"
    for path in sorted(vocab_dir.glob("*.yaml")):
        errors.extend(_schema_errors(path, "Vocabulary"))
    registry_path = root / "coupling" / "mechanisms.yaml"
    errors.extend(_schema_errors(registry_path, "MechanismRegistry"))
    if errors:
        return errors

    known = concept_ids(vocab_dir)
    seen: set[str] = set()
    for path in sorted(vocab_dir.glob("*.yaml")):
        for concept in load_yaml(path)["concepts"]:
            if concept["id"] in seen:
                errors.append(f"{path.name}: duplicate concept id {concept['id']}")
            seen.add(concept["id"])
            references = [
                *concept.get("broader", []),
                *concept.get("proxy_for", []),
                *([concept["typical_approach"]] if concept.get("typical_approach") else []),
            ]
            for reference in references:
                if reference not in known:
                    errors.append(f"{concept['id']}: unknown concept {reference}")

    for mechanism in load_yaml(registry_path)["mechanisms"]:
        references = [
            *mechanism.get("forcing_variables", []),
            *mechanism.get("response_variables", []),
            *mechanism.get("compartments", []),
        ]
        for reference in references:
            if reference not in known:
                errors.append(f"{mechanism['id']}: unknown concept {reference}")

    errors.extend(_mapping_errors(root / "mappings" / "seed.sssom.tsv", known))
    return errors


def _mapping_errors(path: Path, known: set[str]) -> list[str]:
    errors: list[str] = []
    with open(path, encoding="utf-8") as handle:
        rows = csv.DictReader((line for line in handle if not line.startswith("#")), delimiter="\t")
        absent = [name for name in REQUIRED_MAPPING_COLUMNS if name not in (rows.fieldnames or [])]
        if absent:
            return [f"{path.name}: missing columns {absent}"]
        for row in rows:
            if row["subject_id"] not in known:
                errors.append(f"{path.name}: unknown subject {row['subject_id']}")
            local_object = row["object_id"].split(":")[0] in ("seis", "hydro", "shared")
            if local_object and row["object_id"] not in known:
                errors.append(f"{path.name}: unknown object {row['object_id']}")
    return errors
