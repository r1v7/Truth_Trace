from fastapi import APIRouter, HTTPException, Request, status

from app.analysis.segment import segment
from app.api.deps import CurrentUser, DbSession, audit, get_case_for_user
from app.models import Claim, Interview, Statement
from app.schemas.case import (
    InterviewCreate,
    InterviewOut,
    StatementCreate,
    StatementOut,
)

router = APIRouter(tags=["interviews"])


def _get_interview(db, interview_id: int, user, *, write: bool = False) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    get_case_for_user(db, interview.case_id, user, write=write)
    return interview


@router.get("/cases/{case_id}/interviews", response_model=list[InterviewOut])
def list_interviews(case_id: int, db: DbSession, user: CurrentUser):
    get_case_for_user(db, case_id, user)
    return (
        db.query(Interview)
        .filter(Interview.case_id == case_id)
        .order_by(Interview.interviewed_on, Interview.id)
        .all()
    )


@router.post("/cases/{case_id}/interviews", response_model=InterviewOut, status_code=201)
def create_interview(
    case_id: int, data: InterviewCreate, db: DbSession, user: CurrentUser, request: Request
):
    get_case_for_user(db, case_id, user, write=True)
    interview = Interview(**data.model_dump(), case_id=case_id, conducted_by_id=user.id)
    db.add(interview)
    db.flush()
    audit(db, request, user, "interview_created", "interview", interview.id, case_id)
    db.commit()
    db.refresh(interview)
    return interview


@router.get("/interviews/{interview_id}/statements", response_model=list[StatementOut])
def list_statements(interview_id: int, db: DbSession, user: CurrentUser):
    interview = _get_interview(db, interview_id, user)
    return (
        db.query(Statement)
        .filter(Statement.interview_id == interview.id)
        .order_by(Statement.id)
        .all()
    )


@router.post("/interviews/{interview_id}/statements", response_model=StatementOut, status_code=201)
def create_statement(
    interview_id: int, data: StatementCreate, db: DbSession, user: CurrentUser, request: Request
):
    """Store the raw statement and derive its claims immediately.

    Claims keep offsets into the original body, so nothing the investigator sees is
    ever detached from the words the subject actually said.
    """
    interview = _get_interview(db, interview_id, user, write=True)
    statement = Statement(interview_id=interview.id, body=data.body, language=data.language)
    db.add(statement)
    db.flush()

    for seg in segment(data.body):
        db.add(
            Claim(
                statement_id=statement.id,
                ordinal=seg.ordinal,
                text=seg.text,
                start_offset=seg.start,
                end_offset=seg.end,
            )
        )
    audit(
        db, request, user, "statement_created", "statement", statement.id, interview.case_id,
        payload={"length": len(data.body)},
    )
    db.commit()
    db.refresh(statement)
    return statement
