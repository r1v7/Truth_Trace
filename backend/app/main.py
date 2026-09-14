import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, auth, cases, interviews
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.models.enums import Role

log = logging.getLogger("truthtrace")


def bootstrap_admin() -> None:
    """Create the first admin once, so a fresh deployment is reachable."""
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return
        db.add(
            User(
                email=settings.first_admin_email.lower(),
                full_name="System Administrator",
                password_hash=hash_password(settings.first_admin_password),
                role=Role.admin,
            )
        )
        db.commit()
        log.warning(
            "Bootstrap admin created: %s - change this password.", settings.first_admin_email
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        bootstrap_admin()
    except Exception:  # noqa: BLE001 - never block startup on bootstrap
        log.exception("Bootstrap admin skipped")
    yield


app = FastAPI(
    title="Truth Trace API",
    description="Decision-support API for comparing investigative statements. "
    "The system surfaces differences; the investigator decides.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "analyzer": settings.analyzer_backend}
