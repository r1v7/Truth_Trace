from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession, audit, require_role
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models import User
from app.models.enums import Role
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, db: DbSession, request: Request) -> TokenPair:
    user = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    if user is None or not user.is_active or not verify_password(data.password, user.password_hash):
        audit(db, request, None, "login_failed", "user", data.email)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    audit(db, request, user, "login", "user", user.id)
    db.commit()
    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    payload = decode_token(data.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive or unknown")
    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: DbSession,
    request: Request,
    actor: User = Depends(require_role(Role.admin)),
) -> User:
    if db.query(User).filter(User.email == data.email.lower()).one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.flush()
    audit(db, request, actor, "user_created", "user", user.id, payload={"role": data.role.value})
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession, _: User = Depends(require_role(Role.admin, Role.supervisor))):
    return db.query(User).order_by(User.id).all()
