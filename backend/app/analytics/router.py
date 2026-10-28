from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.content.models import ContentAsset, ContentPublication
from app.core.database import get_db
from app.finance.models import FinancialTransaction, PaymentMilestone
from app.freelancers.models import Freelancer, FreelancerAssignment, FreelancerPerformance
from app.marketing.models import CampaignMetric, MarketingCampaign, CampaignProspect
from app.notifications.models import Notification
from app.projects.models import Milestone, Project, ProjectRisk
from app.shared.models import Opportunity, Prospect, User
from app.social_media.models import SocialPost
from app.tasks.models import Task

router = APIRouter(prefix="/analytics", tags=["Analytics"])
PERMISSION = "analytics.dashboard.view"


def _count(db: Session, model, company_id, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(model.company_id == company_id, *conditions)) or 0)


def _sales(db: Session, company_id):
    total = _count(db, Prospect, company_id)
    won = _count(db, Prospect, company_id, Prospect.status == "won")
    lost = _count(db, Prospect, company_id, Prospect.status == "lost")
    qualified = _count(db, Prospect, company_id, Prospect.status.in_({"responded", "discovery_scheduled", "discovery_completed", "proposal_sent", "negotiation", "won"}))
    open_opps = _count(db, Opportunity, company_id, Opportunity.stage.notin_({"won", "lost"}))
    won_opps = _count(db, Opportunity, company_id, Opportunity.stage == "won")
    pipeline = db.scalar(select(func.coalesce(func.sum(Opportunity.estimated_value), 0)).where(Opportunity.company_id == company_id, Opportunity.stage.notin_({"won", "lost"}))) or Decimal("0")
    won_value = db.scalar(select(func.coalesce(func.sum(Opportunity.estimated_value), 0)).where(Opportunity.company_id == company_id, Opportunity.stage == "won")) or Decimal("0")
    return {"prospects": total, "qualified_leads": qualified, "won_prospects": won, "lost_prospects": lost, "open_opportunities": open_opps, "won_opportunities": won_opps, "pipeline_value": float(pipeline), "won_value": float(won_value), "lead_conversion_rate": round((won / total) * 100, 2) if total else 0.0}


def _revenue(db: Session, company_id):
    income = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == company_id, FinancialTransaction.transaction_type == "income")) or Decimal("0")
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialTransaction.amount), 0)).where(FinancialTransaction.company_id == company_id, FinancialTransaction.transaction_type == "expense")) or Decimal("0")
    outstanding = db.scalar(select(func.coalesce(func.sum(PaymentMilestone.amount - PaymentMilestone.paid_amount), 0)).where(PaymentMilestone.company_id == company_id, PaymentMilestone.status != "paid")) or Decimal("0")
    return {"revenue": float(income), "expenses": float(expenses), "net": float(income - expenses), "outstanding": float(outstanding)}


def _projects(db: Session, company_id):
    now = datetime.now(timezone.utc)
    active = _count(db, Project, company_id, Project.status.notin_({"completed", "cancelled", "closed"}))
    completed = _count(db, Project, company_id, Project.status.in_({"completed", "closed"}))
    overdue = _count(db, Project, company_id, Project.target_end_at.is_not(None), Project.target_end_at < now, Project.status.notin_({"completed", "cancelled", "closed"}))
    risks = int(db.scalar(select(func.count()).select_from(ProjectRisk).join(Project, Project.id == ProjectRisk.project_id).where(Project.company_id == company_id, ProjectRisk.status == "open")) or 0)
    milestones_due = int(db.scalar(select(func.count()).select_from(Milestone).join(Project, Project.id == Milestone.project_id).where(Project.company_id == company_id, Milestone.due_at.is_not(None), Milestone.due_at < now, Milestone.status.notin_({"completed", "approved"}))) or 0)
    return {"active": active, "completed": completed, "overdue": overdue, "open_risks": risks, "overdue_milestones": milestones_due}


def _freelancers(db: Session, company_id):
    total = _count(db, Freelancer, company_id)
    active = _count(db, Freelancer, company_id, Freelancer.status.in_({"active", "approved", "onboarding"}))
    assigned = int(db.scalar(select(func.count()).select_from(FreelancerAssignment).join(Freelancer, Freelancer.id == FreelancerAssignment.freelancer_id).where(Freelancer.company_id == company_id, FreelancerAssignment.status.in_({"active", "confirmed"}))) or 0)
    avg = db.scalar(select(func.avg(FreelancerPerformance.overall_score)).join(Freelancer, Freelancer.id == FreelancerPerformance.freelancer_id).where(Freelancer.company_id == company_id))
    return {"total": total, "active": active, "active_assignments": assigned, "average_performance_score": round(float(avg), 2) if avg is not None else 0.0}


def _marketing(db: Session, company_id):
    campaigns = _count(db, MarketingCampaign, company_id)
    active = _count(db, MarketingCampaign, company_id, MarketingCampaign.status.in_({"active", "running"}))
    metrics = db.execute(select(func.coalesce(func.sum(CampaignMetric.impressions), 0), func.coalesce(func.sum(CampaignMetric.reach), 0), func.coalesce(func.sum(CampaignMetric.clicks), 0), func.coalesce(func.sum(CampaignMetric.leads), 0), func.coalesce(func.sum(CampaignMetric.conversions), 0), func.coalesce(func.sum(CampaignMetric.spend), 0), func.coalesce(func.sum(CampaignMetric.revenue), 0)).join(MarketingCampaign, MarketingCampaign.id == CampaignMetric.campaign_id).where(MarketingCampaign.company_id == company_id)).one()
    attributed = int(db.scalar(select(func.count()).select_from(CampaignProspect).join(MarketingCampaign, MarketingCampaign.id == CampaignProspect.campaign_id).where(MarketingCampaign.company_id == company_id)) or 0)
    impressions, reach, clicks, leads, conversions, spend, revenue = metrics
    return {"campaigns": campaigns, "active_campaigns": active, "impressions": int(impressions), "reach": int(reach), "clicks": int(clicks), "leads": int(leads), "conversions": int(conversions), "spend": float(spend), "revenue": float(revenue), "roas": round(float(revenue / spend), 2) if spend else 0.0, "attributed_prospects": attributed}


def _content(db: Session, company_id):
    assets = _count(db, ContentAsset, company_id)
    published = _count(db, ContentPublication, company_id, ContentPublication.status == "published")
    scheduled = _count(db, ContentPublication, company_id, ContentPublication.status == "planned")
    posts = _count(db, SocialPost, company_id, SocialPost.status == "published")
    social = db.execute(select(func.coalesce(func.sum(SocialPost.impressions), 0), func.coalesce(func.sum(SocialPost.reach), 0), func.coalesce(func.sum(SocialPost.likes), 0), func.coalesce(func.sum(SocialPost.comments), 0), func.coalesce(func.sum(SocialPost.shares), 0), func.coalesce(func.sum(SocialPost.saves), 0), func.coalesce(func.sum(SocialPost.clicks), 0), func.coalesce(func.sum(SocialPost.views), 0)).where(SocialPost.company_id == company_id)).one()
    impressions, reach, likes, comments, shares, saves, clicks, views = social
    engagement = int(likes + comments + shares + saves)
    return {"assets": assets, "published": published, "scheduled": scheduled, "published_social_posts": posts, "impressions": int(impressions), "reach": int(reach), "likes": int(likes), "comments": int(comments), "shares": int(shares), "saves": int(saves), "clicks": int(clicks), "views": int(views), "engagements": engagement, "engagement_rate": round((engagement / reach) * 100, 2) if reach else 0.0}


@router.get("/dashboard")
def dashboard(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    company_id = current_user.company_id
    sales = _sales(db, company_id)
    revenue = _revenue(db, company_id)
    projects = _projects(db, company_id)
    freelancers = _freelancers(db, company_id)
    marketing = _marketing(db, company_id)
    content = _content(db, company_id)
    now = datetime.now(timezone.utc)
    overdue_tasks = _count(db, Task, company_id, Task.due_at.is_not(None), Task.due_at < now, Task.status.notin_({"completed", "done", "cancelled"}))
    unread_notifications = _count(db, Notification, company_id, Notification.recipient_user_id == current_user.id, Notification.status == "unread")
    health = {"active_projects": projects["active"], "overdue_work": overdue_tasks + projects["overdue"], "open_risks": projects["open_risks"], "outstanding_payments": revenue["outstanding"], "unread_notifications": unread_notifications}
    return {"business_health": health, "sales": sales, "revenue": revenue, "projects": projects, "freelancers": freelancers, "marketing": marketing, "content": content}


@router.get("/sales")
def sales(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _sales(db, current_user.company_id)


@router.get("/revenue")
def revenue(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _revenue(db, current_user.company_id)


@router.get("/projects")
def projects(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _projects(db, current_user.company_id)


@router.get("/freelancers")
def freelancers(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _freelancers(db, current_user.company_id)


@router.get("/marketing")
def marketing(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _marketing(db, current_user.company_id)


@router.get("/content")
def content(current_user: User = Depends(require_permission(PERMISSION)), db: Session = Depends(get_db)):
    return _content(db, current_user.company_id)
