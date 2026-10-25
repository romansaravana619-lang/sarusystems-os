from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import UUIDPrimaryKeyMixin, TimestampMixin


class Client(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clients"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    opportunity_id: Mapped[UUID] = mapped_column(ForeignKey("opportunities.id"), unique=True, nullable=False, index=True)
    source_contact_id: Mapped[UUID] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    website: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str | None] = mapped_column(String(100))
    preferred_contact_channel: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="onboarding", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    health_status: Mapped[str] = mapped_column(String(30), nullable=False, default="healthy", index=True)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    health_reason: Mapped[str | None] = mapped_column(Text)
    last_health_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_health_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    onboarding_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClientContact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "client_contacts"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[str | None] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class Agreement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "client_agreements"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    document_id: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)


class ClientOnboardingItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "client_onboarding_items"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class ClientDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "client_documents"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    external_document_id: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)


class ClientRelation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Client relationship index; downstream modules remain authoritative for their records."""

    __tablename__ = "client_relations"

    client_id: Mapped[UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    related_entity_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
