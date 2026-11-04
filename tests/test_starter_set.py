"""The starter set is metadata only, with exactly 100 unique papers across the planned strata."""

import csv
from collections import Counter

from seismohydro_kg.config import REPO_ROOT
from seismohydro_kg.graph.validate import FORBIDDEN_COLUMNS


def rows():
    with open(REPO_ROOT / "docs" / "starter-set-100.csv", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_one_hundred_unique_papers_with_dois():
    found = rows()
    assert len(found) == 100
    assert len({row["doi"].lower() for row in found}) == 100
    assert all(row["doi"].startswith("10.") for row in found)


def test_strata_quotas():
    assert Counter(row["stratum"] for row in rows()) == {
        "seismohydrology": 50,
        "seismology": 20,
        "hydrology": 20,
        "application": 10,
    }


def test_no_abstract_columns_or_long_text():
    found = rows()
    assert not FORBIDDEN_COLUMNS & {name.lower() for name in found[0]}
    assert all(len(row["title"].split()) <= 60 for row in found)
