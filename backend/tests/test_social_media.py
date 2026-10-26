from app.social_media.models import SocialPost
from app.social_media.schemas import PLATFORMS, STATUSES, TRANSITIONS, SocialPerformanceUpdate


def test_social_platforms_match_approved_module():
    assert PLATFORMS == {"instagram", "facebook", "linkedin", "youtube", "website"}


def test_social_lifecycle():
    assert "ready" in TRANSITIONS["draft"]
    assert "scheduled" in TRANSITIONS["ready"]
    assert "published" in TRANSITIONS["scheduled"]
    assert TRANSITIONS["published"] == set()
    assert STATUSES == {"draft", "ready", "scheduled", "published"}


def test_social_performance_validation():
    metrics = SocialPerformanceUpdate(reach=100, impressions=250, likes=20, comments=3, shares=2, saves=4, clicks=8, views=120)
    assert metrics.reach == 100
    assert metrics.views == 120
    try:
        SocialPerformanceUpdate(reach=-1)
        assert False
    except ValueError:
        assert True


def test_social_post_persists_performance_fields():
    table_columns = {column.name for column in SocialPost.__table__.columns}
    assert {"impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "views"}.issubset(table_columns)
