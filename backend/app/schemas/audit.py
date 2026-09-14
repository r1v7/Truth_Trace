from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    created_at: datetime
    actor_id: int | None
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str | None
    case_id: int | None
    case_reference: str | None
    ip_address: str | None
    payload: dict[str, Any]


class AuditPage(BaseModel):
    total: int
    offset: int
    limit: int
    entries: list[AuditEntryOut]
