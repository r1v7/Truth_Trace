from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import or_

from app.api.deps import CurrentUser, DbSession, audit, get_case_for_user
from app.models import Case, CaseMember, User
from app.models.enums import CaseMemberRole, Role
from app.schemas.case import (
    CaseCreate,
    CaseMemberCreate,
    CaseMemberOut,
    CaseOut,
    CaseUpdate,
)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseOut])
def list_cases(db: DbSession, user: CurrentUser):
    query = db.query(Case)
    if user.role is not Role.admin:
        query = query.join(CaseMember, CaseMember.case_id == Case.id).filter(
            or_(CaseMember.user_id == user.id, Case.created_by_id == user.id)
        )
    return query.order_by(Case.created_at.desc()).all()


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(data: CaseCreate, db: DbSession, user: CurrentUser, request: Request):
    if db.query(Case).filter(Case.reference == data.reference).one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Case reference already exists")
    case = Case(**data.model_dump(), created_by_id=user.id)
    db.add(case)
    db.flush()
    # The creator is always a member, otherwise they would lose their own case.
    db.add(CaseMember(case_id=case.id, user_id=user.id, role=CaseMemberRole.owner))
    audit(db, request, user, "case_created", "case", case.id, case.id)
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: DbSession, user: CurrentUser):
    return get_case_for_user(db, case_id, user)


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int, data: CaseUpdate, db: DbSession, user: CurrentUser, request: Request
):
    case = get_case_for_user(db, case_id, user, write=True)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(case, key, value)
    audit(
        db, request, user, "case_updated", "case", case.id, case.id,
        payload={k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()},
    )
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}/members", response_model=list[CaseMemberOut])
def list_members(case_id: int, db: DbSession, user: CurrentUser):
    get_case_for_user(db, case_id, user)
    return db.query(CaseMember).filter(CaseMember.case_id == case_id).all()


@router.post("/{case_id}/members", response_model=CaseMemberOut, status_code=201)
def add_member(
    case_id: int, data: CaseMemberCreate, db: DbSession, user: CurrentUser, request: Request
):
    case = get_case_for_user(db, case_id, user, write=True)
    if db.get(User, data.user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    existing = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == case_id, CaseMember.user_id == data.user_id)
        .one_or_none()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member of this case")
    member = CaseMember(case_id=case.id, user_id=data.user_id, role=data.role)
    db.add(member)
    db.flush()
    audit(
        db, request, user, "case_member_added", "case_member", member.id, case.id,
        payload={"user_id": data.user_id, "role": data.role.value},
    )
    db.commit()
    db.refresh(member)
    return member
