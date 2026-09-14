from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ReportStatus


class ReportItemIn(BaseModel):
    finding_id: int
    note: str | None = None


class ReportCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    summary: str | None = None
    items: list[ReportItemIn] = Field(default_factory=list)


class ReportUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    items: list[ReportItemIn] | None = None


class ReportItemOut(BaseModel):
    finding_id: int
    position: int
    note: str | None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: int
    case_id: int
    version: int
    title: str
    summary: str | None
    status: ReportStatus
    content_sha256: str | None
    prepared_by_id: int
    submitted_at: datetime | None
    decided_by_id: int | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime
    items: list[ReportItemOut] = []

    model_config = {"from_attributes": True}


class ReportDetail(ReportOut):
    snapshot: dict[str, Any] = {}


class SupervisorDecision(BaseModel):
    approve: bool
    note: str | None = None
