from app.analysis.segment import segment


def test_offsets_point_back_into_the_source():
    text = "I arrived at 8 PM. Then I left."
    segs = segment(text)
    assert [s.text for s in segs] == ["I arrived at 8 PM.", "Then I left."]
    for s in segs:
        assert text[s.start : s.end] == s.text


def test_abbreviation_does_not_split():
    assert len(segment("Mr. Khan was waiting outside.")) == 1


def test_trailing_fragment_is_kept():
    assert [s.text for s in segment("First one. No full stop here")][-1] == "No full stop here"
