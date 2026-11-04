import shutil

import pytest
import yaml

from seismohydro_kg.config import ONTOLOGY_DIR, REPO_ROOT
from seismohydro_kg.ontology import validate_ontology


@pytest.fixture
def ontology_copy(tmp_path):
    root = tmp_path / "ontology"
    shutil.copytree(ONTOLOGY_DIR, root)
    return root


def edit(path, change):
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data))


def test_repository_ontology_is_valid():
    assert validate_ontology() == []


def test_mechanism_with_unknown_variable_fails(ontology_copy):
    def change(data):
        data["mechanisms"][0]["forcing_variables"] = ["shared:not_a_variable"]

    edit(ontology_copy / "coupling" / "mechanisms.yaml", change)
    assert any("unknown concept" in item for item in validate_ontology(ontology_copy))


def test_mechanism_with_bad_direction_fails_schema(ontology_copy):
    def change(data):
        data["mechanisms"][0]["direction"] = "sideways"

    edit(ontology_copy / "coupling" / "mechanisms.yaml", change)
    assert validate_ontology(ontology_copy)


def test_concept_without_status_fails_schema(ontology_copy):
    edit(ontology_copy / "vocab" / "shared.yaml", lambda data: data["concepts"][0].pop("status"))
    assert validate_ontology(ontology_copy)


def test_unknown_concept_type_fails_schema(ontology_copy):
    def change(data):
        data["concepts"][0]["concept_type"] = "Vibes"

    edit(ontology_copy / "vocab" / "shared.yaml", change)
    assert validate_ontology(ontology_copy)


@pytest.mark.parametrize(
    ("field", "value"),
    [("broader", ["shared:missing"]), ("proxy_for", ["shared:missing"])],
)
def test_concept_with_unknown_reference_fails(ontology_copy, field, value):
    def change(data):
        data["concepts"][0][field] = value

    edit(ontology_copy / "vocab" / "shared.yaml", change)
    assert validate_ontology(ontology_copy)


def test_every_node_type_has_a_seed_and_a_definition():
    schema = yaml.safe_load((ONTOLOGY_DIR / "schema" / "seismohydro.linkml.yaml").read_text())
    types = {name for name, spec in schema["classes"].items() if spec.get("is_a") == "Concept"}
    seeded = {
        concept["concept_type"]
        for path in (ONTOLOGY_DIR / "vocab").glob("*.yaml")
        for concept in yaml.safe_load(path.read_text())["concepts"]
    }
    assert seeded == types
    assert all(schema["classes"][name].get("description") for name in types)
    definitions = (REPO_ROOT / "docs" / "node-types.md").read_text()
    assert all(f"**{name}**" in definitions for name in types)


def test_research_approach_has_exactly_three_values():
    facets = yaml.safe_load((ONTOLOGY_DIR / "vocab" / "facets.yaml").read_text())
    values = {c["id"] for c in facets["concepts"] if c["concept_type"] == "ResearchApproach"}
    assert values == {"shared:data_driven", "shared:model_driven", "shared:hybrid"}


def test_duplicate_concept_id_fails(ontology_copy):
    def change(data):
        data["concepts"].append(dict(data["concepts"][0]))

    edit(ontology_copy / "vocab" / "shared.yaml", change)
    assert any("duplicate" in item for item in validate_ontology(ontology_copy))


def test_mapping_with_unknown_subject_fails(ontology_copy):
    path = ontology_copy / "mappings" / "seed.sssom.tsv"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("seis:missing\tx\tskos:exactMatch\tENVO:1\ty\tsemapv:ManualMappingCuration\n")
    assert any("unknown subject" in item for item in validate_ontology(ontology_copy))
