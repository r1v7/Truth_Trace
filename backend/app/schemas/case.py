from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import CaseMemberRole, CaseStatus


class CaseCreate(BaseModel):
    reference: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: CaseStatus | None = None


class CaseOut(BaseModel):
    id: int
    reference: str
    title: str
    description: str | None
    status: CaseStatus
    created_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseMemberCreate(BaseModel):
    user_id: int
    role: CaseMemberRole


class CaseMemberOut(BaseModel):
    id: int
    user_id: int
    role: CaseMemberRole

    model_config = {"from_attributes": True}


class InterviewCreate(BaseModel):
    subject_name: str = Field(min_length=2, max_length=255)
    session_label: str = Field(min_length=1, max_length=128)
    interviewed_on: date | None = None
    notes: str | None = None


class InterviewOut(BaseModel):
    id: int
    case_id: int
    subject_name: str
    session_label: str
    interviewed_on: date | None
    notes: str | None
    conducted_by_id: int

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: int
    ordinal: int
    text: str
    start_offset: int
    end_offset: int

    model_config = {"from_attributes": True}


class StatementCreate(BaseModel):
    body: str = Field(min_length=1)
    language: str = "en"


class StatementOut(BaseModel):
    id: int
    interview_id: int
    language: str
    body: str
    claims: list[ClaimOut] = []

    model_config = {"from_attributes": True}
