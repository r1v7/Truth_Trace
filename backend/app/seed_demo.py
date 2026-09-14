"""Seed a public demo: one case, two interviews, statements, and a completed run.

Run with `python -m app.seed_demo`. It is idempotent - if the demo case already
exists, nothing is written.

This exists because the demo deployment has an ephemeral disk: a restart wipes
uploaded evidence, and an empty case list makes a working system look broken. The
findings it produces are computed by the real engine at seed time, not fixtures.
"""

import logging

from sqlalchemy.orm import Session

from app.analysis.engine import ENGINE_VERSION, ClaimInput, compare
from app.analysis.segment import segment
from app.analysis.similarity import get_backend
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    AnalysisRun,
    Case,
    CaseMember,
    Claim,
    Finding,
    Interview,
    Statement,
    User,
)
from app.models.enums import CaseMemberRole, CaseStatus, Role, RunKind, RunStatus

log = logging.getLogger("truthtrace.seed")

DEMO_REFERENCE = "CASE-2026-0184"

# Written to exercise every finding type the engine can report: a time difference,
# a denial, a different person named, a hedged agreement, and a plain match.
SESSION_ONE = (
    "I left the depot at ten past eight in the evening. "
    "I never went into the east store room. "
    "I met Sara near the gate earlier that week. "
    "I think Dani was already outside. "
    "I called Priya straight after."
)

SESSION_TWO = (
    "I left the depot at half past nine in the evening. "
    "I went into the east store room to get a torch. "
    "I met Layla near the gate that week. "
    "Dani was outside when I got there. "
    "I phoned Priya immediately afterwards."
)

DEMO_USERS = [
    ("demo.investigator@truthtrace.com", "Rachel Okafor", Role.investigator, "DemoPass123!"),
    ("demo.supervisor@truthtrace.com", "Tomas Halvorsen", Role.supervisor, "DemoPass123!"),
]


def _user(db: Session, email: str, name: str, role: Role, password: str) -> User:
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        return existing
    user = User(
        email=email, full_name=name, password_hash=hash_password(password), role=role
    )
    db.add(user)
    db.flush()
    return user


def _interview(db: Session, case: Case, author: User, label: str, body: str) -> Interview:
    interview = Interview(
        case_id=case.id,
        subject_name="Marek Sowa",
        session_label=label,
        conducted_by_id=author.id,
    )
    db.add(interview)
    db.flush()

    statement = Statement(interview_id=interview.id, body=body)
    db.add(statement)
    db.flush()

    for seg in segment(body):
        db.add(
            Claim(
                statement_id=statement.id,
                ordinal=seg.ordinal,
                text=seg.text,
                start_offset=seg.start,
                end_offset=seg.end,
            )
        )
    db.flush()
    return interview


def _claims(db: Session, interview_id: int) -> list[Claim]:
    return (
        db.query(Claim)
        .join(Statement, Statement.id == Claim.statement_id)
        .filter(Statement.interview_id == interview_id)
        .order_by(Statement.id, Claim.ordinal)
        .all()
    )


def seed() -> bool:
    """Return True if the demo was created, False if it already existed."""
    with SessionLocal() as db:
        if db.query(Case).filter(Case.reference == DEMO_REFERENCE).one_or_none():
            return False

        users = [_user(db, *entry) for entry in DEMO_USERS]
        investigator, supervisor = users[0], users[1]

        case = Case(
            reference=DEMO_REFERENCE,
            title="Warehouse fire, Pier 9",
            description=(
                "Demonstration case. Suspected arson at the Pier 9 storage facility. "
                "Two sessions with the same subject, the second taken after the site "
                "report landed."
            ),
            status=CaseStatus.open,
            created_by_id=investigator.id,
        )
        db.add(case)
        db.flush()

        db.add(CaseMember(case_id=case.id, user_id=investigator.id, role=CaseMemberRole.owner))
        db.add(CaseMember(case_id=case.id, user_id=supervisor.id, role=CaseMemberRole.reviewer))

        first = _interview(db, case, investigator, "Session 1", SESSION_ONE)
        second = _interview(db, case, investigator, "Session 2", SESSION_TWO)

        backend = get_backend()
        run = AnalysisRun(
            case_id=case.id,
            kind=RunKind.interview_pair,
            interview_a_id=first.id,
            interview_b_id=second.id,
            status=RunStatus.running,
            analyzer_backend=backend.name,
            analyzer_version=f"{ENGINE_VERSION}+{backend.version}",
            requested_by_id=investigator.id,
        )
        db.add(run)
        db.flush()

        # Findings come from the real engine, so the demo shows what the system
        # actually produces rather than a hand-written illustration of it.
        results = compare(
            [ClaimInput(c.id, c.text) for c in _claims(db, first.id)],
            [ClaimInput(c.id, c.text) for c in _claims(db, second.id)],
        )
        for result in results:
            db.add(
                Finding(
                    run_id=run.id,
                    claim_a_id=result.claim_a_id,
                    claim_b_id=result.claim_b_id,
                    finding_type=result.finding_type,
                    field=result.field,
                    score=result.score,
                    explanation=result.explanation,
                    details=result.details,
                )
            )
        run.status = RunStatus.completed

        db.commit()
        log.warning("Demo case %s seeded with %d findings", DEMO_REFERENCE, len(results))
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("seeded" if seed() else "demo case already present")
