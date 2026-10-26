from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin

class ContentIdea(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "content_ideas"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    pillar: Mapped[str | None] = mapped_column(String(120), index=True)
    audience: Mapped[str | None] = mapped_column(String(200))
    objective: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="idea", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)

class ContentAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "content_assets"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    idea_id: Mapped[UUID | None] = mapped_column(ForeignKey("content_ideas.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    file_url: Mapped[str | None] = mapped_column(Text)
    script: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    copy_text: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft", index=True)
    brand_qa_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ContentProduction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "content_productions"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    idea_id: Mapped[UUID | None] = mapped_column(ForeignKey("content_ideas.id", ondelete="SET NULL"), index=True)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("content_assets.id", ondelete="SET NULL"), index=True)
    producer_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned", index=True)
    brief: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class ContentPublication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "content_publications"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_reference: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("asset_id", "platform", name="uq_content_asset_platform"),)
