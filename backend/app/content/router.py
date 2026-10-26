from collections import Counter
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.content.models import ContentAsset, ContentIdea, ContentProduction, ContentPublication
from app.content.schemas import *
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/content", tags=["content"])
IDEA_TRANSITIONS = {"idea": {"approved", "rejected", "archived"}, "approved": {"in_production", "rejected", "archived"}, "in_production": {"converted", "archived"}, "converted": {"archived"}, "rejected": {"idea", "archived"}, "archived": set()}
ASSET_TRANSITIONS = {"draft": {"in_review", "archived"}, "in_review": {"revision", "approved", "archived"}, "revision": {"in_review", "archived"}, "approved": {"archived"}, "archived": set()}
PRODUCTION_TRANSITIONS = {"planned": {"in_progress", "cancelled"}, "in_progress": {"review", "cancelled"}, "review": {"revision", "completed", "cancelled"}, "revision": {"in_progress", "review", "cancelled"}, "completed": set(), "cancelled": set()}
PUBLICATION_TRANSITIONS = {"planned": {"scheduled", "cancelled"}, "scheduled": {"published", "failed", "cancelled"}, "published": set(), "failed": {"scheduled", "cancelled"}, "cancelled": set()}

def _get(db, model, company_id, obj_id, label):
    obj = db.get(model, obj_id)
    if not obj or obj.company_id != company_id: raise HTTPException(404, f"{label} not found.")
    return obj

def _owner(db, company_id, user_id):
    if user_id is None: return
    user = db.get(User, user_id)
    if not user or user.company_id != company_id or not user.is_active: raise HTTPException(400, "Content owner must be an active user in the same company.")

def _audit(db, user, action, entity, obj, details=""):
    db.add(AuditLog(actor_user_id=user.id, action=action, entity_type=entity, entity_id=str(obj.id), details=details))

def _transition(current, new, mapping):
    if new != current and new not in mapping[current]: raise HTTPException(409, f"Invalid lifecycle transition: {current} -> {new}.")

@router.get("/dashboard", response_model=ContentDashboardResponse)
def dashboard(current_user: User = Depends(require_permission("content.dashboard.view")), db: Session = Depends(get_db)):
    cid = current_user.company_id
    ideas = list(db.scalars(select(ContentIdea).where(ContentIdea.company_id == cid)).all())
    assets = list(db.scalars(select(ContentAsset).where(ContentAsset.company_id == cid)).all())
    production = list(db.scalars(select(ContentProduction).where(ContentProduction.company_id == cid)).all())
    publications = list(db.scalars(select(ContentPublication).where(ContentPublication.company_id == cid).order_by(ContentPublication.created_at.desc())).all())
    now = datetime.now(timezone.utc)
    return ContentDashboardResponse(ideas=len(ideas), approved_ideas=sum(x.status == "approved" for x in ideas), in_production_ideas=sum(x.status == "in_production" for x in ideas), assets=len(assets), assets_in_review=sum(x.status == "in_review" for x in assets), approved_assets=sum(x.status == "approved" for x in assets), active_production=sum(x.status == "in_progress" for x in production), revision_production=sum(x.status == "revision" for x in production), scheduled_publications=sum(x.status == "scheduled" for x in publications), published_publications=sum(x.status == "published" for x in publications), overdue_production=sum(x.status not in {"completed", "cancelled"} and x.due_at is not None and x.due_at < now for x in production), by_content_type=dict(Counter(x.content_type for x in ideas)), by_asset_status=dict(Counter(x.status for x in assets)), by_platform=dict(Counter(x.platform for x in publications)), recent_publications=publications[:10])

@router.get("/ideas", response_model=list[IdeaResponse])
def list_ideas(current_user: User = Depends(require_permission("content.ideas.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(ContentIdea).where(ContentIdea.company_id == current_user.company_id).order_by(ContentIdea.created_at.desc())).all())

@router.post("/ideas", response_model=IdeaResponse, status_code=201)
def create_idea(p: IdeaCreate, current_user: User = Depends(require_permission("content.ideas.create")), db: Session = Depends(get_db)):
    _owner(db, current_user.company_id, p.owner_user_id)
    obj = ContentIdea(company_id=current_user.company_id, **p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"content.idea.create","ContentIdea",obj,obj.title); db.commit(); db.refresh(obj); return obj

@router.patch("/ideas/{idea_id}", response_model=IdeaResponse)
def update_idea(idea_id: UUID, p: IdeaUpdate, current_user: User = Depends(require_permission("content.ideas.edit")), db: Session = Depends(get_db)):
    obj = _get(db, ContentIdea, current_user.company_id, idea_id, "Content idea"); changes=p.model_dump(exclude_unset=True)
    if "status" in changes: _transition(obj.status, changes["status"], IDEA_TRANSITIONS)
    if "content_type" in changes and changes["content_type"] not in CONTENT_TYPES: raise HTTPException(400,"Invalid content type.")
    if "priority" in changes and changes["priority"] not in PRIORITIES: raise HTTPException(400,"Invalid priority.")
    if "owner_user_id" in changes: _owner(db,current_user.company_id,changes["owner_user_id"])
    for k,v in changes.items(): setattr(obj,k,v)
    _audit(db,current_user,"content.idea.update","ContentIdea",obj); db.commit(); db.refresh(obj); return obj

@router.get("/assets", response_model=list[AssetResponse])
def list_assets(current_user: User = Depends(require_permission("content.assets.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(ContentAsset).where(ContentAsset.company_id == current_user.company_id).order_by(ContentAsset.created_at.desc())).all())

@router.post("/assets", response_model=AssetResponse, status_code=201)
def create_asset(p: AssetCreate, current_user: User = Depends(require_permission("content.assets.create")), db: Session = Depends(get_db)):
    if p.idea_id: _get(db,ContentIdea,current_user.company_id,p.idea_id,"Content idea")
    _owner(db,current_user.company_id,p.owner_user_id)
    obj=ContentAsset(company_id=current_user.company_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"content.asset.create","ContentAsset",obj,obj.title); db.commit(); db.refresh(obj); return obj

@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: UUID,p: AssetUpdate,current_user: User=Depends(require_permission("content.assets.edit")),db: Session=Depends(get_db)):
    obj=_get(db,ContentAsset,current_user.company_id,asset_id,"Content asset"); changes=p.model_dump(exclude_unset=True)
    if "status" in changes: _transition(obj.status,changes["status"],ASSET_TRANSITIONS)
    if "owner_user_id" in changes: _owner(db,current_user.company_id,changes["owner_user_id"])
    for k,v in changes.items(): setattr(obj,k,v)
    _audit(db,current_user,"content.asset.update","ContentAsset",obj); db.commit(); db.refresh(obj); return obj

@router.get("/production", response_model=list[ProductionResponse])
def list_production(current_user: User=Depends(require_permission("content.production.view")),db: Session=Depends(get_db)):
    return list(db.scalars(select(ContentProduction).where(ContentProduction.company_id==current_user.company_id).order_by(ContentProduction.created_at.desc())).all())

@router.post("/production", response_model=ProductionResponse,status_code=201)
def create_production(p:ProductionCreate,current_user:User=Depends(require_permission("content.production.create")),db:Session=Depends(get_db)):
    if p.idea_id: _get(db,ContentIdea,current_user.company_id,p.idea_id,"Content idea")
    if p.asset_id: _get(db,ContentAsset,current_user.company_id,p.asset_id,"Content asset")
    _owner(db,current_user.company_id,p.producer_user_id)
    if p.status not in PRODUCTION_STATUSES: raise HTTPException(400,"Invalid production status.")
    if p.status != "planned": raise HTTPException(400,"Production must start in planned status.")
    obj=ContentProduction(company_id=current_user.company_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"content.production.create","ContentProduction",obj); db.commit(); db.refresh(obj); return obj

@router.patch("/production/{production_id}",response_model=ProductionResponse)
def update_production(production_id:UUID,p:ProductionUpdate,current_user:User=Depends(require_permission("content.production.edit")),db:Session=Depends(get_db)):
    obj=_get(db,ContentProduction,current_user.company_id,production_id,"Content production"); changes=p.model_dump(exclude_unset=True); new_status=changes.get("status",obj.status); _transition(obj.status,new_status,PRODUCTION_TRANSITIONS)
    if "asset_id" in changes and changes["asset_id"]: _get(db,ContentAsset,current_user.company_id,changes["asset_id"],"Content asset")
    if "producer_user_id" in changes: _owner(db,current_user.company_id,changes["producer_user_id"])
    if new_status in {"review","completed"} and not (changes.get("asset_id",obj.asset_id)): raise HTTPException(400,"Production must have an asset before review/completion.")
    for k,v in changes.items(): setattr(obj,k,v)
    if obj.status=="in_progress" and obj.started_at is None: obj.started_at=datetime.now(timezone.utc)
    if obj.status=="revision": obj.revision_count += 1
    if obj.status=="completed" and obj.completed_at is None: obj.completed_at=datetime.now(timezone.utc)
    _audit(db,current_user,"content.production.update","ContentProduction",obj); db.commit(); db.refresh(obj); return obj

@router.get("/publications",response_model=list[PublicationResponse])
def list_publications(current_user:User=Depends(require_permission("content.publications.view")),db:Session=Depends(get_db)):
    return list(db.scalars(select(ContentPublication).where(ContentPublication.company_id==current_user.company_id).order_by(ContentPublication.scheduled_at.desc().nullslast(),ContentPublication.created_at.desc())).all())

@router.post("/publications",response_model=PublicationResponse,status_code=201)
def create_publication(p:PublicationCreate,current_user:User=Depends(require_permission("content.publications.create")),db:Session=Depends(get_db)):
    asset=_get(db,ContentAsset,current_user.company_id,p.asset_id,"Content asset")
    if asset.status != "approved": raise HTTPException(409,"Only approved content assets can be scheduled for publication.")
    if db.scalar(select(ContentPublication).where(ContentPublication.asset_id==asset.id,ContentPublication.platform==p.platform)): raise HTTPException(409,"This asset is already scheduled for that platform.")
    if p.status not in {"planned","scheduled"}: raise HTTPException(400,"Publication must start as planned or scheduled.")
    if p.status=="scheduled" and p.scheduled_at is None: raise HTTPException(400,"Scheduled publication requires scheduled_at.")
    obj=ContentPublication(company_id=current_user.company_id,**p.model_dump()); db.add(obj); db.flush(); _audit(db,current_user,"content.publication.create","ContentPublication",obj); db.commit(); db.refresh(obj); return obj

@router.patch("/publications/{publication_id}",response_model=PublicationResponse)
def update_publication(publication_id:UUID,p:PublicationUpdate,current_user:User=Depends(require_permission("content.publications.edit")),db:Session=Depends(get_db)):
    obj=_get(db,ContentPublication,current_user.company_id,publication_id,"Content publication"); changes=p.model_dump(exclude_unset=True)
    new_status=changes.get("status",obj.status); _transition(obj.status,new_status,PUBLICATION_TRANSITIONS)
    if new_status=="scheduled" and not changes.get("scheduled_at",obj.scheduled_at): raise HTTPException(400,"Scheduled publication requires scheduled_at.")
    if new_status=="published" and not changes.get("published_at",obj.published_at): changes["published_at"]=datetime.now(timezone.utc)
    for k,v in changes.items(): setattr(obj,k,v)
    _audit(db,current_user,"content.publication.update","ContentPublication",obj); db.commit(); db.refresh(obj); return obj
