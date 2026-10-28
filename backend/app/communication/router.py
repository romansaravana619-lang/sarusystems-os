from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.clients.models import Client
from app.communication.models import ActivityRecord
from app.communication.schemas import ActivityCreate, ActivityDashboard, ActivityResponse, ActivityUpdate
from app.core.database import get_db
from app.freelancers.models import Freelancer
from app.projects.models import Project
from app.shared.models import AuditLog, Contact, Opportunity, Prospect, User

router = APIRouter(prefix="/communication", tags=["communication-activity-history"])


def _record(db: Session, company_id: UUID, activity_id: UUID) -> ActivityRecord:
    obj = db.scalar(select(ActivityRecord).where(ActivityRecord.id == activity_id, ActivityRecord.company_id == company_id))
    if obj is None:
        raise HTTPException(404, "Activity record not found.")
    return obj


def _company_record(db: Session, model, company_id: UUID, item_id: UUID | None, label: str) -> None:
    if item_id is None:
        return
    if db.scalar(select(model.id).where(model.id == item_id, model.company_id == company_id)) is None:
        raise HTTPException(400, f"Referenced {label} must exist in this company.")


def _validate_links(db: Session, company_id: UUID, values: dict) -> None:
    _company_record(db, Client, company_id, values.get("client_id"), "client")
    _company_record(db, Contact, company_id, values.get("contact_id"), "contact")
    _company_record(db, Prospect, company_id, values.get("prospect_id"), "prospect")
    _company_record(db, Opportunity, company_id, values.get("opportunity_id"), "opportunity")
    _company_record(db, Project, company_id, values.get("project_id"), "project")
    _company_record(db, Freelancer, company_id, values.get("freelancer_id"), "freelancer")
    actor_id = values.get("actor_user_id")
    _company_record(db, User, company_id, actor_id, "actor user")

    project_id = values.get("project_id")
    client_id = values.get("client_id")
    if project_id and client_id:
        project = db.scalar(select(Project).where(Project.id == project_id, Project.company_id == company_id))
        if project and project.client_id != client_id:
            raise HTTPException(400, "Project and client references do not match.")


def _validate_entity(db: Session, company_id: UUID, entity_type: str | None, entity_id: str | None) -> None:
    if entity_type is None and entity_id is None:
        return
    if entity_type is None or entity_id is None:
        raise HTTPException(400, "entity_type and entity_id must be provided together.")
    if entity_type == "company":
        try:
            entity_uuid = UUID(entity_id)
        except ValueError as exc:
            raise HTTPException(400, "Invalid company entity_id.") from exc
        from app.shared.models import Company
        exists = db.scalar(select(Company.id).where(Company.id == entity_uuid, Company.id == company_id))
    else:
        model_map = {"prospect": Prospect, "contact": Contact, "opportunity": Opportunity, "client": Client, "project": Project, "freelancer": Freelancer}
        model = model_map[entity_type]
        try:
            entity_uuid = UUID(entity_id)
        except ValueError as exc:
            raise HTTPException(400, "entity_id must be a UUID for linked business records.") from exc
        exists = db.scalar(select(model.id).where(model.id == entity_uuid, model.company_id == company_id))
    if exists is None:
        raise HTTPException(400, "Referenced entity does not exist in this company.")


def _audit(db: Session, actor: User, action: str, obj: ActivityRecord) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type="ActivityRecord", entity_id=str(obj.id), details=obj.activity_type))


@router.get("/dashboard", response_model=ActivityDashboard)
def dashboard(current_user: User = Depends(require_permission("communication.dashboard.view")), db: Session = Depends(get_db)):
    base = ActivityRecord.company_id == current_user.company_id
    def count(activity_type: str) -> int:
        return db.scalar(select(func.count(ActivityRecord.id)).where(base, ActivityRecord.activity_type == activity_type)) or 0
    return ActivityDashboard(total=db.scalar(select(func.count(ActivityRecord.id)).where(base)) or 0, emails=count("email"), calls=count("call"), meetings=count("meeting"), client_notes=count("client_note"), internal_notes=count("internal_note"), interactions=count("interaction"))


@router.get("/activities", response_model=list[ActivityResponse])
def list_activities(
    activity_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    client_id: UUID | None = None,
    project_id: UUID | None = None,
    freelancer_id: UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    current_user: User = Depends(require_permission("communication.activities.view")),
    db: Session = Depends(get_db),
):
    values = {"client_id": client_id, "project_id": project_id, "freelancer_id": freelancer_id}
    _validate_links(db, current_user.company_id, values)
    _validate_entity(db, current_user.company_id, entity_type, entity_id)
    query = select(ActivityRecord).where(ActivityRecord.company_id == current_user.company_id)
    if activity_type: query = query.where(ActivityRecord.activity_type == activity_type)
    if entity_type: query = query.where(ActivityRecord.entity_type == entity_type)
    if entity_id: query = query.where(ActivityRecord.entity_id == entity_id)
    if client_id: query = query.where(ActivityRecord.client_id == client_id)
    if project_id: query = query.where(ActivityRecord.project_id == project_id)
    if freelancer_id: query = query.where(ActivityRecord.freelancer_id == freelancer_id)
    if occurred_from: query = query.where(ActivityRecord.occurred_at >= occurred_from)
    if occurred_to: query = query.where(ActivityRecord.occurred_at <= occurred_to)
    return list(db.scalars(query.order_by(ActivityRecord.occurred_at.desc()).limit(limit)).all())


@router.get("/activities/{entity_type}/{entity_id}", response_model=list[ActivityResponse])
def entity_history(entity_type: str, entity_id: str, limit: int = Query(default=100, ge=1, le=250), current_user: User = Depends(require_permission("communication.activities.view")), db: Session = Depends(get_db)):
    _validate_entity(db, current_user.company_id, entity_type, entity_id)
    return list(db.scalars(select(ActivityRecord).where(ActivityRecord.company_id == current_user.company_id, ActivityRecord.entity_type == entity_type, ActivityRecord.entity_id == entity_id).order_by(ActivityRecord.occurred_at.desc()).limit(limit)).all())


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreate, current_user: User = Depends(require_permission("communication.activities.create")), db: Session = Depends(get_db)):
    values = payload.model_dump()
    values["actor_user_id"] = values.get("actor_user_id") or current_user.id
    _validate_links(db, current_user.company_id, values)
    _validate_entity(db, current_user.company_id, values.get("entity_type"), values.get("entity_id"))
    obj = ActivityRecord(company_id=current_user.company_id, **values)
    db.add(obj); db.flush(); _audit(db, current_user, "communication.activity.create", obj); db.commit(); db.refresh(obj)
    return obj


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id: UUID, payload: ActivityUpdate, current_user: User = Depends(require_permission("communication.activities.edit")), db: Session = Depends(get_db)):
    obj = _record(db, current_user.company_id, activity_id)
    values = payload.model_dump(exclude_unset=True)
    merged = {key: values.get(key, getattr(obj, key)) for key in ["client_id", "contact_id", "prospect_id", "opportunity_id", "project_id", "freelancer_id", "actor_user_id"]}
    _validate_links(db, current_user.company_id, merged)
    _validate_entity(db, current_user.company_id, values.get("entity_type", obj.entity_type), values.get("entity_id", obj.entity_id))
    for key, value in values.items(): setattr(obj, key, value)
    _audit(db, current_user, "communication.activity.update", obj); db.commit(); db.refresh(obj)
    return obj
