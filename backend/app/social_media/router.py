from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.content.models import ContentAsset, ContentPublication
from app.core.database import get_db
from app.marketing.models import MarketingCampaign
from app.shared.models import AuditLog, User
from app.social_media.models import SocialPost
from app.social_media.schemas import (
    SocialDashboard,
    SocialPerformanceUpdate,
    SocialPostCreate,
    SocialPostResponse,
    SocialPostUpdate,
    TRANSITIONS,
)

router = APIRouter(prefix="/social-media", tags=["social-media"])


def _get(db: Session, company_id: UUID, post_id: UUID) -> SocialPost:
    obj = db.scalar(
        select(SocialPost).where(
            SocialPost.id == post_id,
            SocialPost.company_id == company_id,
        )
    )
    if not obj:
        raise HTTPException(404, "Social post not found.")
    return obj


def _validate_links(
    db: Session,
    company_id: UUID,
    content_asset_id: UUID | None,
    campaign_id: UUID | None,
    platform: str,
    new_status: str | None = None,
) -> ContentAsset | None:
    asset = None
    if content_asset_id is not None:
        asset = db.scalar(
            select(ContentAsset).where(
                ContentAsset.id == content_asset_id,
                ContentAsset.company_id == company_id,
            )
        )
        if not asset:
            raise HTTPException(400, "Content asset not found in this company.")
        if new_status in {"scheduled", "published"}:
            if asset.status != "approved" or asset.brand_qa_status not in {"passed", "not_required"}:
                raise HTTPException(
                    409,
                    "Linked content must be approved and pass brand QA before scheduling or publication.",
                )
    if campaign_id is not None and db.scalar(
        select(MarketingCampaign.id).where(
            MarketingCampaign.id == campaign_id,
            MarketingCampaign.company_id == company_id,
        )
    ) is None:
        raise HTTPException(400, "Marketing campaign not found in this company.")
    return asset


def _audit(db: Session, user: User, action: str, obj: SocialPost) -> None:
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action=action,
            entity_type="SocialPost",
            entity_id=str(obj.id),
            details=obj.post_id,
        )
    )


def _publication_for_post(db: Session, post: SocialPost) -> ContentPublication | None:
    if post.content_asset_id is None:
        return None
    return db.scalar(
        select(ContentPublication).where(
            ContentPublication.company_id == post.company_id,
            ContentPublication.asset_id == post.content_asset_id,
            ContentPublication.platform == post.platform,
        )
    )


def _sync_publication(
    db: Session,
    user: User,
    post: SocialPost,
    status: str,
    post_date: datetime | None = None,
    published_at: datetime | None = None,
) -> None:
    if post.content_asset_id is None:
        return
    publication = _publication_for_post(db, post)
    if status == "scheduled":
        if not publication:
            publication = ContentPublication(
                company_id=post.company_id,
                asset_id=post.content_asset_id,
                platform=post.platform,
                status="planned",
                notes=f"Managed from Social Media post {post.post_id}",
            )
            db.add(publication)
            db.flush()
        publication.status = "scheduled"
        publication.scheduled_at = post_date
    elif status == "ready" and publication and publication.status in {"planned", "scheduled", "failed"}:
        publication.status = "planned"
        publication.scheduled_at = None
    elif status == "published":
        if not publication:
            publication = ContentPublication(
                company_id=post.company_id,
                asset_id=post.content_asset_id,
                platform=post.platform,
                status="planned",
                notes=f"Managed from Social Media post {post.post_id}",
            )
            db.add(publication)
            db.flush()
        publication.status = "published"
        publication.published_at = published_at or datetime.now(timezone.utc)
    elif status == "scheduled" and publication:
        publication.scheduled_at = post_date
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="content.publication.synced_from_social_media",
            entity_type="ContentPublication",
            entity_id=str(publication.id) if publication else None,
            details=f"SocialPost {post.id} -> {status}",
        )
    )


@router.get("/dashboard", response_model=SocialDashboard)
def dashboard(
    current_user: User = Depends(require_permission("social_media.dashboard.view")),
    db: Session = Depends(get_db),
):
    posts = list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.company_id == current_user.company_id)
            .order_by(SocialPost.created_at.desc())
        ).all()
    )
    performance = {
        key: sum(getattr(post, key) for post in posts)
        for key in ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views")
    }
    return SocialDashboard(
        total_posts=len(posts),
        drafts=sum(post.status == "draft" for post in posts),
        ready=sum(post.status == "ready" for post in posts),
        scheduled=sum(post.status == "scheduled" for post in posts),
        published=sum(post.status == "published" for post in posts),
        by_platform=dict(Counter(post.platform for post in posts)),
        performance=performance,
        recent_posts=posts[:10],
    )


@router.get("/posts", response_model=list[SocialPostResponse])
def list_posts(
    current_user: User = Depends(require_permission("social_media.posts.view")),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(SocialPost)
            .where(SocialPost.company_id == current_user.company_id)
            .order_by(SocialPost.post_date.desc().nullslast(), SocialPost.created_at.desc())
        ).all()
    )


@router.post("/posts", response_model=SocialPostResponse, status_code=201)
def create_post(
    p: SocialPostCreate,
    current_user: User = Depends(require_permission("social_media.posts.create")),
    db: Session = Depends(get_db),
):
    duplicate = db.scalar(
        select(SocialPost.id).where(
            SocialPost.company_id == current_user.company_id,
            SocialPost.platform == p.platform,
            SocialPost.post_id == p.post_id,
        )
    )
    if duplicate:
        raise HTTPException(409, "A post with this platform and Post ID already exists.")
    _validate_links(
        db,
        current_user.company_id,
        p.content_asset_id,
        p.campaign_id,
        p.platform,
        p.status,
    )
    if p.status == "scheduled":
        if not p.post_date:
            raise HTTPException(400, "Scheduled posts require a publishing date.")
        if p.post_date <= datetime.now(timezone.utc):
            raise HTTPException(400, "Publishing date must be in the future.")
    if p.status == "published":
        raise HTTPException(
            409,
            "Create posts as draft or ready; use the publishing workflow to mark a post published.",
        )
    obj = SocialPost(company_id=current_user.company_id, **p.model_dump())
    db.add(obj)
    db.flush()
    _audit(db, current_user, "social_media.post.create", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/posts/{post_id}", response_model=SocialPostResponse)
def update_post(
    post_id: UUID,
    p: SocialPostUpdate,
    current_user: User = Depends(require_permission("social_media.posts.edit")),
    db: Session = Depends(get_db),
):
    obj = _get(db, current_user.company_id, post_id)
    changes = p.model_dump(exclude_unset=True)
    new_status = changes.get("status", obj.status)
    if new_status != obj.status and new_status not in TRANSITIONS[obj.status]:
        raise HTTPException(409, f"Invalid social post transition: {obj.status} -> {new_status}.")
    post_date = changes.get("post_date", obj.post_date)
    if new_status == "scheduled":
        if not post_date:
            raise HTTPException(400, "Scheduled posts require a publishing date.")
        if post_date <= datetime.now(timezone.utc):
            raise HTTPException(400, "Publishing date must be in the future.")
    if new_status == "published":
        if not (
            obj.post_content
            or obj.creative_url
            or changes.get("post_content")
            or changes.get("creative_url")
        ):
            raise HTTPException(400, "Published posts require content or a creative.")
        changes["published_at"] = datetime.now(timezone.utc)
    content_asset_id = changes.get("content_asset_id", obj.content_asset_id)
    campaign_id = changes.get("campaign_id", obj.campaign_id)
    _validate_links(
        db,
        current_user.company_id,
        content_asset_id,
        campaign_id,
        obj.platform,
        new_status,
    )
    for key, value in changes.items():
        setattr(obj, key, value)
    db.flush()
    if new_status in {"scheduled", "published"} and new_status != obj.status:
        _sync_publication(db, current_user, obj, new_status, post_date, obj.published_at)
    elif new_status == "scheduled":
        _sync_publication(db, current_user, obj, new_status, post_date, obj.published_at)
    elif new_status == "ready" and "status" in changes:
        _sync_publication(db, current_user, obj, new_status, post_date, obj.published_at)
    _audit(db, current_user, "social_media.post.update", obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/posts/{post_id}/performance", response_model=SocialPostResponse)
def update_performance(
    post_id: UUID,
    p: SocialPerformanceUpdate,
    current_user: User = Depends(require_permission("social_media.posts.edit")),
    db: Session = Depends(get_db),
):
    obj = _get(db, current_user.company_id, post_id)
    if obj.status != "published":
        raise HTTPException(409, "Performance can only be recorded for published posts.")
    for key, value in p.model_dump().items():
        setattr(obj, key, value)
    _audit(db, current_user, "social_media.post.performance.update", obj)
    db.commit()
    db.refresh(obj)
    return obj
