import pytest

from seismohydro_kg.evaluate.gold import GoldSpan, rehydrate
from seismohydro_kg.openalex.abstracts import reconstruct_abstract


def test_rebuilds_word_order_with_repeats():
    index = {"water": [0, 3], "and": [1], "waves": [2]}
    assert reconstruct_abstract(index) == "water and waves water"


@pytest.mark.parametrize("index", [None, {}, {"word": []}])
def test_missing_abstract_is_none(index):
    assert reconstruct_abstract(index) is None


def test_round_trip_against_a_known_text():
    text = "the elastic wave equation is hyperbolic and the richards equation is parabolic"
    index: dict[str, list[int]] = {}
    for position, word in enumerate(text.split()):
        index.setdefault(word, []).append(position)
    assert reconstruct_abstract(index) == text


def test_gold_span_rehydrates_and_detects_changed_upstream_text():
    span = GoldSpan("W1", 6, 10, "seis:dv_v", "annotator-a")
    assert rehydrate(span, "using dv/v here") == "dv/v"
    with pytest.raises(ValueError, match="do not fit"):
        rehydrate(span, "short")
