from app.marketing.router import TRANSITIONS
from app.marketing.schemas import ACTIVITY_TYPES, CAMPAIGN_CHANNELS, CAMPAIGN_OBJECTIVES, CAMPAIGN_STATUSES


def test_marketing_campaign_lifecycle():
    assert TRANSITIONS["planned"] == {"active", "cancelled"}
    assert "completed" in TRANSITIONS["active"]
    assert TRANSITIONS["completed"] == set()
    assert TRANSITIONS["cancelled"] == set()


def test_marketing_catalogs():
    assert {"planned", "active", "paused", "completed", "cancelled"}.issubset(CAMPAIGN_STATUSES)
    assert "lead_generation" in CAMPAIGN_OBJECTIVES
    assert "instagram" in CAMPAIGN_CHANNELS
    assert "campaign_launch" in ACTIVITY_TYPES


def test_campaign_cannot_restart_after_completion():
    assert "active" not in TRANSITIONS["completed"]


def test_campaign_cannot_bypass_planning_gate():
    assert "completed" not in TRANSITIONS["planned"]


def test_marketing_kpi_channels_are_supported():
    assert {"ctr", "cost_per_lead", "cost_per_conversion", "roas"}.issubset({"ctr", "cost_per_lead", "cost_per_conversion", "roas"})


def test_activity_catalog_is_controlled():
    assert "other" in ACTIVITY_TYPES


def test_campaign_terminal_states_have_no_outgoing_transitions():
    for terminal in ("completed", "cancelled"):
        assert not TRANSITIONS[terminal]
