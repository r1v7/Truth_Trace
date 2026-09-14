from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.analysis.engine import ENGINE_VERSION, ClaimInput, Sides, compare
from app.analysis.segment import segment
from app.analysis.similarity import get_backend
from app.api.deps import CurrentUser, DbSession, audit, get_case_for_user
from app.api.routes.analysis import serialize_run
from app.models import AnalysisRun, Claim, Evidence, Finding, Interview, Statement
from app.models.enums import EvidenceKind, RunKind, RunStatus
from app.schemas.analysis import AnalysisRunDetail
from app.schemas.evidence import EvidenceOut, IntegrityOut
from app.services import storage

router = APIRouter(tags=["evidence"])


def _get_evidence(db, evidence_id: int, user, *, write: bool = False) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    get_case_for_user(db, evidence.case_id, user, write=write)
    return evidence


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(case_id: int, db: DbSession, user: CurrentUser):
    get_case_for_user(db, case_id, user)
    return (
        db.query(Evidence)
        .filter(Evidence.case_id == case_id)
        .order_by(Evidence.created_at.desc())
        .all()
    )


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    case_id: int,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    file: UploadFile = File(...),
    kind: EvidenceKind = Form(EvidenceKind.other),
    description: str | None = Form(None),
):
    """Store a file and record its SHA-256 digest at the moment of upload."""
    get_case_for_user(db, case_id, user, write=True)

    try:
        stored = storage.store(case_id, file.file, file.content_type or "")
    except storage.StorageError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    evidence = Evidence(
        case_id=case_id,
        kind=kind,
        original_filename=storage.safe_display_name(file.filename or "unnamed"),
        content_type=file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        storage_path=stored.storage_path,
        description=description,
        uploaded_by_id=user.id,
    )
    db.add(evidence)
    db.flush()
    audit(
        db, request, user, "evidence_uploaded", "evidence", evidence.id, case_id,
        payload={"sha256": stored.sha256, "size": stored.size_bytes, "kind": kind.value},
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/evidence/{evidence_id}/integrity", response_model=IntegrityOut)
def check_integrity(evidence_id: int, db: DbSession, user: CurrentUser, request: Request):
    """Recompute the digest and compare it with the one stored at upload."""
    evidence = _get_evidence(db, evidence_id, user)
    result, computed = storage.verify(evidence.storage_path, evidence.sha256)
    audit(
        db, request, user, "evidence_integrity_checked", "evidence", evidence.id,
        evidence.case_id, payload={"status": result.value},
    )
    db.commit()
    return IntegrityOut(
        evidence_id=evidence.id,
        status=result,
        recorded_sha256=evidence.sha256,
        computed_sha256=computed,
        checked_at=datetime.now(UTC),
    )


@router.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, db: DbSession, user: CurrentUser, request: Request):
    evidence = _get_evidence(db, evidence_id, user)
    result, _ = storage.verify(evidence.storage_path, evidence.sha256)
    if result.value == "missing_file":
        raise HTTPException(status.HTTP_410_GONE, "The stored file is no longer present")
    audit(
        db, request, user, "evidence_downloaded", "evidence", evidence.id, evidence.case_id,
        payload={"integrity": result.value},
    )
    db.commit()
    return FileResponse(
        evidence.storage_path,
        media_type=evidence.content_type,
        filename=evidence.original_filename,
        # Tell the caller whether what they are downloading still matches its digest.
        headers={"X-Evidence-Integrity": result.value, "X-Evidence-SHA256": evidence.sha256},
    )


@router.post("/evidence/{evidence_id}/check", response_model=AnalysisRunDetail, status_code=201)
def check_against_interview(
    evidence_id: int,
    interview_id: int,
    db: DbSession,
    user: CurrentUser,
    request: Request,
):
    """Compare a statement's claims against text evidence.

    The evidence is segmented into claims exactly like a statement, so the same engine
    and the same review flow apply. Only text-shaped evidence can be checked this way;
    images and audio are stored and hashed but not analysed.
    """
    evidence = _get_evidence(db, evidence_id, user, write=True)

    if evidence.content_type not in storage.TEXT_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"{evidence.content_type} cannot be compared against statements yet. "
            "Only text evidence is supported.",
        )

    integrity, _ = storage.verify(evidence.storage_path, evidence.sha256)
    if integrity.value != "verified":
        # Refusing here is deliberate: a result drawn from altered evidence would be
        # worse than no result, because it would look exactly like a sound one.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Evidence integrity check failed ({integrity.value}). Analysis refused.",
        )

    interview = db.get(Interview, interview_id)
    if interview is None or interview.case_id != evidence.case_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found in this case")

    claims = (
        db.query(Claim)
        .join(Statement, Statement.id == Claim.statement_id)
        .filter(Statement.interview_id == interview_id)
        .order_by(Statement.id, Claim.ordinal)
        .all()
    )
    if not claims:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The interview has no statements")

    evidence_segments = segment(storage.read_text(evidence.storage_path))
    if not evidence_segments:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The evidence file has no readable text")

    backend = get_backend()
    run = AnalysisRun(
        case_id=evidence.case_id,
        kind=RunKind.evidence,
        interview_a_id=interview_id,
        evidence_id=evidence.id,
        status=RunStatus.running,
        analyzer_backend=backend.name,
        analyzer_version=f"{ENGINE_VERSION}+{backend.version}",
        requested_by_id=user.id,
    )
    db.add(run)
    db.flush()

    # Evidence text has no Claim rows of its own, so findings carry its wording in
    # `details` and leave claim_b unset.
    results = compare(
        [ClaimInput(c.id, c.text) for c in claims],
        [ClaimInput(-(s.ordinal + 1), s.text) for s in evidence_segments],
        Sides(a="the statement", b="the evidence"),
    )
    by_ordinal = {-(s.ordinal + 1): s.text for s in evidence_segments}

    for r in results:
        details = dict(r.details)
        if r.claim_b_id is not None and r.claim_b_id < 0:
            details["evidence_text"] = by_ordinal[r.claim_b_id]
        db.add(
            Finding(
                run_id=run.id,
                claim_a_id=r.claim_a_id if (r.claim_a_id or 0) > 0 else None,
                claim_b_id=None,
                finding_type=r.finding_type,
                field=r.field,
                score=r.score,
                explanation=r.explanation,
                details=details,
            )
        )

    run.status = RunStatus.completed
    audit(
        db, request, user, "evidence_checked", "analysis_run", run.id, evidence.case_id,
        payload={"evidence_id": evidence.id, "findings": len(results)},
    )
    db.commit()
    db.refresh(run)

    return serialize_run(db, run)
