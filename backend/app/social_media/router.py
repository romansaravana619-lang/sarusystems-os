from collections import Counter
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.shared.models import AuditLog, User
from app.social_media.models import SocialPost
from app.social_media.schemas import SocialDashboard, SocialPerformanceUpdate, SocialPostCreate, SocialPostResponse, SocialPostUpdate, TRANSITIONS
from app.content.models import ContentAsset
from app.marketing.models import MarketingCampaign

router = APIRouter(prefix="/social-media", tags=["social-media"])


def _get(db: Session, company_id: UUID, post_id: UUID) -> SocialPost:
    obj = db.get(SocialPost, post_id)
    if not obj or obj.company_id != company_id:
        raise HTTPException(404, "Social post not found.")
    return obj


def _validate_links(db: Session, company_id: UUID, content_asset_id: UUID | None, campaign_id: UUID | None) -> None:
    if content_asset_id is not None:
        asset = db.get(ContentAsset, content_asset_id)
        if not asset or asset.company_id != company_id:
            raise HTTPException(400, "Content asset not found in this company.")
    if campaign_id is not None:
        campaign = db.get(MarketingCampaign, campaign_id)
        if not campaign or campaign.company_id != company_id:
            raise HTTPException(400, "Marketing campaign not found in this company.")


def _audit(db: Session, user: User, action: str, obj: SocialPost) -> None:
    db.add(AuditLog(actor_user_id=user.id, action=action, entity_type="SocialPost", entity_id=str(obj.id), details=obj.post_id))


@router.get("/dashboard", response_model=SocialDashboard)
def dashboard(current_user: User = Depends(require_permission("social_media.dashboard.view")), db: Session = Depends(get_db)):
    posts = list(db.scalars(select(SocialPost).where(SocialPost.company_id == current_user.company_id).order_by(SocialPost.created_at.desc())).all())
    performance = {k: sum(getattr(p, k) for p in posts) for k in ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views")}
    return SocialDashboard(total_posts=len(posts), drafts=sum(p.status == "draft" for p in posts), ready=sum(p.status == "ready" for p in posts), scheduled=sum(p.status == "scheduled" for p in posts), published=sum(p.status == "published" for p in posts), by_platform=dict(Counter(p.platform for p in posts)), performance=performance, recent_posts=posts[:10])


@router.get("/posts", response_model=list[SocialPostResponse])
def list_posts(current_user: User = Depends(require_permission("social_media.posts.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(SocialPost).where(SocialPost.company_id == current_user.company_id).order_by(SocialPost.post_date.desc().nullslast(), SocialPost.created_at.desc())).all())


@router.post("/posts", response_model=SocialPostResponse, status_code=201)
def create_post(p: SocialPostCreate, current_user: User = Depends(require_permission("social_media.posts.create")), db: Session = Depends(get_db)):
    if db.scalar(select(SocialPost).where(SocialPost.company_id == current_user.company_id, SocialPost.platform == p.platform, SocialPost.post_id == p.post_id)):
        raise HTTPException(409, "A post with this platform and Post ID already exists.")
    _validate_links(db, current_user.company_id, p.content_asset_id, p.campaign_id)
    if p.status == "scheduled" and not p.post_date:
        raise HTTPException(400, "Scheduled posts require a publishing date.")
    if p.status == "published":
        raise HTTPException(409, "Create posts as draft or ready; use the publishing workflow to mark a post published.")
    obj = SocialPost(company_id=current_user.company_id, **p.model_dump())
    db.add(obj); db.flush(); _audit(db, current_user, "social_media.post.create", obj); db.commit(); db.refresh(obj)
    return obj


@router.patch("/posts/{post_id}", response_model=SocialPostResponse)
def update_post(post_id: UUID, p: SocialPostUpdate, current_user: User = Depends(require_permission("social_media.posts.edit")), db: Session = Depends(get_db)):
    obj = _get(db, current_user.company_id, post_id)
    changes = p.model_dump(exclude_unset=True)
    new_status = changes.get("status", obj.status)
    if new_status != obj.status and new_status not in TRANSITIONS[obj.status]:
        raise HTTPException(409, f"Invalid social post transition: {obj.status} -> {new_status}.")
    if new_status == "scheduled":
        post_date = changes.get("post_date", obj.post_date)
        if not post_date:
            raise HTTPException(400, "Scheduled posts require a publishing date.")
        if post_date <= datetime.now(timezone.utc):
            raise HTTPException(400, "Publishing date must be in the future.")
    if new_status == "published":
        if not (obj.post_content or obj.creative_url or changes.get("post_content") or changes.get("creative_url")):
            raise HTTPException(400, "Published posts require content or a creative.")
        if not changes.get("published_at"):
            changes["published_at"] = datetime.now(timezone.utc)
    if "content_asset_id" in changes or "campaign_id" in changes:
        _validate_links(db, current_user.company_id, changes.get("content_asset_id", obj.content_asset_id), changes.get("campaign_id", obj.campaign_id))
    for k, v in changes.items():
        setattr(obj, k, v)
    _audit(db, current_user, "social_media.post.update", obj); db.commit(); db.refresh(obj)
    return obj


@router.patch("/posts/{post_id}/performance", response_model=SocialPostResponse)
def update_performance(post_id: UUID, p: SocialPerformanceUpdate, current_user: User = Depends(require_permission("social_media.posts.edit")), db: Session = Depends(get_db)):
    obj = _get(db, current_user.company_id, post_id)
    if obj.status != "published":
        raise HTTPException(409, "Performance can only be recorded for published posts.")
    for k, v in p.model_dump().items():
        setattr(obj, k, v)
    _audit(db, current_user, "social_media.post.performance.update", obj); db.commit(); db.refresh(obj)
    return obj
