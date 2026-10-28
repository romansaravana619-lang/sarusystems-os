from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CAMPAIGN_STATUSES = {"planned", "active", "paused", "completed", "cancelled"}
CAMPAIGN_OBJECTIVES = {"awareness", "lead_generation", "engagement", "traffic", "conversion", "retention", "recruitment"}
CAMPAIGN_CHANNELS = {"website", "instagram", "facebook", "linkedin", "youtube", "whatsapp", "email", "google_ads", "meta_ads", "offline", "other"}
AUDIENCE_STATUSES = {"active", "inactive"}
ACTIVITY_TYPES = {"campaign_launch", "content_published", "outreach", "event", "promotion", "partnership", "review", "optimization", "other"}


class AudienceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    segment: str | None = None
    location: str | None = None
    industry: str | None = None
    size_band: str | None = None
    status: str = "active"


class AudienceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    segment: str | None = None
    location: str | None = None
    industry: str | None = None
    size_band: str | None = None
    status: str | None = None


class AudienceResponse(AudienceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    objective: str
    channel: str
    audience_id: UUID | None = None
    status: str = "planned"
    start_at: datetime | None = None
    end_at: datetime | None = None
    budget: float | None = Field(default=None, ge=0)
    owner_user_id: UUID | None = None
    goal: str | None = None
    notes: str | None = None
    target_leads: int | None = Field(default=None, ge=0)
    target_conversions: int | None = Field(default=None, ge=0)
    target_spend: float | None = Field(default=None, ge=0)
    target_revenue: float | None = Field(default=None, ge=0)


class CampaignUpdate(CampaignCreate):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    objective: str | None = None
    channel: str | None = None
    status: str | None = None
    budget: float | None = Field(default=None, ge=0)
    target_leads: int | None = Field(default=None, ge=0)
    target_conversions: int | None = Field(default=None, ge=0)
    target_spend: float | None = Field(default=None, ge=0)
    target_revenue: float | None = Field(default=None, ge=0)


class CampaignResponse(CampaignCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class ProspectLinkCreate(BaseModel):
    prospect_id: UUID
    attribution_source: str | None = None


class MetricCreate(BaseModel):
    metric_date: datetime
    impressions: int = Field(default=0, ge=0)
    reach: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    leads: int = Field(default=0, ge=0)
    positive_replies: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: float = Field(default=0, ge=0)
    spend: float = Field(default=0, ge=0)


class MetricResponse(MetricCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    campaign_id: UUID
    created_at: datetime
    updated_at: datetime


class ActivityCreate(BaseModel):
    campaign_id: UUID | None = None
    activity_type: str = Field(min_length=1, max_length=80)
    channel: str = Field(min_length=1, max_length=80)
    activity_date: datetime
    description: str = Field(min_length=1)
    outcome: str | None = None
    owner_user_id: UUID | None = None


class ActivityResponse(ActivityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class MarketingDashboardResponse(BaseModel):
    total_campaigns: int
    active_campaigns: int
    planned_campaigns: int
    paused_campaigns: int
    completed_campaigns: int
    total_budget: float
    total_spend: float
    total_revenue: float
    impressions: int
    reach: int
    clicks: int
    leads: int
    positive_replies: int
    conversions: int
    campaign_conversion_rate: float
    ctr: float
    cost_per_lead: float
    cost_per_conversion: float
    roas: float
    by_channel: dict[str, int]
    by_objective: dict[str, int]
    by_status: dict[str, int]
    recent_activities: list[ActivityResponse]
