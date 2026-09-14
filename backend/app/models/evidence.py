from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import EvidenceKind


class Evidence(Base, TimestampMixin):
    """A digital file attached to a case.

    The file itself lives outside the database; this row holds its identity. The
    SHA-256 digest is recorded once at upload and never recomputed into this column -
    verification compares a fresh digest against this stored one. A matching digest
    proves the bytes have not changed since upload. It says nothing about whether the
    contents are true, or about where the file came from before it reached the system.
    """

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    kind: Mapped[EvidenceKind] = mapped_column(
        Enum(EvidenceKind, name="evidence_kind"), default=EvidenceKind.other, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
