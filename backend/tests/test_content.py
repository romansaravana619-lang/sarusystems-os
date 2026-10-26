from app.content.router import ASSET_TRANSITIONS, IDEA_TRANSITIONS, PRODUCTION_TRANSITIONS, PUBLICATION_TRANSITIONS
from app.content.schemas import CONTENT_TYPES, PLATFORMS, PRIORITIES, PRODUCTION_STATUSES

def test_content_catalogs():
    assert {"post","reel","video"}.issubset(CONTENT_TYPES)
    assert "urgent" in PRIORITIES
    assert {"instagram","linkedin","youtube"}.issubset(PLATFORMS)
    assert "review" in PRODUCTION_STATUSES

def test_idea_lifecycle_requires_approval_before_production():
    assert "approved" in IDEA_TRANSITIONS["idea"]
    assert "in_production" in IDEA_TRANSITIONS["approved"]
    assert "in_production" not in IDEA_TRANSITIONS["idea"]

def test_asset_review_lifecycle():
    assert "in_review" in ASSET_TRANSITIONS["draft"]
    assert "approved" in ASSET_TRANSITIONS["in_review"]
    assert "revision" in ASSET_TRANSITIONS["in_review"]
    assert "approved" not in ASSET_TRANSITIONS["draft"]

def test_production_lifecycle():
    assert "in_progress" in PRODUCTION_TRANSITIONS["planned"]
    assert "review" in PRODUCTION_TRANSITIONS["in_progress"]
    assert "revision" in PRODUCTION_TRANSITIONS["review"]
    assert "completed" in PRODUCTION_TRANSITIONS["review"]

def test_publication_gate():
    assert "scheduled" in PUBLICATION_TRANSITIONS["planned"]
    assert "published" in PUBLICATION_TRANSITIONS["scheduled"]
    assert "published" not in PUBLICATION_TRANSITIONS["planned"]
    assert PUBLICATION_TRANSITIONS["published"] == set()
