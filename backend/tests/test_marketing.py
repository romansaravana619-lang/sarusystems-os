from app.marketing.router import TRANSITIONS
from app.marketing.schemas import CAMPAIGN_CHANNELS, CAMPAIGN_OBJECTIVES, CAMPAIGN_STATUSES

def test_marketing_campaign_lifecycle():
    assert TRANSITIONS["planned"]=={"active","cancelled"}
    assert "completed" in TRANSITIONS["active"]
    assert TRANSITIONS["completed"]==set()
    assert TRANSITIONS["cancelled"]==set()

def test_marketing_catalogs():
    assert {"planned","active","paused","completed","cancelled"}.issubset(CAMPAIGN_STATUSES)
    assert "lead_generation" in CAMPAIGN_OBJECTIVES
    assert "instagram" in CAMPAIGN_CHANNELS

def test_campaign_cannot_restart_after_completion():
    assert "active" not in TRANSITIONS["completed"]

def test_campaign_cannot_bypass_planning_gate():
    assert "completed" not in TRANSITIONS["planned"]
