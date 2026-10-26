from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.calendar.models import CalendarEvent, CalendarReminder
from app.calendar.schemas import CalendarDashboard, CalendarEventCreate, CalendarEventResponse, CalendarEventUpdate, ReminderResponse
from app.clients.models import Client
from app.core.database import get_db
from app.freelancers.models import Freelancer
from app.projects.models import Project
from app.shared.models import AuditLog, Contact, Opportunity, Prospect, User
from app.tasks.models import Task

router = APIRouter(prefix="/calendar", tags=["calendar-scheduling"])


def _event(db: Session, company_id: UUID, event_id: UUID) -> CalendarEvent:
    obj = db.scalar(select(CalendarEvent).where(CalendarEvent.id == event_id, CalendarEvent.company_id == company_id))
    if obj is None:
        raise HTTPException(404, "Calendar event not found.")
    return obj


def _company_record(db: Session, model, company_id: UUID, item_id: UUID | None, label: str) -> None:
    if item_id is not None and db.scalar(select(model.id).where(model.id == item_id, model.company_id == company_id)) is None:
        raise HTTPException(400, f"Referenced {label} must exist in this company.")


def _validate_links(db: Session, company_id: UUID, values: dict) -> None:
    for key, model, label in [
        ("client_id", Client, "client"), ("contact_id", Contact, "contact"), ("prospect_id", Prospect, "prospect"),
        ("opportunity_id", Opportunity, "opportunity"), ("project_id", Project, "project"),
        ("freelancer_id", Freelancer, "freelancer"), ("task_id", Task, "task"), ("owner_user_id", User, "owner user"),
    ]:
        _company_record(db, model, company_id, values.get(key), label)
    if values.get("project_id") and values.get("client_id"):
        project = db.scalar(select(Project).where(Project.id == values["project_id"], Project.company_id == company_id))
        if project and project.client_id != values["client_id"]:
            raise HTTPException(400, "Project and client references do not match.")


def _validate_entity(db: Session, company_id: UUID, entity_type: str | None, entity_id: str | None) -> None:
    if entity_type is None and entity_id is None:
        return
    if entity_type is None or entity_id is None:
        raise HTTPException(400, "entity_type and entity_id must be provided together.")
    if entity_type == "company":
        from app.shared.models import Company
        try:
            entity_uuid = UUID(entity_id)
        except ValueError as exc:
            raise HTTPException(400, "Invalid company entity_id.") from exc
        exists = db.scalar(select(Company.id).where(Company.id == entity_uuid, Company.id == company_id))
    else:
        models = {"prospect": Prospect, "contact": Contact, "opportunity": Opportunity, "client": Client, "project": Project, "freelancer": Freelancer, "task": Task}
        model = models[entity_type]
        try:
            entity_uuid = UUID(entity_id)
        except ValueError as exc:
            raise HTTPException(400, "entity_id must be a UUID for linked business records.") from exc
        exists = db.scalar(select(model.id).where(model.id == entity_uuid, model.company_id == company_id))
    if exists is None:
        raise HTTPException(400, "Referenced entity does not exist in this company.")


def _reminders(db: Session, event_id: UUID) -> list[CalendarReminder]:
    return list(db.scalars(select(CalendarReminder).where(CalendarReminder.event_id == event_id).order_by(CalendarReminder.remind_at)).all())


def _response(db: Session, event: CalendarEvent) -> CalendarEventResponse:
    return CalendarEventResponse.model_validate({**event.__dict__, "reminders": _reminders(db, event.id)})


def _audit(db: Session, actor: User, action: str, event: CalendarEvent) -> None:
    db.add(AuditLog(actor_user_id=actor.id, action=action, entity_type="CalendarEvent", entity_id=str(event.id), details=event.title))


def _create_reminders(db: Session, event: CalendarEvent, reminders: list) -> None:
    for reminder in reminders:
        remind_at = event.start_at - timedelta(minutes=reminder.minutes_before)
        db.add(CalendarReminder(event_id=event.id, remind_at=remind_at, minutes_before=reminder.minutes_before))


@router.get("/dashboard", response_model=CalendarDashboard)
def dashboard(current_user: User = Depends(require_permission("calendar.dashboard.view")), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today_start + timedelta(days=1)
    base = CalendarEvent.company_id == current_user.company_id
    upcoming = db.scalar(select(func.count(CalendarEvent.id)).where(base, CalendarEvent.start_at >= now, CalendarEvent.status == "scheduled")) or 0
    today = db.scalar(select(func.count(CalendarEvent.id)).where(base, CalendarEvent.start_at >= today_start, CalendarEvent.start_at < tomorrow, CalendarEvent.status != "cancelled")) or 0
    overdue = db.scalar(select(func.count(CalendarEvent.id)).where(base, CalendarEvent.end_at < now, CalendarEvent.status == "scheduled")) or 0
    def count(kind: str) -> int:
        return db.scalar(select(func.count(CalendarEvent.id)).where(base, CalendarEvent.event_type == kind, CalendarEvent.status != "cancelled")) or 0
    return CalendarDashboard(total_upcoming=upcoming, today=today, discovery_calls=count("discovery_call"), client_meetings=count("client_meeting"), freelancer_meetings=count("freelancer_meeting"), deadlines=count("deadline"), content_schedule=count("content_schedule"), follow_ups=count("follow_up"), founder_reminders=count("founder_reminder"), overdue=overdue)


@router.get("/events", response_model=list[CalendarEventResponse])
def list_events(start_from: datetime | None = None, end_to: datetime | None = None, event_type: str | None = None, event_status: str | None = Query(default=None, alias="status"), owner_user_id: UUID | None = None, client_id: UUID | None = None, project_id: UUID | None = None, freelancer_id: UUID | None = None, limit: int = Query(default=200, ge=1, le=500), current_user: User = Depends(require_permission("calendar.events.view")), db: Session = Depends(get_db)):
    _validate_links(db, current_user.company_id, {"owner_user_id": owner_user_id, "client_id": client_id, "project_id": project_id, "freelancer_id": freelancer_id})
    query = select(CalendarEvent).where(CalendarEvent.company_id == current_user.company_id)
    if start_from: query = query.where(CalendarEvent.end_at >= start_from)
    if end_to: query = query.where(CalendarEvent.start_at <= end_to)
    if event_type: query = query.where(CalendarEvent.event_type == event_type)
    if event_status: query = query.where(CalendarEvent.status == event_status)
    if owner_user_id: query = query.where(CalendarEvent.owner_user_id == owner_user_id)
    if client_id: query = query.where(CalendarEvent.client_id == client_id)
    if project_id: query = query.where(CalendarEvent.project_id == project_id)
    if freelancer_id: query = query.where(CalendarEvent.freelancer_id == freelancer_id)
    events = db.scalars(query.order_by(CalendarEvent.start_at).limit(limit)).all()
    return [_response(db, event) for event in events]


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
def get_event(event_id: UUID, current_user: User = Depends(require_permission("calendar.events.view")), db: Session = Depends(get_db)):
    return _response(db, _event(db, current_user.company_id, event_id))


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: CalendarEventCreate, current_user: User = Depends(require_permission("calendar.events.create")), db: Session = Depends(get_db)):
    values = payload.model_dump(exclude={"reminders"})
    values["owner_user_id"] = values.get("owner_user_id") or current_user.id
    _validate_links(db, current_user.company_id, values)
    _validate_entity(db, current_user.company_id, values.get("entity_type"), values.get("entity_id"))
    event = CalendarEvent(company_id=current_user.company_id, **values)
    db.add(event)
    db.flush()
    _create_reminders(db, event, payload.reminders)
    _audit(db, current_user, "calendar.event.create", event)
    db.commit()
    db.refresh(event)
    return _response(db, event)


@router.patch("/events/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: UUID, payload: CalendarEventUpdate, current_user: User = Depends(require_permission("calendar.events.edit")), db: Session = Depends(get_db)):
    event = _event(db, current_user.company_id, event_id)
    values = payload.model_dump(exclude_unset=True)
    merged = {key: values.get(key, getattr(event, key)) for key in ["owner_user_id", "client_id", "contact_id", "prospect_id", "opportunity_id", "project_id", "freelancer_id", "task_id"]}
    _validate_links(db, current_user.company_id, merged)
    _validate_entity(db, current_user.company_id, values.get("entity_type", event.entity_type), values.get("entity_id", event.entity_id))
    start_at = values.get("start_at", event.start_at)
    end_at = values.get("end_at", event.end_at)
    if end_at <= start_at:
        raise HTTPException(400, "end_at must be after start_at")
    for key, value in values.items():
        setattr(event, key, value)
    _audit(db, current_user, "calendar.event.update", event)
    db.commit()
    db.refresh(event)
    return _response(db, event)


@router.post("/events/{event_id}/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def add_reminder(event_id: UUID, payload: object, current_user: User = Depends(require_permission("calendar.reminders.manage")), db: Session = Depends(get_db)):
    event = _event(db, current_user.company_id, event_id)
    minutes_before = getattr(payload, "minutes_before", None)
    if minutes_before is None:
        raise HTTPException(400, "minutes_before is required")
    reminder = CalendarReminder(event_id=event.id, remind_at=event.start_at - timedelta(minutes=minutes_before), minutes_before=minutes_before)
    db.add(reminder)
    db.add(AuditLog(actor_user_id=current_user.id, action="calendar.reminder.create", entity_type="CalendarReminder", entity_id=str(reminder.id), details=event.title))
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_event(event_id: UUID, current_user: User = Depends(require_permission("calendar.events.edit")), db: Session = Depends(get_db)):
    event = _event(db, current_user.company_id, event_id)
    event.status = "cancelled"
    _audit(db, current_user, "calendar.event.cancel", event)
    db.commit()
