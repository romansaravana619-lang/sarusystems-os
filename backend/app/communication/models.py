from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class ActivityRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "communication_activity_records"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="internal", index=True)
    subject: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[UUID | None] = mapped_column(ForeignKey("clients.id"), index=True)
    contact_id: Mapped[UUID | None] = mapped_column(ForeignKey("contacts.id"), index=True)
    prospect_id: Mapped[UUID | None] = mapped_column(ForeignKey("prospects.id"), index=True)
    opportunity_id: Mapped[UUID | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    freelancer_id: Mapped[UUID | None] = mapped_column(ForeignKey("freelancers.id"), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), index=True)
    external_reference: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
