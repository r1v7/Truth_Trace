from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.analysis.engine import ENGINE_VERSION, ClaimInput, compare
from app.analysis.similarity import get_backend
from app.api.deps import CurrentUser, DbSession, audit, get_case_for_user
from app.models import AnalysisRun, Claim, Finding, FindingReview, Interview, Statement
from app.models.enums import RunStatus
from app.schemas.analysis import (
    AnalysisRunCreate,
    AnalysisRunDetail,
    AnalysisRunOut,
    ClaimRef,
    FindingOut,
    ReviewCreate,
    ReviewOut,
)

router = APIRouter(tags=["analysis"])


def _claims_for_interview(db: Session, interview_id: int) -> list[Claim]:
    return (
        db.query(Claim)
        .join(Statement, Statement.id == Claim.statement_id)
        .filter(Statement.interview_id == interview_id)
        .order_by(Statement.id, Claim.ordinal)
        .all()
    )


def _claim_ref(claim: Claim | None) -> ClaimRef | None:
    if claim is None:
        return None
    return ClaimRef(
        id=claim.id,
        text=claim.text,
        statement_id=claim.statement_id,
        start_offset=claim.start_offset,
        end_offset=claim.end_offset,
    )


def serialize_run(db: Session, run: AnalysisRun) -> AnalysisRunDetail:
    findings = db.query(Finding).filter(Finding.run_id == run.id).order_by(Finding.id).all()
    out: list[FindingOut] = []
    for f in findings:
        latest = (
            db.query(FindingReview)
            .filter(FindingReview.finding_id == f.id)
            .order_by(FindingReview.created_at.desc())
            .first()
        )
        out.append(
            FindingOut(
                id=f.id,
                finding_type=f.finding_type,
                field=f.field,
                score=f.score,
                explanation=f.explanation,
                details=f.details,
                claim_a=_claim_ref(db.get(Claim, f.claim_a_id) if f.claim_a_id else None),
                claim_b=_claim_ref(db.get(Claim, f.claim_b_id) if f.claim_b_id else None),
                latest_decision=latest.decision if latest else None,
            )
        )
    detail = AnalysisRunDetail.model_validate(run, from_attributes=True)
    detail.findings = out
    return detail


@router.post("/cases/{case_id}/analysis-runs", response_model=AnalysisRunDetail, status_code=201)
def create_run(
    case_id: int, data: AnalysisRunCreate, db: DbSession, user: CurrentUser, request: Request
):
    get_case_for_user(db, case_id, user, write=True)
    if data.interview_a_id == data.interview_b_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick two different interviews")

    interviews = {}
    for key, iid in (("a", data.interview_a_id), ("b", data.interview_b_id)):
        interview = db.get(Interview, iid)
        if interview is None or interview.case_id != case_id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Interview {iid} not found in this case"
            )
        interviews[key] = interview

    if interviews["a"].subject_name.strip().lower() != interviews["b"].subject_name.strip().lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Both interviews must be with the same subject to be comparable",
        )

    backend = get_backend()
    run = AnalysisRun(
        case_id=case_id,
        interview_a_id=data.interview_a_id,
        interview_b_id=data.interview_b_id,
        status=RunStatus.running,
        analyzer_backend=backend.name,
        analyzer_version=f"{ENGINE_VERSION}+{backend.version}",
        requested_by_id=user.id,
    )
    db.add(run)
    db.flush()

    claims_a = _claims_for_interview(db, data.interview_a_id)
    claims_b = _claims_for_interview(db, data.interview_b_id)
    if not claims_a or not claims_b:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Both interviews need at least one statement"
        )

    try:
        results = compare(
            [ClaimInput(c.id, c.text) for c in claims_a],
            [ClaimInput(c.id, c.text) for c in claims_b],
        )
    except Exception as exc:  # noqa: BLE001 - surface the failure on the run itself
        run.status = RunStatus.failed
        run.error = str(exc)[:500]
        db.commit()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Analysis failed") from exc

    for r in results:
        db.add(
            Finding(
                run_id=run.id,
                claim_a_id=r.claim_a_id,
                claim_b_id=r.claim_b_id,
                finding_type=r.finding_type,
                field=r.field,
                score=r.score,
                explanation=r.explanation,
                details=r.details,
            )
        )
    run.status = RunStatus.completed
    audit(
        db, request, user, "analysis_run", "analysis_run", run.id, case_id,
        payload={"backend": backend.name, "findings": len(results)},
    )
    db.commit()
    db.refresh(run)
    return serialize_run(db, run)


@router.get("/cases/{case_id}/analysis-runs", response_model=list[AnalysisRunOut])
def list_runs(case_id: int, db: DbSession, user: CurrentUser):
    get_case_for_user(db, case_id, user)
    return (
        db.query(AnalysisRun)
        .filter(AnalysisRun.case_id == case_id)
        .order_by(AnalysisRun.created_at.desc())
        .all()
    )


@router.get("/analysis-runs/{run_id}", response_model=AnalysisRunDetail)
def get_run(run_id: int, db: DbSession, user: CurrentUser):
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis run not found")
    get_case_for_user(db, run.case_id, user)
    return serialize_run(db, run)


@router.post("/findings/{finding_id}/reviews", response_model=ReviewOut, status_code=201)
def review_finding(
    finding_id: int, data: ReviewCreate, db: DbSession, user: CurrentUser, request: Request
):
    """Record a human judgement. Reviews are additive - history is never overwritten."""
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    run = db.get(AnalysisRun, finding.run_id)
    get_case_for_user(db, run.case_id, user)

    review = FindingReview(
        finding_id=finding.id,
        reviewer_id=user.id,
        decision=data.decision,
        comment=data.comment,
    )
    db.add(review)
    db.flush()
    audit(
        db, request, user, "finding_reviewed", "finding", finding.id, run.case_id,
        payload={"decision": data.decision.value},
    )
    db.commit()
    db.refresh(review)
    return review


@router.get("/findings/{finding_id}/reviews", response_model=list[ReviewOut])
def list_reviews(finding_id: int, db: DbSession, user: CurrentUser):
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Finding not found")
    run = db.get(AnalysisRun, finding.run_id)
    get_case_for_user(db, run.case_id, user)
    return (
        db.query(FindingReview)
        .filter(FindingReview.finding_id == finding_id)
        .order_by(FindingReview.created_at)
        .all()
    )
