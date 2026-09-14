from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CaseMemberRole, CaseStatus


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"), default=CaseStatus.open, nullable=False
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    members: Mapped[list["CaseMember"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class CaseMember(Base, TimestampMixin):
    __tablename__ = "case_members"
    __table_args__ = (UniqueConstraint("case_id", "user_id", name="uq_case_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[CaseMemberRole] = mapped_column(
        Enum(CaseMemberRole, name="case_member_role"), nullable=False
    )

    case: Mapped[Case] = relationship(back_populates="members")


class Interview(Base, TimestampMixin):
    """One interview session with one subject, holding one or more statements."""

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    subject_name: Mapped[str] = mapped_column(String(255), nullable=False)
    session_label: Mapped[str] = mapped_column(String(128), nullable=False)
    interviewed_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    conducted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    case: Mapped[Case] = relationship(back_populates="interviews")
    statements: Mapped[list["Statement"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )


class Statement(Base, TimestampMixin):
    """The raw text given in an interview, plus its derived claims."""

    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    interview: Mapped[Interview] = relationship(back_populates="statements")
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class Claim(Base, TimestampMixin):
    """A single sentence-level assertion extracted from a statement.

    Offsets point back into Statement.body so the UI can always cite the source text.
    """

    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(nullable=False)
    end_offset: Mapped[int] = mapped_column(nullable=False)

    statement: Mapped[Statement] = relationship(back_populates="claims")
