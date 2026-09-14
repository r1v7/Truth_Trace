import pytest

from app.analysis import extract as ex


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I arrived at 8:00 PM.", 20 * 60),
        ("I arrived at 8 PM.", 20 * 60),
        ("I arrived at 20:00.", 20 * 60),
        ("I got there at eight in the evening.", 20 * 60),
        ("It was half past eight in the evening.", 20 * 60 + 30),
        ("I left at ten past eight in the evening.", 20 * 60 + 10),
        ("I left at twenty-five past six in the morning.", 6 * 60 + 25),
        ("I left at five to ten in the evening.", 21 * 60 + 55),
        ("I left at quarter to nine in the evening.", 20 * 60 + 45),
        ("I was home at midnight.", 0),
    ],
)
def test_time_normalisation(text, expected):
    assert expected in ex.extract_times(text)


def test_bare_number_word_is_not_a_time():
    assert ex.extract_times("There were three people with me.") == set()


def test_a_count_before_past_is_not_a_time():
    """'ten people past the gate' counts people, it does not tell the time."""
    assert ex.extract_times("There were ten people past the gate.") == set()


def test_place_aliases_collapse():
    assert ex.extract_locations("I went to the mall.") & ex.extract_locations(
        "I went to the shopping centre."
    )


def test_negation_and_hedging_are_flagged():
    assert ex.extract("I did not go there.").negated
    assert ex.extract("I think it was around eight.").hedged
    assert not ex.extract("I went there at 8:00 PM.").negated


def test_sentence_initial_capital_is_not_a_person():
    assert "monday" not in ex.extract_persons("Monday was the day I met Sara.")
    assert "sara" in ex.extract_persons("Monday was the day I met Sara.")
