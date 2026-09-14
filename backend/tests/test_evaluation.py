"""Regression floor for the engine, measured on the labelled evaluation set.

These thresholds are a ratchet, not a target. If a change drops the engine below them,
the change is wrong until proven otherwise. Raising a floor is only honest after adding
*new* labelled examples - tightening it against the same 42 items measures nothing.
"""

from evaluation.run_eval import evaluate, load_items, per_label

# Deliberately below the current score: the set is small, and a floor that sits exactly
# on today's number turns every future example into a failing test.
MIN_ACCURACY = 0.90
MIN_CONFLICT_RECALL = 0.95
MIN_CONFLICT_PRECISION = 0.85


def test_engine_meets_its_regression_floor():
    result = evaluate(load_items())
    scores = per_label(result["confusion"])["possible_conflict"]

    assert result["accuracy"] >= MIN_ACCURACY, (
        f"accuracy {result['accuracy']:.1%} is below the floor; "
        f"wrong: {[e['id'] for e in result['errors']]}"
    )
    # Missing a real contradiction is the failure that matters most: the investigator
    # never learns it existed.
    assert scores["recall"] >= MIN_CONFLICT_RECALL
    # And a flood of false alarms makes the tool not worth opening.
    assert scores["precision"] >= MIN_CONFLICT_PRECISION


def test_link_threshold_is_not_on_a_knife_edge():
    """The configured threshold should not be the single value that happens to work."""
    from app.core.config import settings

    original = settings.similarity_link_threshold
    try:
        for threshold in (0.45, 0.50, 0.55, 0.60):
            settings.similarity_link_threshold = threshold
            result = evaluate(load_items())
            assert result["accuracy"] >= MIN_ACCURACY, f"fragile at threshold {threshold}"
    finally:
        settings.similarity_link_threshold = original
