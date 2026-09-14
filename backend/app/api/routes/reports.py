from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, audit, get_case_for_user
from app.models import AnalysisRun, Case, Finding, User
from app.models.enums import ReportStatus, Role
from app.models.report import Report, ReportItem
from app.schemas.report import (
    ReportCreate,
    ReportDetail,
    ReportOut,
    ReportUpdate,
    SupervisorDecision,
)
from app.services import reporting

router = APIRouter(tags=["reports"])

EDITABLE = {ReportStatus.draft, ReportStatus.returned}


def _article(word: str) -> str:
    return f"An {word}" if word[0] in "aeiou" else f"A {word}"


def _get_report(db: Session, report_id: int, user, *, write: bool = False) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    get_case_for_user(db, report.case_id, user, write=write)
    return report


def _set_items(db: Session, report: Report, items) -> None:
    """Replace the report's items, checking every finding belongs to this case."""
    db.query(ReportItem).filter(ReportItem.report_id == report.id).delete()
    for position, entry in enumerate(items):
        finding = db.get(Finding, entry.finding_id)
        if finding is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"Finding {entry.finding_id} not found"
            )
        run = db.get(AnalysisRun, finding.run_id)
        if run is None or run.case_id != report.case_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Finding {entry.finding_id} belongs to a different case",
            )
        db.add(
            ReportItem(
                report_id=report.id,
                finding_id=entry.finding_id,
                position=position,
                note=entry.note,
            )
        )


@router.get("/cases/{case_id}/reports", response_model=list[ReportOut])
def list_reports(case_id: int, db: DbSession, user: CurrentUser):
    get_case_for_user(db, case_id, user)
    return (
        db.query(Report).filter(Report.case_id == case_id).order_by(Report.version.desc()).all()
    )


@router.post("/cases/{case_id}/reports", response_model=ReportDetail, status_code=201)
def create_report(
    case_id: int, data: ReportCreate, db: DbSession, user: CurrentUser, request: Request
):
    get_case_for_user(db, case_id, user, write=True)
    next_version = (
        db.query(func.coalesce(func.max(Report.version), 0))
        .filter(Report.case_id == case_id)
        .scalar()
        + 1
    )
    report = Report(
        case_id=case_id,
        version=next_version,
        title=data.title,
        summary=data.summary,
        prepared_by_id=user.id,
    )
    db.add(report)
    db.flush()
    _set_items(db, report, data.items)
    audit(db, request, user, "report_created", "report", report.id, case_id,
          payload={"version": next_version})
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: DbSession, user: CurrentUser):
    return _get_report(db, report_id, user)


@router.patch("/reports/{report_id}", response_model=ReportDetail)
def update_report(
    report_id: int, data: ReportUpdate, db: DbSession, user: CurrentUser, request: Request
):
    report = _get_report(db, report_id, user, write=True)
    if report.status not in EDITABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{_article(report.status.value)} report cannot be edited. "
            "Create a new version instead.",
        )

    if data.title is not None:
        report.title = data.title
    if data.summary is not None:
        report.summary = data.summary
    if data.items is not None:
        _set_items(db, report, data.items)

    audit(db, request, user, "report_updated", "report", report.id, report.case_id)
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/submit", response_model=ReportDetail)
def submit_report(report_id: int, db: DbSession, user: CurrentUser, request: Request):
    """Freeze the findings and hand the report to a supervisor."""
    report = _get_report(db, report_id, user, write=True)
    if report.status not in EDITABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Report is already {report.status.value}"
        )
    if not report.items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "A report must include at least one finding"
        )

    report.snapshot = reporting.build_snapshot(db, report)
    report.content_sha256 = reporting.snapshot_digest(report.snapshot)
    report.status = ReportStatus.submitted
    report.submitted_at = datetime.now(UTC)
    report.decided_by_id = None
    report.decided_at = None

    audit(db, request, user, "report_submitted", "report", report.id, report.case_id,
          payload={"content_sha256": report.content_sha256, "items": len(report.items)})
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/decision", response_model=ReportDetail)
def decide_report(
    report_id: int,
    data: SupervisorDecision,
    db: DbSession,
    user: CurrentUser,
    request: Request,
):
    """Approve or return a submitted report.

    Only supervisors and admins may decide, and never on their own report - the point
    of the step is a second pair of eyes.
    """
    report = _get_report(db, report_id, user)
    if user.role not in {Role.supervisor, Role.admin}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a supervisor can decide a report")
    if report.status is not ReportStatus.submitted:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only a submitted report can be decided; this one is {report.status.value}",
        )
    if report.prepared_by_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "A report cannot be approved by the person who wrote it"
        )
    if not data.approve and not data.note:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Returning a report requires a reason"
        )

    report.status = ReportStatus.approved if data.approve else ReportStatus.returned
    report.decided_by_id = user.id
    report.decided_at = datetime.now(UTC)
    report.decision_note = data.note

    audit(db, request, user, "report_decided", "report", report.id, report.case_id,
          payload={"status": report.status.value})
    db.commit()
    db.refresh(report)
    return report


def _rendered(db: Session, report: Report) -> str:
    case = db.get(Case, report.case_id)
    author = db.get(User, report.prepared_by_id)
    return reporting.render_html(
        report,
        case.reference if case else "",
        case.title if case else "",
        author.full_name if author else "",
    )


@router.get("/reports/{report_id}/preview", response_class=HTMLResponse)
def preview_report(report_id: int, db: DbSession, user: CurrentUser):
    """Render the report as HTML. A draft is previewed from live findings."""
    report = _get_report(db, report_id, user)
    if report.status in EDITABLE:
        report.snapshot = reporting.build_snapshot(db, report)
    return HTMLResponse(_rendered(db, report))


@router.get("/reports/{report_id}/pdf")
def export_pdf(report_id: int, db: DbSession, user: CurrentUser, request: Request):
    """Export the frozen report as a PDF.

    Only submitted or decided reports can be exported: a PDF of a draft would circulate
    as though it were the reviewed record while its findings could still change.
    """
    report = _get_report(db, report_id, user)
    if report.status in EDITABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Submit the report before exporting it. A draft has no frozen content.",
        )

    try:
        pdf = reporting.render_pdf(_rendered(db, report))
    except ImportError as exc:  # pragma: no cover - depends on the deployment image
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "PDF rendering is unavailable in this deployment. Use /preview for HTML.",
        ) from exc

    audit(db, request, user, "report_exported", "report", report.id, report.case_id,
          payload={"content_sha256": report.content_sha256})
    db.commit()

    filename = f"truth-trace-report-{report.case_id}-v{report.version}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Content-SHA256": report.content_sha256 or "",
        },
    )
