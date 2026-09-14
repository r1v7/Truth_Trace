"""The scenarios from the project brief, encoded as regression tests."""

from app.analysis.engine import ClaimInput, compare
from app.models.enums import FindingField, FindingType


def _run(a: str, b: str):
    return compare([ClaimInput(1, a)], [ClaimInput(2, b)])


def _first(results):
    assert results, "engine returned no findings"
    return results[0]


def test_paraphrase_is_not_a_conflict():
    r = _first(_run(
        "I arrived at the mall at 8:00 PM.",
        "I reached the shopping centre at around eight in the evening.",
    ))
    assert r.finding_type in {FindingType.match, FindingType.unclear}


def test_different_time_is_flagged():
    r = _first(_run("I arrived at the mall at 8:00 PM.", "I arrived at the mall at 10:30 PM."))
    assert r.finding_type is FindingType.possible_conflict
    assert r.field is FindingField.time
    assert "20:00" in r.explanation and "22:30" in r.explanation


def test_small_time_difference_is_tolerated():
    r = _first(_run("I arrived at the mall at 8:00 PM.", "I arrived at the mall at 8:10 PM."))
    assert r.finding_type is not FindingType.possible_conflict


def test_negation_beats_wording_similarity():
    """'I was at home' and 'I was not at home' are near-identical text, opposite meaning."""
    r = _first(_run("I was at home that night.", "I was not at home that night."))
    assert r.finding_type is FindingType.possible_conflict
    assert r.field is FindingField.negation


def test_different_people_are_flagged():
    r = _first(_run("I met Sara near the entrance.", "I met Layla near the entrance."))
    assert r.finding_type is FindingType.possible_conflict
    assert r.field is FindingField.person


def test_unmatched_claims_are_reported_missing_on_both_sides():
    results = compare(
        [ClaimInput(1, "I bought a blue jacket from the shop.")],
        [ClaimInput(2, "The weather was cold and rainy all day.")],
    )
    assert {r.finding_type for r in results} == {FindingType.missing}
    assert {(r.claim_a_id, r.claim_b_id) for r in results} == {(1, None), (None, 2)}


def test_conflicts_are_ordered_before_matches():
    results = compare(
        [ClaimInput(1, "I arrived at 8:00 PM."), ClaimInput(2, "I met Sara near the entrance.")],
        [ClaimInput(3, "I arrived at 10:30 PM."), ClaimInput(4, "I met Sara near the entrance.")],
    )
    assert results[0].finding_type is FindingType.possible_conflict


def test_empty_side_yields_only_missing():
    results = compare([ClaimInput(1, "I was there.")], [])
    assert len(results) == 1 and results[0].finding_type is FindingType.missing
