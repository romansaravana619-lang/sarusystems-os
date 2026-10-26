from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.calendar.schemas import CalendarEventCreate, CalendarEventUpdate, ReminderCreate


def test_calendar_event_types_are_strict():
    with pytest.raises(ValidationError):
        CalendarEventCreate(event_type="random", title="x", start_at=datetime.now(timezone.utc), end_at=datetime.now(timezone.utc) + timedelta(hours=1))


def test_calendar_event_requires_valid_time_window():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        CalendarEventCreate(event_type="client_meeting", title="x", start_at=start, end_at=start)


def test_calendar_entity_link_must_be_complete():
    start = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        CalendarEventCreate(event_type="follow_up", title="x", start_at=start, end_at=start + timedelta(hours=1), entity_type="client")


def test_calendar_accepts_all_approved_schedule_types():
    start = datetime.now(timezone.utc)
    for event_type in ["discovery_call", "client_meeting", "freelancer_meeting", "deadline", "content_schedule", "follow_up", "founder_reminder"]:
        event = CalendarEventCreate(event_type=event_type, title="scheduled", start_at=start, end_at=start + timedelta(hours=1))
        assert event.event_type == event_type


def test_reminder_minutes_are_bounded():
    assert ReminderCreate(minutes_before=15).minutes_before == 15
    with pytest.raises(ValidationError):
        ReminderCreate(minutes_before=-1)


def test_update_validates_status_and_event_type():
    with pytest.raises(ValidationError):
        CalendarEventUpdate(status="unknown")
    with pytest.raises(ValidationError):
        CalendarEventUpdate(event_type="unknown")
