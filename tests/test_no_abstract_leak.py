"""The no-abstract rule must fail on contaminated tables, however the text got there."""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from seismohydro_kg.config import FIXTURE_DIR
from seismohydro_kg.graph.build import build_graph
from seismohydro_kg.graph.validate import check_no_abstract_text, validate_graph

ABSTRACT = (
    "we measure relative seismic velocity changes at a single station and compare them with "
    "groundwater levels recorded in a nearby monitoring well over several years of data"
)


def write(tmp_path, **columns):
    pq.write_table(pa.table(columns), tmp_path / "table.parquet")


@pytest.mark.parametrize("column", ["abstract", "ABSTRACT_TEXT", "evidence_text", "snippet"])
def test_forbidden_column_fails(tmp_path, column):
    write(tmp_path, **{column: ["short"]})
    assert any("forbidden column" in item for item in check_no_abstract_text(tmp_path))


def test_long_free_text_in_an_innocent_column_fails(tmp_path):
    write(tmp_path, note=[" ".join(["word"] * 41)])
    assert any("longer than 40 words" in item for item in check_no_abstract_text(tmp_path))


def test_exact_abstract_words_fail_when_abstracts_are_supplied(tmp_path):
    fragment = " ".join(ABSTRACT.split()[:14])
    write(tmp_path, note=[fragment])
    assert check_no_abstract_text(tmp_path) == []
    found = check_no_abstract_text(tmp_path, abstracts=[ABSTRACT])
    assert any("contains abstract text" in item for item in found)


def test_title_repeating_the_abstract_opening_is_allowed(tmp_path):
    write(tmp_path, label=[" ".join(ABSTRACT.split()[:14])])
    assert check_no_abstract_text(tmp_path, abstracts=[ABSTRACT]) == []


def test_clean_fixture_graph_passes(tmp_path):
    build_graph(
        {"fixture": [FIXTURE_DIR / "works_synthetic.jsonl"]},
        [FIXTURE_DIR / "assertions_synthetic.jsonl"],
        tmp_path,
    )
    assert check_no_abstract_text(tmp_path) == []


def test_validate_graph_fails_on_a_contaminated_release_table(tmp_path):
    build_graph(
        {"fixture": [FIXTURE_DIR / "works_synthetic.jsonl"]},
        [FIXTURE_DIR / "assertions_synthetic.jsonl"],
        tmp_path,
    )
    pq.write_table(pa.table({"abstract": [ABSTRACT]}), tmp_path / "extra.parquet")
    assert any("forbidden column" in item for item in validate_graph(tmp_path))
