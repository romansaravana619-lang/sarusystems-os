from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.marketing.models import CampaignMetric, CampaignProspect, MarketingActivity, MarketingAudience, MarketingCampaign
from app.marketing.schemas import *
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/marketing", tags=["marketing"])
TRANSITIONS = {
    "planned": {"active", "cancelled"},
    "active": {"paused", "completed", "cancelled"},
    "paused": {"active", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _campaign(db, company_id, campaign_id):
    obj = db.get(MarketingCampaign, campaign_id)
    if not obj or obj.company_id != company_id:
        raise HTTPException(404, "Campaign not found.")
    return obj


def _audience(db, company_id, audience_id):
    obj = db.get(MarketingAudience, audience_id)
    if not obj or obj.company_id != company_id:
        raise HTTPException(404, "Audience not found.")
    return obj


def _owner(db, company_id, owner_user_id):
    if owner_user_id is None:
        return None
    user = db.get(User, owner_user_id)
    if not user or user.company_id != company_id or not user.is_active:
        raise HTTPException(400, "Marketing owner must be an active user in the same company.")
    return user


def _valid_campaign(p):
    if p.status is not None and p.status not in CAMPAIGN_STATUSES:
        raise HTTPException(400, "Invalid campaign status.")
    if p.objective is not None and p.objective not in CAMPAIGN_OBJECTIVES:
        raise HTTPException(400, "Invalid campaign objective.")
    if p.channel is not None and p.channel not in CAMPAIGN_CHANNELS:
        raise HTTPException(400, "Invalid campaign channel.")


def _audit(db, user, action, entity, obj, details=""):
    db.add(AuditLog(actor_user_id=user.id, action=action, entity_type=entity, entity_id=str(obj.id), details=details))


def _sync_campaign_attribution(db, campaign, prospect=None):
    query = select(CampaignProspect).where(CampaignProspect.campaign_id == campaign.id)
    if prospect is not None:
        query = query.where(CampaignProspect.prospect_id == prospect.id)
    links = list(db.scalars(query).all())
    if not links:
        return 0
    from app.crm.models import Prospect

    prospect_ids = [link.prospect_id for link in links]
    prospects = {p.id: p for p in db.scalars(select(Prospect).where(Prospect.id.in_(prospect_ids), Prospect.company_id == campaign.company_id)).all()}
    changed = 0
    for link in links:
        crm_prospect = prospects.get(link.prospect_id)
        if not crm_prospect:
            continue
        if crm_prospect.status == "won" and link.converted_at is None:
            from datetime import datetime, timezone
            link.converted_at = datetime.now(timezone.utc)
            changed += 1
    return changed


@router.get("/dashboard", response_model=MarketingDashboardResponse)
def dashboard(current_user: User = Depends(require_permission("marketing.dashboard.view")), db: Session = Depends(get_db)):
    campaigns = list(db.scalars(select(MarketingCampaign).where(MarketingCampaign.company_id == current_user.company_id)).all())
    metrics = list(db.scalars(select(CampaignMetric).join(MarketingCampaign, CampaignMetric.campaign_id == MarketingCampaign.id).where(MarketingCampaign.company_id == current_user.company_id)).all())
    activities = list(db.scalars(select(MarketingActivity).where(MarketingActivity.company_id == current_user.company_id).order_by(MarketingActivity.activity_date.desc()).limit(10)).all())
    spend = sum(float(x.spend or 0) for x in metrics)
    revenue = sum(float(x.revenue or 0) for x in metrics)
    impressions = sum(x.impressions for x in metrics)
    reach = sum(x.reach for x in metrics)
    clicks = sum(x.clicks for x in metrics)
    leads = sum(x.leads for x in metrics)
    positive = sum(x.positive_replies for x in metrics)
    conversions = sum(x.conversions for x in metrics)
    return MarketingDashboardResponse(
        total_campaigns=len(campaigns),
        active_campaigns=sum(x.status == "active" for x in campaigns),
        planned_campaigns=sum(x.status == "planned" for x in campaigns),
        paused_campaigns=sum(x.status == "paused" for x in campaigns),
        completed_campaigns=sum(x.status == "completed" for x in campaigns),
        total_budget=sum(float(x.budget or 0) for x in campaigns),
        total_spend=spend,
        total_revenue=revenue,
        impressions=impressions,
        reach=reach,
        clicks=clicks,
        leads=leads,
        positive_replies=positive,
        conversions=conversions,
        campaign_conversion_rate=round(conversions / leads * 100, 2) if leads else 0,
        ctr=round(clicks / impressions * 100, 2) if impressions else 0,
        cost_per_lead=round(spend / leads, 2) if leads else 0,
        cost_per_conversion=round(spend / conversions, 2) if conversions else 0,
        roas=round(revenue / spend, 2) if spend else 0,
        by_channel=dict(Counter(x.channel for x in campaigns)),
        by_objective=dict(Counter(x.objective for x in campaigns)),
        by_status=dict(Counter(x.status for x in campaigns)),
        recent_activities=activities,
    )


@router.get("/audiences", response_model=list[AudienceResponse])
def list_audiences(current_user: User = Depends(require_permission("marketing.audiences.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(MarketingAudience).where(MarketingAudience.company_id == current_user.company_id).order_by(MarketingAudience.name)).all())


@router.post("/audiences", response_model=AudienceResponse, status_code=201)
def create_audience(p: AudienceCreate, current_user: User = Depends(require_permission("marketing.audiences.create")), db: Session = Depends(get_db)):
    if p.status not in AUDIENCE_STATUSES:
        raise HTTPException(400, "Invalid audience status.")
    obj = MarketingAudience(company_id=current_user.company_id, **p.model_dump())
    db.add(obj)
    db.flush()
    _audit(db, current_user, "marketing.audience.create", "MarketingAudience", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/audiences/{audience_id}", response_model=AudienceResponse)
def update_audience(audience_id: UUID, p: AudienceUpdate, current_user: User = Depends(require_permission("marketing.audiences.edit")), db: Session = Depends(get_db)):
    obj = _audience(db, current_user.company_id, audience_id)
    changes = p.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] not in AUDIENCE_STATUSES:
        raise HTTPException(400, "Invalid audience status.")
    for key, value in changes.items():
        setattr(obj, key, value)
    _audit(db, current_user, "marketing.audience.update", "MarketingAudience", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(current_user: User = Depends(require_permission("marketing.campaigns.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(MarketingCampaign).where(MarketingCampaign.company_id == current_user.company_id).order_by(MarketingCampaign.created_at.desc())).all())


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(p: CampaignCreate, current_user: User = Depends(require_permission("marketing.campaigns.create")), db: Session = Depends(get_db)):
    _valid_campaign(p)
    if p.end_at and p.start_at and p.end_at < p.start_at:
        raise HTTPException(400, "Campaign end cannot precede start.")
    if p.audience_id:
        _audience(db, current_user.company_id, p.audience_id)
    _owner(db, current_user.company_id, p.owner_user_id)
    if p.target_spend is not None and p.budget is not None and p.target_spend > p.budget:
        raise HTTPException(400, "Target spend cannot exceed campaign budget.")
    obj = MarketingCampaign(company_id=current_user.company_id, **p.model_dump())
    db.add(obj)
    db.flush()
    _audit(db, current_user, "marketing.campaign.create", "MarketingCampaign", obj, obj.name)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: UUID, p: CampaignUpdate, current_user: User = Depends(require_permission("marketing.campaigns.edit")), db: Session = Depends(get_db)):
    obj = _campaign(db, current_user.company_id, campaign_id)
    changes = p.model_dump(exclude_unset=True)
    new_status = changes.get("status", obj.status)
    if new_status not in CAMPAIGN_STATUSES:
        raise HTTPException(400, "Invalid campaign status.")
    if new_status != obj.status and new_status not in TRANSITIONS[obj.status]:
        raise HTTPException(409, "Invalid campaign lifecycle transition.")
    if "objective" in changes and changes["objective"] not in CAMPAIGN_OBJECTIVES:
        raise HTTPException(400, "Invalid campaign objective.")
    if "channel" in changes and changes["channel"] not in CAMPAIGN_CHANNELS:
        raise HTTPException(400, "Invalid campaign channel.")
    if "audience_id" in changes and changes["audience_id"]:
        _audience(db, current_user.company_id, changes["audience_id"])
    if "owner_user_id" in changes:
        _owner(db, current_user.company_id, changes["owner_user_id"])
    for key, value in changes.items():
        setattr(obj, key, value)
    if obj.end_at and obj.start_at and obj.end_at < obj.start_at:
        raise HTTPException(400, "Campaign end cannot precede start.")
    if obj.target_spend is not None and obj.budget is not None and obj.target_spend > obj.budget:
        raise HTTPException(400, "Target spend cannot exceed campaign budget.")
    _audit(db, current_user, "marketing.campaign.update", "MarketingCampaign", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/campaigns/{campaign_id}/prospects", status_code=201)
def link_prospect(campaign_id: UUID, p: ProspectLinkCreate, current_user: User = Depends(require_permission("marketing.campaigns.edit")), db: Session = Depends(get_db)):
    campaign = _campaign(db, current_user.company_id, campaign_id)
    from app.crm.models import Prospect
    prospect = db.get(Prospect, p.prospect_id)
    if not prospect or prospect.company_id != current_user.company_id:
        raise HTTPException(404, "Prospect not found.")
    if db.scalar(select(CampaignProspect).where(CampaignProspect.campaign_id == campaign.id, CampaignProspect.prospect_id == prospect.id)):
        raise HTTPException(409, "Prospect already linked to campaign.")
    obj = CampaignProspect(campaign_id=campaign.id, prospect_id=prospect.id, attribution_source=p.attribution_source)
    db.add(obj)
    db.flush()
    _sync_campaign_attribution(db, campaign, prospect)
    _audit(db, current_user, "marketing.campaign.prospect_link", "CampaignProspect", obj)
    db.commit()
    return {"id": str(obj.id), "campaign_id": str(campaign.id), "prospect_id": str(prospect.id), "converted": obj.converted_at is not None}


@router.post("/campaigns/{campaign_id}/attribution/sync")
def sync_attribution(campaign_id: UUID, current_user: User = Depends(require_permission("marketing.campaigns.edit")), db: Session = Depends(get_db)):
    campaign = _campaign(db, current_user.company_id, campaign_id)
    changed = _sync_campaign_attribution(db, campaign)
    if changed:
        _audit(db, current_user, "marketing.campaign.attribution_sync", "MarketingCampaign", campaign, f"converted_links={changed}")
    db.commit()
    return {"campaign_id": str(campaign.id), "converted_links_updated": changed}


@router.post("/campaigns/{campaign_id}/metrics", response_model=MetricResponse, status_code=201)
def add_metric(campaign_id: UUID, p: MetricCreate, current_user: User = Depends(require_permission("marketing.metrics.manage")), db: Session = Depends(get_db)):
    campaign = _campaign(db, current_user.company_id, campaign_id)
    metric_exists = db.scalar(select(CampaignMetric).where(CampaignMetric.campaign_id == campaign.id, CampaignMetric.metric_date == p.metric_date))
    if metric_exists:
        raise HTTPException(409, "A metric record already exists for this campaign and date.")
    obj = CampaignMetric(campaign_id=campaign.id, **p.model_dump())
    db.add(obj)
    db.flush()
    _audit(db, current_user, "marketing.metric.create", "CampaignMetric", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/campaigns/{campaign_id}/metrics", response_model=list[MetricResponse])
def list_metrics(campaign_id: UUID, current_user: User = Depends(require_permission("marketing.dashboard.view")), db: Session = Depends(get_db)):
    campaign = _campaign(db, current_user.company_id, campaign_id)
    return list(db.scalars(select(CampaignMetric).where(CampaignMetric.campaign_id == campaign.id).order_by(CampaignMetric.metric_date.desc())).all())


@router.get("/activities", response_model=list[ActivityResponse])
def list_activities(current_user: User = Depends(require_permission("marketing.activities.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(MarketingActivity).where(MarketingActivity.company_id == current_user.company_id).order_by(MarketingActivity.activity_date.desc())).all())


@router.post("/activities", response_model=ActivityResponse, status_code=201)
def create_activity(p: ActivityCreate, current_user: User = Depends(require_permission("marketing.activities.create")), db: Session = Depends(get_db)):
    if p.activity_type not in ACTIVITY_TYPES:
        raise HTTPException(400, "Invalid marketing activity type.")
    if p.channel not in CAMPAIGN_CHANNELS:
        raise HTTPException(400, "Invalid marketing activity channel.")
    if p.campaign_id:
        _campaign(db, current_user.company_id, p.campaign_id)
    _owner(db, current_user.company_id, p.owner_user_id)
    obj = MarketingActivity(company_id=current_user.company_id, **p.model_dump())
    db.add(obj)
    db.flush()
    _audit(db, current_user, "marketing.activity.create", "MarketingActivity", obj)
    db.commit()
    db.refresh(obj)
    return obj
