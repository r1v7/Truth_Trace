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

# Phrases where "not" expresses uncertainty rather than denial of the claim itself.
_HEDGED_NEGATION_RE = re.compile(
    r"\b(?:am|are|is|was|were|'m)?\s*not\s+"
    r"(?:entirely\s+|totally\s+|completely\s+|really\s+|quite\s+)?"
    r"(?:sure|certain|positive|confident)\b",
    re.IGNORECASE,
)

_HEDGES = {
    "maybe", "perhaps", "possibly", "probably", "approximately", "around",
    "about", "roughly", "think", "guess", "believe", "unsure", "sure",
    "remember", "somewhere", "someone", "something", "sometime",
}

# Irregular past tenses, mapped to their stem. Without these the most common verbs in
# a statement ("I met", "I went", "I saw") carry no action signal at all.
_IRREGULAR_VERBS = {
    "met": "meet", "went": "go", "gone": "go", "got": "get", "saw": "see",
    "seen": "see", "left": "leave", "took": "take", "taken": "take",
    "drove": "drive", "driven": "drive", "came": "come", "ran": "run",
    "paid": "pay", "bought": "buy", "brought": "bring", "spoke": "speak",
    "spoken": "speak", "told": "tell", "gave": "give", "given": "give",
    "made": "make", "found": "find", "wrote": "write", "written": "write",
    "sent": "send", "heard": "hear", "held": "hold", "kept": "keep",
    "knew": "know", "said": "say", "sat": "sit", "stood": "stand",
    "slept": "sleep", "ate": "eat", "drank": "drink", "wore": "wear",
    "lost": "lose", "felt": "feel", "thought": "think", "caught": "catch",
}

# Verbs that mean the same thing in a statement. Without this, "I arrived at the mall"
# and "I reached the shopping centre" look like two different actions. Keep this list
# narrow: collapsing genuinely different verbs would hide real differences.
_ACTION_SYNONYMS = {
    "reach": "arrive",
    "arriv": "arrive",
    "phon": "call",
    "depart": "leave",
    "purchas": "buy",
    "spoke": "speak",
}

# Words that can open a sentence but are never a person's name.
_SENTENCE_STARTERS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "the", "then", "after", "before", "when", "while", "during", "later",
    "yesterday", "today", "tomorrow", "that", "this", "there", "he", "she",
    "they", "we", "it", "my", "his", "her", "our", "their", "at", "in", "on",
    "first", "next", "finally", "afterwards", "around", "about", "both",
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
# Minutes as people actually say them: "ten past eight", "twenty-five past six".
_MINUTE_WORDS = {
    "five": 5,
    "ten": 10,
    "quarter": 15,
    "twenty": 20,
    "twenty-five": 25,
    "twenty five": 25,
    "half": 30,
}

_WORD_TIME_RE = re.compile(
    r"\b(?:(half|quarter|twenty[- ]five|twenty|five|ten|\d{1,2})\s+(past|to)\s+)?"
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
        offset_text, direction, word, meridiem = m.groups()
        hour = _NUMBER_WORDS[word.lower()]
        minute = 0
        if offset_text:
            key = offset_text.lower()
            offset = _MINUTE_WORDS.get(key, int(key) if key.isdigit() else None)
            if offset is None or not 0 < offset < 60:
                continue
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
    """Capitalised tokens that are not ordinary words. Coarse, but transparent.

    A name that opens a sentence still names a person - "Faisal drove me" as much as
    "I met Faisal" - so the first word is filtered through a stop list rather than
    skipped outright.
    """
    persons: set[str] = set()
    for m in _PROPER_RE.finditer(text):
        lowered = m.group(1).lower()
        if lowered in _STOPWORDS or lowered in _NUMBER_WORDS:
            continue
        if lowered in _SENTENCE_STARTERS:
            continue
        persons.add(lowered)
    return persons


def extract_actions(text: str) -> set[str]:
    """Crude verb stems, with synonyms collapsed. Enough to tell 'arrived' from 'left'."""
    actions: set[str] = set()
    for token in re.findall(r"\b[a-z]+\b", text.lower()):
        if token in _NEGATIONS or token in _STOPWORDS or token in _HEDGES:
            continue
        if token in _IRREGULAR_VERBS:
            stem = _IRREGULAR_VERBS[token]
        elif token.endswith("ed") and len(token) > 4:
            stem = token[:-2].rstrip("d")
        elif token.endswith("ing") and len(token) > 5:
            stem = token[:-3]
        else:
            continue
        actions.add(_ACTION_SYNONYMS.get(stem, stem))
    return actions


def extract(text: str) -> Attributes:
    # "I am not sure" must not read as a denial of the claim, so uncertainty phrases are
    # removed before negation is looked for - while still counting as hedging.
    hedged_negation = bool(_HEDGED_NEGATION_RE.search(text))
    denial_tokens = set(re.findall(r"\b[\w']+\b", _HEDGED_NEGATION_RE.sub(" ", text).lower()))
    all_tokens = set(re.findall(r"\b[\w']+\b", text.lower()))
    return Attributes(
        times=extract_times(text),
        locations=extract_locations(text),
        persons=extract_persons(text),
        actions=extract_actions(text),
        negated=bool(denial_tokens & _NEGATIONS),
        hedged=bool(all_tokens & _HEDGES) or hedged_negation,
    )
