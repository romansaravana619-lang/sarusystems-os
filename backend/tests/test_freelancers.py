from app.freelancers.router import TRANSITIONS
from app.freelancers.schemas import APPLICATION_STATUSES, ASSIGNMENT_STATUSES, FREELANCER_STATUSES
from app.freelancers.workflow_router import AGREEMENT_TRANSITIONS, APPLICATION_TRANSITIONS


def test_freelancer_lifecycle_is_explicit():
    assert TRANSITIONS["prospect"] == {"screening", "rejected", "blacklisted"}
    assert "active" in TRANSITIONS["onboarding"]
    assert TRANSITIONS["blacklisted"] == set()


def test_freelancer_catalogs_cover_required_states():
    assert {"prospect", "screening", "approved", "onboarding", "active", "inactive", "rejected", "blacklisted"}.issubset(FREELANCER_STATUSES)
    assert {"received", "screening", "shortlisted", "interview", "selected", "rejected", "withdrawn"}.issubset(APPLICATION_STATUSES)
    assert {"proposed", "approved", "active", "paused", "completed", "cancelled"}.issubset(ASSIGNMENT_STATUSES)


def test_application_lifecycle_is_gated():
    assert APPLICATION_TRANSITIONS["received"] == {"screening", "withdrawn"}
    assert "selected" in APPLICATION_TRANSITIONS["interview"]
    assert APPLICATION_TRANSITIONS["selected"] == set()


def test_agreement_lifecycle_requires_signature_before_activation():
    assert AGREEMENT_TRANSITIONS["draft"] == {"pending_signature", "terminated"}
    assert "active" in AGREEMENT_TRANSITIONS["pending_signature"]
    assert AGREEMENT_TRANSITIONS["terminated"] == set()
