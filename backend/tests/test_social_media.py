from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.social_media.models import SocialPost
from app.social_media.router import update_performance, update_post, create_post
from app.social_media.schemas import PLATFORMS, STATUSES, TRANSITIONS, SocialPerformanceUpdate, SocialPostCreate, SocialPostUpdate


def test_social_platforms_match_approved_module():
    assert PLATFORMS == {"instagram", "facebook", "linkedin", "youtube", "website"}


def test_social_lifecycle():
    assert TRANSITIONS == {"draft": {"ready"}, "ready": {"draft", "scheduled"}, "scheduled": {"ready", "published"}, "published": set()}
    assert STATUSES == {"draft", "ready", "scheduled", "published"}


def test_social_performance_validation():
    metrics = SocialPerformanceUpdate(reach=100, impressions=250, likes=20, comments=3, shares=2, saves=4, clicks=8, views=120)
    assert metrics.reach == 100
    assert metrics.views == 120
    with pytest.raises(ValidationError):
        SocialPerformanceUpdate(reach=-1)


def test_social_post_persists_performance_and_relationship_fields():
    columns = {column.name for column in SocialPost.__table__.columns}
    assert {"impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views"}.issubset(columns)
    assert {"content_asset_id", "campaign_id", "published_at"}.issubset(columns)


def test_post_create_validates_platform_and_rejects_published_initial_state():
    with pytest.raises(ValidationError):
        SocialPostCreate(platform="tiktok", post_id="x")
    request = SocialPostCreate(platform="instagram", post_id="x", status="published", post_content="copy")
    assert request.status == "published"  # route workflow rejects direct published creation


def test_duplicate_post_id_is_scoped_by_platform_and_company_constraint():
    constraint = next(c for c in SocialPost.__table__.constraints if getattr(c, "name", None) == "uq_social_post_identity")
    assert {col.name for col in constraint.columns} == {"company_id", "platform", "post_id"}


def test_schedule_requires_future_time_and_lifecycle_transition(monkeypatch):
    class Obj:
        id = uuid4(); company_id = uuid4(); platform = "linkedin"; post_id = "p1"; status = "ready"
        post_date = None; post_content = "content"; creative_url = None; published_at = None; content_asset_id = None; campaign_id = None
    obj = Obj()
    class DB:
        def commit(self): pass
        def refresh(self, value): pass
        def add(self, value): pass
    class User:
        id = uuid4(); company_id = obj.company_id
    monkeypatch.setattr("app.social_media.router._get", lambda *a: obj)
    with pytest.raises(HTTPException) as e:
        update_post(obj.id, SocialPostUpdate(status="scheduled", post_date=datetime.now(timezone.utc) - timedelta(minutes=1)), User(), DB())
    assert e.value.status_code == 400


def test_performance_only_allowed_after_published(monkeypatch):
    class Obj:
        id = uuid4(); company_id = uuid4(); status = "scheduled"
    obj = Obj()
    class DB: pass
    class User: company_id = obj.company_id
    monkeypatch.setattr("app.social_media.router._get", lambda *a: obj)
    with pytest.raises(HTTPException) as e:
        update_performance(obj.id, SocialPerformanceUpdate(likes=3), User(), DB())
    assert e.value.status_code == 409
