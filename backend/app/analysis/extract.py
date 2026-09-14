"""Rule-based attribute extraction from an English claim.

Deliberately explicit rather than model-driven: an investigator has to be able to
read *why* the system flagged something, and rules are auditable. Times are
normalised to minutes-from-midnight so that "8 PM" and "20:00" compare equal.
"""

import re
from dataclasses import dataclass, field

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "midnight": 0, "noon": 12,
}

_NEGATIONS = {
    "not", "never", "no", "none", "nothing", "nobody", "nowhere",
    "didn't", "wasn't", "weren't", "wouldn't", "couldn't", "haven't",
    "hadn't", "hasn't", "isn't", "aren't", "don't", "doesn't", "cannot", "can't",
}

_HEDGES = {
    "maybe", "perhaps", "possibly", "probably", "approximately", "around",
    "about", "roughly", "think", "guess", "believe", "unsure", "sure",
    "remember", "somewhere", "someone", "something", "sometime",
}

_LOCATION_CUES = r"(?:at|in|to|from|near|inside|outside|behind|beside)"
_STOPWORDS = {
    "the", "a", "an", "my", "his", "her", "their", "our", "its", "that", "this",
    "then", "there", "here", "and", "but", "so", "because", "about", "around",
    "approximately", "night", "evening", "morning", "afternoon", "oclock",
}

# Canonical place aliases. Widen this list from real case data during evaluation.
_PLACE_ALIASES = {
    "mall": "mall",
    "shopping centre": "mall",
    "shopping center": "mall",
    "shopping mall": "mall",
    "flat": "home",
    "apartment": "home",
    "house": "home",
    "home": "home",
    "petrol station": "fuel_station",
    "gas station": "fuel_station",
    "car park": "parking",
    "parking lot": "parking",
}

_HOUR_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b|\b(\d{1,2}):(\d{2})\b",
    re.IGNORECASE,
)
_WORD_TIME_RE = re.compile(
    r"\b(?:(half|quarter)\s+(past|to)\s+)?"
    r"\b(" + "|".join(_NUMBER_WORDS) + r")\b"
    r"(?:\s*(?:o'?clock))?"
    r"(?:\s*(?:in\s+the\s+|at\s+)?(morning|afternoon|evening|night|a\.?m\.?|p\.?m\.?))?",
    re.IGNORECASE,
)
_PROPER_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")


@dataclass
class Attributes:
    times: set[int] = field(default_factory=set)          # minutes from midnight
    locations: set[str] = field(default_factory=set)
    persons: set[str] = field(default_factory=set)
    actions: set[str] = field(default_factory=set)
    negated: bool = False
    hedged: bool = False

    def as_dict(self) -> dict:
        return {
            "times": sorted(self.times),
            "locations": sorted(self.locations),
            "persons": sorted(self.persons),
            "actions": sorted(self.actions),
            "negated": self.negated,
            "hedged": self.hedged,
        }


def format_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _to_24h(hour: int, minute: int, meridiem: str | None) -> int | None:
    if meridiem:
        m = meridiem.lower().replace(".", "")
        if m.startswith("p") or m in {"evening", "night", "afternoon"}:
            if hour != 12:
                hour += 12
        elif (m.startswith("a") or m == "morning") and hour == 12:
            hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def extract_times(text: str) -> set[int]:
    times: set[int] = set()
    for m in _HOUR_RE.finditer(text):
        if m.group(4):  # bare HH:MM, already 24h
            hour, minute = int(m.group(4)), int(m.group(5))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                times.add(hour * 60 + minute)
            continue
        value = _to_24h(int(m.group(1)), int(m.group(2) or 0), m.group(3))
        if value is not None:
            times.add(value)

    for m in _WORD_TIME_RE.finditer(text):
        fraction, direction, word, meridiem = m.groups()
        hour = _NUMBER_WORDS[word.lower()]
        minute = 0
        if fraction:
            offset = 30 if fraction.lower() == "half" else 15
            if direction.lower() == "past":
                minute = offset
            else:
                minute = 60 - offset
                hour -= 1
        elif word.lower() in {"midnight", "noon"}:
            pass  # complete on its own
        elif not meridiem and not re.search(r"o'?clock", m.group(0), re.IGNORECASE):
            # A bare number word ("two people") is not a time.
            continue
        value = _to_24h(hour % 24, minute, meridiem)
        if value is not None:
            times.add(value)
    return times


def extract_locations(text: str) -> set[str]:
    locations: set[str] = set()
    lowered = text.lower()
    for alias, canonical in _PLACE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            locations.add(canonical)
    for m in re.finditer(rf"\b{_LOCATION_CUES}\s+(?:the\s+|my\s+|his\s+|her\s+)?([a-z]+)", lowered):
        word = m.group(1)
        if word in _STOPWORDS or word in _NUMBER_WORDS:
            continue
        locations.add(_PLACE_ALIASES.get(word, word))
    return locations


def extract_persons(text: str) -> set[str]:
    """Capitalised tokens that are not sentence-initial. Coarse, but transparent."""
    persons: set[str] = set()
    for m in _PROPER_RE.finditer(text):
        if m.start() == 0:
            continue
        token = m.group(1)
        if token.lower() in _STOPWORDS or token.lower() in _NUMBER_WORDS:
            continue
        persons.add(token.lower())
    return persons


def extract_actions(text: str) -> set[str]:
    """Crude verb stems. Enough to tell 'arrived' apart from 'left'."""
    actions: set[str] = set()
    for token in re.findall(r"\b[a-z]+\b", text.lower()):
        if token in _NEGATIONS or token in _STOPWORDS or token in _HEDGES:
            continue
        if token.endswith("ed") and len(token) > 4:
            actions.add(token[:-2].rstrip("d"))
        elif token.endswith("ing") and len(token) > 5:
            actions.add(token[:-3])
    return actions


def extract(text: str) -> Attributes:
    tokens = set(re.findall(r"\b[\w']+\b", text.lower()))
    return Attributes(
        times=extract_times(text),
        locations=extract_locations(text),
        persons=extract_persons(text),
        actions=extract_actions(text),
        negated=bool(tokens & _NEGATIONS),
        hedged=bool(tokens & _HEDGES),
    )
