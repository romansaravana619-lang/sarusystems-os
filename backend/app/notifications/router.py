from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.notifications.models import Notification, NotificationPreference
from app.notifications.schemas import NotificationCreate, NotificationDashboard, NotificationResponse, PreferenceResponse, PreferenceUpsert
from app.shared.models import AuditLog, User

router = APIRouter(prefix="/notifications", tags=["notification-engine"])


def _notification(db: Session, company_id: UUID, notification_id: UUID) -> Notification:
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.company_id == company_id))
    if item is None: raise HTTPException(404, "Notification not found.")
    return item


def _preference_enabled(db: Session, company_id: UUID, user_id: UUID, notification_type: str, channel: str) -> bool:
    pref = db.scalar(select(NotificationPreference).where(NotificationPreference.company_id == company_id, NotificationPreference.user_id == user_id, NotificationPreference.notification_type == notification_type, NotificationPreference.channel == channel))
    return pref.enabled if pref else True

@router.get("/dashboard", response_model=NotificationDashboard)
def dashboard(current_user: User = Depends(require_permission("notifications.dashboard.view")), db: Session = Depends(get_db)):
    base = Notification.company_id == current_user.company_id
    own = Notification.recipient_user_id == current_user.id
    def count(*conditions): return db.scalar(select(func.count(Notification.id)).where(base, own, *conditions)) or 0
    return NotificationDashboard(unread=count(Notification.status == "unread"), high_priority=count(Notification.priority.in_(["high", "urgent"])), scheduled=count(Notification.scheduled_for.is_not(None), Notification.status == "pending"), failed=count(Notification.status == "failed"), total=count())

@router.get("", response_model=list[NotificationResponse])
def list_notifications(unread_only: bool = False, notification_type: str | None = None, priority: str | None = None, limit: int = Query(default=100, ge=1, le=500), current_user: User = Depends(require_permission("notifications.view")), db: Session = Depends(get_db)):
    query = select(Notification).where(Notification.company_id == current_user.company_id, Notification.recipient_user_id == current_user.id)
    if unread_only: query = query.where(Notification.status == "unread")
    if notification_type: query = query.where(Notification.notification_type == notification_type)
    if priority: query = query.where(Notification.priority == priority)
    return list(db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)).all())

@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, current_user: User = Depends(require_permission("notifications.create")), db: Session = Depends(get_db)):
    recipient = db.scalar(select(User).where(User.id == payload.recipient_user_id, User.company_id == current_user.company_id))
    if recipient is None: raise HTTPException(400, "Recipient must belong to this company.")
    enabled = _preference_enabled(db, current_user.company_id, recipient.id, payload.notification_type, payload.channel)
    if not enabled: raise HTTPException(409, "Notification channel is disabled for this recipient and notification type.")
    scheduled = payload.scheduled_for
    now = datetime.now(timezone.utc)
    item = Notification(company_id=current_user.company_id, recipient_user_id=recipient.id, notification_type=payload.notification_type, channel=payload.channel, priority=payload.priority, title=payload.title, message=payload.message, scheduled_for=scheduled, status="pending" if scheduled and scheduled > now else ("sent" if payload.channel == "email" else "unread"), sent_at=None if scheduled and scheduled > now else now, source_type=payload.source_type, source_id=payload.source_id, action_url=payload.action_url, payload=payload.payload)
    db.add(item); db.flush(); db.add(AuditLog(actor_user_id=current_user.id, action="notification.create", entity_type="Notification", entity_id=str(item.id), details=item.title)); db.commit(); db.refresh(item)
    return item

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: UUID, current_user: User = Depends(require_permission("notifications.manage")), db: Session = Depends(get_db)):
    item = _notification(db, current_user.company_id, notification_id)
    if item.recipient_user_id != current_user.id: raise HTTPException(403, "You can only manage your own notifications.")
    item.status = "read"; item.read_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=current_user.id, action="notification.read", entity_type="Notification", entity_id=str(item.id), details=item.title)); db.commit(); db.refresh(item)
    return item

@router.patch("/{notification_id}/archive", response_model=NotificationResponse)
def archive(notification_id: UUID, current_user: User = Depends(require_permission("notifications.manage")), db: Session = Depends(get_db)):
    item = _notification(db, current_user.company_id, notification_id)
    if item.recipient_user_id != current_user.id: raise HTTPException(403, "You can only manage your own notifications.")
    item.status = "archived"; db.add(AuditLog(actor_user_id=current_user.id, action="notification.archive", entity_type="Notification", entity_id=str(item.id), details=item.title)); db.commit(); db.refresh(item)
    return item

@router.get("/preferences", response_model=list[PreferenceResponse])
def preferences(current_user: User = Depends(require_permission("notifications.preferences.view")), db: Session = Depends(get_db)):
    return list(db.scalars(select(NotificationPreference).where(NotificationPreference.company_id == current_user.company_id, NotificationPreference.user_id == current_user.id).order_by(NotificationPreference.notification_type, NotificationPreference.channel)).all())

@router.put("/preferences", response_model=PreferenceResponse)
def upsert_preference(payload: PreferenceUpsert, current_user: User = Depends(require_permission("notifications.preferences.edit")), db: Session = Depends(get_db)):
    item = db.scalar(select(NotificationPreference).where(NotificationPreference.company_id == current_user.company_id, NotificationPreference.user_id == current_user.id, NotificationPreference.notification_type == payload.notification_type, NotificationPreference.channel == payload.channel))
    if item is None: item = NotificationPreference(company_id=current_user.company_id, user_id=current_user.id, **payload.model_dump()); db.add(item)
    else: item.enabled = payload.enabled
    db.flush(); db.add(AuditLog(actor_user_id=current_user.id, action="notification.preference.update", entity_type="NotificationPreference", entity_id=str(item.id), details=f"{payload.notification_type}/{payload.channel}")); db.commit(); db.refresh(item)
    return item
