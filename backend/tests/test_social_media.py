from app.social_media.schemas import PLATFORMS, STATUSES, TRANSITIONS

def test_social_catalogs():
    assert {"linkedin", "instagram", "facebook", "x"}.issubset(PLATFORMS)
    assert {"draft", "ready", "scheduled", "published"}.issubset(STATUSES)

def test_social_lifecycle():
    assert "ready" in TRANSITIONS["draft"]
    assert "scheduled" in TRANSITIONS["ready"]
    assert "published" in TRANSITIONS["scheduled"]
    assert TRANSITIONS["published"] == set()
