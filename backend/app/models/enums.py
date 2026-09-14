import enum


class Role(str, enum.Enum):
    """Global role. Governs what a user may do across the system."""

    investigator = "investigator"
    supervisor = "supervisor"
    admin = "admin"


class CaseStatus(str, enum.Enum):
    open = "open"
    under_review = "under_review"
    closed = "closed"
    archived = "archived"


class CaseMemberRole(str, enum.Enum):
    """Per-case role. Governs access to one case's data."""

    owner = "owner"
    collaborator = "collaborator"
    reviewer = "reviewer"


class FindingType(str, enum.Enum):
    match = "match"
    possible_conflict = "possible_conflict"
    missing = "missing"
    unclear = "unclear"


class FindingField(str, enum.Enum):
    """Which extracted attribute the finding is about."""

    time = "time"
    location = "location"
    person = "person"
    action = "action"
    negation = "negation"
    other = "other"


class ReviewDecision(str, enum.Enum):
    accepted = "accepted"
    rejected = "rejected"
    needs_more_info = "needs_more_info"


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
