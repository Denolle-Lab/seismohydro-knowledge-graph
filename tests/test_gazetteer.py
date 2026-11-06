"""Vocabulary matching: the free tier a first graph rests on. All text here is synthetic."""

from seismohydro_kg.extract.gazetteer import build_gazetteer, load_concepts
from seismohydro_kg.extract.text import work_text


def concept(id_, label, *synonyms, type_="Method"):
    return {"id": id_, "concept_type": type_, "label": label, "synonyms": list(synonyms)}


def match(text, *concepts):
    return build_gazetteer(concepts).match(text)


def test_offsets_point_at_the_match():
    text = "We apply coda wave interferometry here."
    found = match(text, concept("a", "coda wave interferometry"))
    start, end = found["a"]
    assert text[start:end] == "coda wave interferometry"


def test_plurals_case_and_hyphens_match():
    gazetteer = build_gazetteer(
        [
            concept("a", "earthquake"),
            concept("b", "permeability"),
            concept("c", "cross correlation"),
        ]
    )
    found = gazetteer.match("Earthquakes and permeabilities from cross-correlations.")
    assert set(found) == {"a", "b", "c"}


def test_symbols_are_case_sensitive_and_need_word_boundaries():
    symbol = concept("a", "shear velocity", "Vs")
    assert match("the Vs profile", symbol)
    assert not match("england vs france", symbol)
    assert not match("the Vsomething", symbol)


def test_longer_term_wins_over_the_shorter_one_inside_it():
    found = match(
        "seismic interferometry", concept("a", "seismic interferometry"), concept("b", "seismic")
    )
    assert set(found) == {"a"}


def test_term_claimed_by_two_concepts_is_left_for_the_llm():
    gazetteer = build_gazetteer(
        [concept("a", "alpha", "inversion"), concept("b", "b", "inversion")]
    )
    assert gazetteer.ambiguous_terms == ("inversion",)
    assert not gazetteer.match("an inversion")


def test_one_letter_terms_and_research_approaches_are_skipped():
    gazetteer = build_gazetteer(
        [
            concept("a", "attenuation", "Q"),
            concept("b", "data-driven", type_="ResearchApproach"),
        ]
    )
    assert set(gazetteer.match("Q and data-driven attenuation")) == {"a"}


def test_real_vocabulary_compiles():
    assert build_gazetteer(load_concepts()).group_to_concept


def test_work_text_is_title_then_abstract():
    record = {"title": "A title", "abstract_inverted_index": {"Some": [0], "words": [1]}}
    assert work_text(record) == "A title\n\nSome words"
    assert work_text({"title": "Only", "abstract_inverted_index": None}) == "Only"
    assert work_text({"title": None, "abstract_inverted_index": None}) is None
