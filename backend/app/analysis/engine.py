"""Three-stage comparison engine.

1. Link  - pair claims from two interviews that talk about the same thing.
2. Extract - pull time / location / person / action / negation out of each claim.
3. Judge - decide match, possible_conflict, missing or unclear, with a readable reason.

Every result carries the source claims so the investigator reviews the actual words,
never the engine's verdict alone.
"""

from dataclasses import dataclass, field

from app.analysis import extract as ex
from app.analysis.similarity import get_backend
from app.core.config import settings
from app.models.enums import FindingField, FindingType

ENGINE_VERSION = "0.1.0"

# Two times count as agreeing if within this many minutes ("around eight" vs "8:10").
TIME_TOLERANCE_MINUTES = 20


@dataclass(frozen=True)
class Sides:
    """What to call each side in the explanations the investigator reads.

    A statement-to-statement run says "the first interview"; an evidence run says
    "the evidence". Naming the sides wrongly would misdescribe where a difference was
    found, which is the one thing a finding has to get right.
    """

    a: str = "the first interview"
    b: str = "the second interview"


DEFAULT_SIDES = Sides()


@dataclass
class ClaimInput:
    id: int
    text: str


@dataclass
class FindingResult:
    finding_type: FindingType
    field: FindingField
    score: float
    explanation: str
    claim_a_id: int | None = None
    claim_b_id: int | None = None
    details: dict = field(default_factory=dict)


def _times_agree(a: set[int], b: set[int]) -> bool:
    return any(abs(x - y) <= TIME_TOLERANCE_MINUTES for x in a for y in b)


# The action is the spine of a claim: two claims with the same verb are usually about
# the same event, and the detail that differs is the finding. Places and people are
# weaker evidence on their own - many events happen at the same place.
_ACTION_WEIGHT = 2
_DETAIL_WEIGHT = 1


def _attribute_overlap(a: ex.Attributes, b: ex.Attributes) -> float:
    """How much evidence there is that the two claims describe the *same event*.

    Wording similarity alone misses paraphrases ("the mall" vs "the shopping centre"),
    so shared places, people, actions and agreeing times act as a second, independent
    linking signal.
    """
    shared = 0
    total = 0
    for set_a, set_b, weight in (
        (a.actions, b.actions, _ACTION_WEIGHT),
        (a.locations, b.locations, _DETAIL_WEIGHT),
        (a.persons, b.persons, _DETAIL_WEIGHT),
    ):
        if set_a and set_b:
            total += weight
            if set_a & set_b:
                shared += weight
    # Agreeing times are evidence of the same event. Disagreeing times are deliberately
    # left out of the denominator: the very contradiction stage 3 exists to report must
    # not be what stops the pair from being linked in stage 1.
    if a.times and b.times and _times_agree(a.times, b.times):
        total += _DETAIL_WEIGHT
        shared += _DETAIL_WEIGHT
    return shared / total if total else 0.0


def _link(
    claims_a: list[ClaimInput], claims_b: list[ClaimInput]
) -> tuple[list[tuple[int, int, float]], set[int], set[int]]:
    """Greedy best-first pairing above the link threshold.

    A pair links on whichever signal is stronger: wording similarity from the active
    backend, or extracted-attribute overlap. Over-linking is the safer error here -
    a wrongly paired claim surfaces as a reviewable finding, a missed pair surfaces
    as nothing at all.
    """
    backend = get_backend()
    matrix = backend.similarity_matrix([c.text for c in claims_a], [c.text for c in claims_b])
    attrs_a = [ex.extract(c.text) for c in claims_a]
    attrs_b = [ex.extract(c.text) for c in claims_b]

    candidates = []
    for i, row in enumerate(matrix):
        for j, text_score in enumerate(row):
            score = max(text_score, _attribute_overlap(attrs_a[i], attrs_b[j]))
            if score >= settings.similarity_link_threshold:
                candidates.append((score, i, j))
    candidates.sort(reverse=True)

    used_a: set[int] = set()
    used_b: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for score, i, j in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        pairs.append((i, j, score))

    unmatched_a = set(range(len(claims_a))) - used_a
    unmatched_b = set(range(len(claims_b))) - used_b
    return pairs, unmatched_a, unmatched_b


def _judge(a: ClaimInput, b: ClaimInput, score: float, sides: Sides) -> FindingResult:
    attrs_a, attrs_b = ex.extract(a.text), ex.extract(b.text)
    details = {"a": attrs_a.as_dict(), "b": attrs_b.as_dict(), "link_score": round(score, 3)}

    def conflict(fld: FindingField, reason: str) -> FindingResult:
        return FindingResult(FindingType.possible_conflict, fld, score, reason, a.id, b.id, details)

    if attrs_a.negated != attrs_b.negated:
        affirmed, denied = (sides.a, sides.b) if attrs_b.negated else (sides.b, sides.a)
        return conflict(
            FindingField.negation,
            f"{affirmed.capitalize()} asserts this; {denied} denies it.",
        )

    if attrs_a.times and attrs_b.times and not _times_agree(attrs_a.times, attrs_b.times):
        times_a = ", ".join(ex.format_time(t) for t in sorted(attrs_a.times))
        times_b = ", ".join(ex.format_time(t) for t in sorted(attrs_b.times))
        return conflict(
            FindingField.time,
            f"Time differs: {times_a} in {sides.a} vs {times_b} in {sides.b} "
            f"(tolerance {TIME_TOLERANCE_MINUTES} min).",
        )

    if attrs_a.locations and attrs_b.locations and not (attrs_a.locations & attrs_b.locations):
        return conflict(
            FindingField.location,
            f"Location differs: {', '.join(sorted(attrs_a.locations))} vs "
            f"{', '.join(sorted(attrs_b.locations))}.",
        )

    if attrs_a.persons and attrs_b.persons and not (attrs_a.persons & attrs_b.persons):
        return conflict(
            FindingField.person,
            f"People named differ: {', '.join(sorted(attrs_a.persons))} vs "
            f"{', '.join(sorted(attrs_b.persons))}.",
        )

    if attrs_a.hedged or attrs_b.hedged:
        return FindingResult(
            FindingType.unclear,
            FindingField.other,
            score,
            "The statements agree, but at least one is hedged and may need clarification.",
            a.id,
            b.id,
            details,
        )

    return FindingResult(
        FindingType.match,
        FindingField.other,
        score,
        "Both statements describe the same thing with no differing detail found.",
        a.id,
        b.id,
        details,
    )


def compare(
    claims_a: list[ClaimInput],
    claims_b: list[ClaimInput],
    sides: Sides = DEFAULT_SIDES,
) -> list[FindingResult]:
    pairs, unmatched_a, unmatched_b = _link(claims_a, claims_b)

    results = [_judge(claims_a[i], claims_b[j], score, sides) for i, j, score in pairs]

    for i in sorted(unmatched_a):
        results.append(
            FindingResult(
                FindingType.missing,
                FindingField.other,
                0.0,
                f"Mentioned in {sides.a} but not found in {sides.b}.",
                claim_a_id=claims_a[i].id,
                details={"a": ex.extract(claims_a[i].text).as_dict()},
            )
        )
    for j in sorted(unmatched_b):
        results.append(
            FindingResult(
                FindingType.missing,
                FindingField.other,
                0.0,
                f"Mentioned in {sides.b} but not found in {sides.a}.",
                claim_b_id=claims_b[j].id,
                details={"b": ex.extract(claims_b[j].text).as_dict()},
            )
        )

    priority = {
        FindingType.possible_conflict: 0,
        FindingType.unclear: 1,
        FindingType.missing: 2,
        FindingType.match: 3,
    }
    results.sort(key=lambda r: (priority[r.finding_type], -r.score))
    return results
