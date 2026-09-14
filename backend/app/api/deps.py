from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import AuditLog, Case, CaseMember, User
from app.models.enums import CaseMemberRole, Role

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive or unknown")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return checker


def get_case_for_user(db: Session, case_id: int, user: User, *, write: bool = False) -> Case:
    """Admins see everything; everyone else needs a membership row.

    Reviewers may read a case but not change its data.
    """
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if user.role is Role.admin:
        return case

    membership = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == case_id, CaseMember.user_id == user.id)
        .one_or_none()
    )
    if membership is None:
        # Do not reveal that the case exists to someone with no access to it.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    if write and membership.role is CaseMemberRole.reviewer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Reviewers have read-only access")
    return case


def audit(
    db: Session,
    request: Request,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    case_id: int | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            case_id=case_id,
            ip_address=request.client.host if request.client else None,
            payload=payload or {},
        )
    )
