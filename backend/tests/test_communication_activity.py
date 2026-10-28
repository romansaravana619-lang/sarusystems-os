from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.communication.schemas import ActivityCreate


def test_activity_types_are_strict():
    with pytest.raises(ValidationError):
        ActivityCreate(activity_type="chat", summary="x", occurred_at=datetime.now(timezone.utc))


def test_activity_requires_valid_direction():
    with pytest.raises(ValidationError):
        ActivityCreate(activity_type="call", direction="sideways", summary="x", occurred_at=datetime.now(timezone.utc))


def test_entity_type_is_strict():
    with pytest.raises(ValidationError):
        ActivityCreate(activity_type="meeting", entity_type="unknown", entity_id=str(uuid4()), summary="x", occurred_at=datetime.now(timezone.utc))


def test_activity_accepts_all_core_history_types():
    for activity_type in ["email", "call", "meeting", "client_note", "internal_note", "interaction"]:
        payload = ActivityCreate(activity_type=activity_type, summary="recorded", occurred_at=datetime.now(timezone.utc))
        assert payload.activity_type == activity_type
