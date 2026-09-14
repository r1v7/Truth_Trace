from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import FindingField, FindingType, ReviewDecision, RunKind, RunStatus


class AnalysisRun(Base, TimestampMixin):
    """One comparison: either two interviews of the same subject, or an interview
    against a piece of text evidence.

    Both kinds produce the same findings and go through the same review, so the
    investigator reads one kind of result rather than two.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    kind: Mapped[RunKind] = mapped_column(
        Enum(RunKind, name="run_kind"), default=RunKind.interview_pair, nullable=False
    )
    interview_a_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"))
    interview_b_id: Mapped[int | None] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE")
    )
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.pending, nullable=False
    )
    analyzer_backend: Mapped[str] = mapped_column(String(64), nullable=False)
    analyzer_version: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    findings: Mapped[list["Finding"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Finding(Base, TimestampMixin):
    """A single comparison result linking one claim from each interview.

    `score` is the engine's internal similarity/agreement score. It is deliberately
    NOT labelled a confidence percentage anywhere in the UI: it has not been
    calibrated against ground-truth data yet.
    """

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True
    )
    claim_a_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    claim_b_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    finding_type: Mapped[FindingType] = mapped_column(
        Enum(FindingType, name="finding_type"), nullable=False
    )
    field: Mapped[FindingField] = mapped_column(
        Enum(FindingField, name="finding_field"), default=FindingField.other, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="findings")
    reviews: Mapped[list["FindingReview"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class FindingReview(Base, TimestampMixin):
    """An investigator's or supervisor's judgement on a finding. The human decides."""

    __tablename__ = "finding_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, name="review_decision"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)

    finding: Mapped[Finding] = relationship(back_populates="reviews")
