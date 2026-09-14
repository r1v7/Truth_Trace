from datetime import datetime

from pydantic import BaseModel

from app.models.enums import EvidenceKind, IntegrityStatus


class EvidenceOut(BaseModel):
    id: int
    case_id: int
    kind: EvidenceKind
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    description: str | None
    uploaded_by_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrityOut(BaseModel):
    evidence_id: int
    status: IntegrityStatus
    recorded_sha256: str
    computed_sha256: str | None
    checked_at: datetime
    note: str = (
        "A matching digest shows the stored file has not changed since it was uploaded. "
        "It does not show that the contents are accurate or that the file is authentic."
    )


class EvidenceCheckCreate(BaseModel):
    interview_id: int
