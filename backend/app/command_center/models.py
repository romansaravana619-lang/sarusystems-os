from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import UUIDPrimaryKeyMixin, TimestampMixin


class FounderAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "founder_actions"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_entity_id: Mapped[UUID | None] = mapped_column(index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_action: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open", index=True)
    founder_notes: Mapped[str | None] = mapped_column(Text)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
