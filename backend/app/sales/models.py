from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import UUIDPrimaryKeyMixin, TimestampMixin


class Discovery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "discoveries"

    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    business_problem: Mapped[str | None] = mapped_column(Text)
    goals: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class Requirement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "requirements"

    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class Proposal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "proposals"

    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class DealOutcome(Base):
    __tablename__ = "deal_outcomes"

    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), primary_key=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    decided_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
