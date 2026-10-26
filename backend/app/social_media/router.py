from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.shared.models import AuditLog, User
from app.social_media.models import SocialPost
from app.social_media.schemas import *

router = APIRouter(prefix="/social-media", tags=["social-media"])

def _get(db, company_id, post_id):
    obj = db.get(SocialPost, post_id)
    if not obj or obj.company_id != company_id: raise HTTPException(404, "Social post not found.")
    return obj

def _audit(db, user, action, obj):
    db.add(AuditLog(actor_user_id=user.id, action=action, entity_type="SocialPost", entity_id=str(obj.id), details=obj.post_id))

@router.get("/dashboard", response_model=SocialDashboard)
def dashboard(current_user: User = Depends(require_permission("social_media.dashboard.view")), db: Session = Depends(get_db)):
    posts = list(db.scalars(select(SocialPost).where(SocialPost.company_id == current_user.company_id).order_by(SocialPost.created_at.desc())).all())
    return SocialDashboard(total_posts=len(posts), drafts=sum(p.status == "draft" for p in posts), ready=sum(p.status == "ready" for p in posts), scheduled=sum(p.status == "scheduled" for p in posts), published=sum(p.status == "published" for p in posts), by_platform=dict(Counter(p.platform for p in posts)), recent_posts=posts[:10])

@router.get("/posts", response_model=list[SocialPostResponse])
def list_posts(current_user: User = Depends(require_permission("social_media.posts.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(SocialPost).where(SocialPost.company_id == current_user.company_id).order_by(SocialPost.post_date.desc().nullslast(), SocialPost.created_at.desc())).all())

@router.post("/posts", response_model=SocialPostResponse, status_code=201)
def create_post(p: SocialPostCreate, current_user: User = Depends(require_permission("social_media.posts.create")), db: Session = Depends(get_db)):
    if db.scalar(select(SocialPost).where(SocialPost.company_id == current_user.company_id, SocialPost.platform == p.platform, SocialPost.post_id == p.post_id)):
        raise HTTPException(409, "A post with this platform and Post ID already exists.")
    obj = SocialPost(company_id=current_user.company_id, **p.model_dump()); db.add(obj); db.flush(); _audit(db, current_user, "social_media.post.create", obj); db.commit(); db.refresh(obj); return obj

@router.patch("/posts/{post_id}", response_model=SocialPostResponse)
def update_post(post_id: UUID, p: SocialPostUpdate, current_user: User = Depends(require_permission("social_media.posts.edit")), db: Session = Depends(get_db)):
    obj = _get(db, current_user.company_id, post_id); changes = p.model_dump(exclude_unset=True); new_status = changes.get("status", obj.status)
    if new_status != obj.status and new_status not in TRANSITIONS[obj.status]: raise HTTPException(409, f"Invalid social post transition: {obj.status} -> {new_status}.")
    if new_status == "scheduled" and not changes.get("post_date", obj.post_date): raise HTTPException(400, "Scheduled posts require a post date.")
    if new_status == "published" and not (changes.get("post_content", obj.post_content) or changes.get("creative_url", obj.creative_url)): raise HTTPException(400, "Published posts require content or a creative.")
    for k, v in changes.items(): setattr(obj, k, v)
    _audit(db, current_user, "social_media.post.update", obj); db.commit(); db.refresh(obj); return obj
