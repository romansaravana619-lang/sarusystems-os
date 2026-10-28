from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin, UUIDPrimaryKeyMixin


class MarketingAudience(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_audiences"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    segment: Mapped[str | None] = mapped_column(String(120), index=True)
    location: Mapped[str | None] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(120))
    size_band: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)


class MarketingCampaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_campaigns"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    audience_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketing_audiences.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="planned", index=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    budget: Mapped[float | None] = mapped_column(Numeric(12, 2))
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    target_leads: Mapped[int | None] = mapped_column(Integer)
    target_conversions: Mapped[int | None] = mapped_column(Integer)
    target_spend: Mapped[float | None] = mapped_column(Numeric(12, 2))
    target_revenue: Mapped[float | None] = mapped_column(Numeric(12, 2))


class CampaignProspect(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_campaign_prospects"
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    prospect_id: Mapped[UUID] = mapped_column(ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    attribution_source: Mapped[str | None] = mapped_column(String(120))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("campaign_id", "prospect_id", name="uq_marketing_campaign_prospect"),)


class CampaignMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_campaign_metrics"
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reach: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    positive_replies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    spend: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    __table_args__ = (UniqueConstraint("campaign_id", "metric_date", name="uq_marketing_campaign_metric_date"),)


class MarketingActivity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "marketing_activities"
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), index=True)
    activity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    activity_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
