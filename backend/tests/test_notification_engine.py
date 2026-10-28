from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.notifications.schemas import NotificationCreate, PreferenceUpsert


def test_notification_type_is_strict():
    with pytest.raises(ValidationError):
        NotificationCreate(recipient_user_id=uuid4(), notification_type="random", title="x", message="y")


def test_notification_channel_and_priority_are_strict():
    with pytest.raises(ValidationError):
        NotificationCreate(recipient_user_id=uuid4(), notification_type="general", channel="sms", title="x", message="y")
    with pytest.raises(ValidationError):
        NotificationCreate(recipient_user_id=uuid4(), notification_type="general", priority="critical", title="x", message="y")


def test_all_approved_notification_types_are_supported():
    for kind in ["system_alert", "task_due", "deadline", "meeting_reminder", "follow_up", "payment_due", "payment_received", "approval_required", "project_update", "freelancer_update", "client_update", "workflow_event", "general"]:
        item = NotificationCreate(recipient_user_id=uuid4(), notification_type=kind, title="x", message="y", scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=5))
        assert item.notification_type == kind


def test_preferences_use_same_type_and_channel_contract():
    assert PreferenceUpsert(notification_type="deadline", channel="email", enabled=False).enabled is False
    with pytest.raises(ValidationError):
        PreferenceUpsert(notification_type="deadline", channel="push")
