from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func

from app.api.deps import CurrentUser, DbSession
from app.models import AuditLog, Case, CaseMember, User
from app.models.enums import Role
from app.schemas.audit import AuditEntryOut, AuditPage

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
def list_audit(
    db: DbSession,
    user: CurrentUser,
    case_id: int | None = None,
    days: int | None = Query(None, ge=1, le=365),
    action: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Read the audit trail.

    The trail is append-only: there is no endpoint to edit or delete an entry, and
    none will be added. Supervisors and admins see everything; an investigator sees
    only entries for cases they are a member of, so the trail cannot be used to learn
    about cases they have no access to.
    """
    query = db.query(AuditLog)

    if user.role not in {Role.admin, Role.supervisor}:
        visible = db.query(CaseMember.case_id).filter(CaseMember.user_id == user.id).subquery()
        query = query.filter(AuditLog.case_id.in_(visible))

    if case_id is not None:
        query = query.filter(AuditLog.case_id == case_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if days is not None:
        query = query.filter(AuditLog.created_at >= datetime.now(UTC) - timedelta(days=days))

    total = query.with_entities(func.count(AuditLog.id)).scalar() or 0
    rows = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Names are resolved here rather than stored on the row: the trail records who acted,
    # and a later rename should not rewrite history's spelling of it.
    actor_ids = {row.actor_id for row in rows if row.actor_id}
    case_ids = {row.case_id for row in rows if row.case_id}
    actors = (
        {u.id: u.full_name for u in db.query(User).filter(User.id.in_(actor_ids)).all()}
        if actor_ids
        else {}
    )
    cases = (
        {c.id: c.reference for c in db.query(Case).filter(Case.id.in_(case_ids)).all()}
        if case_ids
        else {}
    )

    return AuditPage(
        total=total,
        offset=offset,
        limit=limit,
        entries=[
            AuditEntryOut(
                id=row.id,
                created_at=row.created_at,
                actor_id=row.actor_id,
                actor_name=actors.get(row.actor_id) if row.actor_id else None,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                case_id=row.case_id,
                case_reference=cases.get(row.case_id) if row.case_id else None,
                ip_address=row.ip_address,
                payload=row.payload,
            )
            for row in rows
        ],
    )


@router.get("/actions", response_model=list[str])
def list_actions(db: DbSession, user: CurrentUser):
    """The action names present in the trail, for building a filter."""
    query = db.query(AuditLog.action).distinct()
    if user.role not in {Role.admin, Role.supervisor}:
        visible = db.query(CaseMember.case_id).filter(CaseMember.user_id == user.id).subquery()
        query = query.filter(AuditLog.case_id.in_(visible))
    return sorted(row[0] for row in query.all())
