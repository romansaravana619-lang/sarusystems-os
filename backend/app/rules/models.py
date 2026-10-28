from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class SOPDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sop_definitions"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    sop_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    purpose: Mapped[str | None] = mapped_column(Text)
    scope: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    required_roles: Mapped[list] = mapped_column(JSON, default=list)
    entry_conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    exit_conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    prohibited_actions: Mapped[list] = mapped_column(JSON, default=list)
    linked_document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "sop_key", name="uq_sops_company_key"),)


class BusinessRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "business_rules"

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    trigger_event: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    applies_to: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    required_conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    prohibited_conditions: Mapped[dict] = mapped_column(JSON, default=dict)
    required_actions: Mapped[list] = mapped_column(JSON, default=list)
    prohibited_actions: Mapped[list] = mapped_column(JSON, default=list)
    allowed_roles: Mapped[list] = mapped_column(JSON, default=list)
    allowed_user_ids: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    enforcement_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="block")
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    reviewer_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (UniqueConstraint("company_id", "rule_key", name="uq_rules_company_key"),)
