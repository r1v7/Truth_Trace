from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ReportStatus


class Report(Base, TimestampMixin):
    """An investigation report drafted from reviewed findings.

    `snapshot` holds the findings exactly as they read when the report was submitted.
    A report is what a supervisor signed off on, so it must not silently change when
    someone later edits a statement or re-runs an analysis - the frozen copy is the
    record, and `content_sha256` lets anyone confirm the PDF matches it.
    """

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), default=ReportStatus.draft, nullable=False
    )

    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    content_sha256: Mapped[str | None] = mapped_column(String(64))

    prepared_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("case_id", "version", name="uq_report_case_version"),)

    items: Mapped[list["ReportItem"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportItem(Base, TimestampMixin):
    """One finding the investigator chose to include, in the order they chose."""

    __tablename__ = "report_items"
    __table_args__ = (UniqueConstraint("report_id", "finding_id", name="uq_report_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    report: Mapped[Report] = relationship(back_populates="items")
