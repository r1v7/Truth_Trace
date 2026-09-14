"""Split a raw statement into sentence-level claims with source offsets."""

import re
from dataclasses import dataclass

# Abbreviations that must not end a sentence.
_ABBREV = (
    r"(?<!\bMr\.)(?<!\bMrs\.)(?<!\bMs\.)(?<!\bDr\.)(?<!\bSt\.)"
    r"(?<!\bNo\.)(?<!\ba\.m\.)(?<!\bp\.m\.)"
)
_BOUNDARY = re.compile(rf"(?<=[.!?]){_ABBREV}[\"')\]]*\s+")


@dataclass(frozen=True)
class Segment:
    ordinal: int
    text: str
    start: int
    end: int


def segment(text: str) -> list[Segment]:
    """Return non-empty sentences, each carrying its offsets into `text`."""
    segments: list[Segment] = []
    cursor = 0
    ordinal = 0
    for match in _BOUNDARY.finditer(text):
        raw = text[cursor : match.end()]
        stripped = raw.strip()
        if stripped:
            start = cursor + (len(raw) - len(raw.lstrip()))
            segments.append(Segment(ordinal, stripped, start, start + len(stripped)))
            ordinal += 1
        cursor = match.end()

    tail = text[cursor:]
    stripped = tail.strip()
    if stripped:
        start = cursor + (len(tail) - len(tail.lstrip()))
        segments.append(Segment(ordinal, stripped, start, start + len(stripped)))
    return segments
