from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import FindingField, FindingType, ReviewDecision, RunStatus


class AnalysisRunCreate(BaseModel):
    interview_a_id: int
    interview_b_id: int


class ClaimRef(BaseModel):
    id: int
    text: str
    statement_id: int
    start_offset: int
    end_offset: int


class FindingOut(BaseModel):
    id: int
    finding_type: FindingType
    field: FindingField
    score: float
    explanation: str
    details: dict[str, Any]
    claim_a: ClaimRef | None = None
    claim_b: ClaimRef | None = None
    latest_decision: ReviewDecision | None = None


class AnalysisRunOut(BaseModel):
    id: int
    case_id: int
    interview_a_id: int
    interview_b_id: int
    status: RunStatus
    analyzer_backend: str
    analyzer_version: str
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisRunDetail(AnalysisRunOut):
    findings: list[FindingOut] = []


class ReviewCreate(BaseModel):
    decision: ReviewDecision
    comment: str | None = None


class ReviewOut(BaseModel):
    id: int
    finding_id: int
    reviewer_id: int
    decision: ReviewDecision
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
