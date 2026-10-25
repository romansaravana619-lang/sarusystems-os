from app.freelancer_work.router import TRANSITIONS
from app.freelancer_work.schemas import REVIEW_DECISIONS, WORK_STATUSES


def test_freelancer_work_lifecycle_matches_execution_flow():
    assert TRANSITIONS["assigned"] == {"acknowledged", "cancelled"}
    assert "in_progress" in TRANSITIONS["acknowledged"]
    assert "submitted" in TRANSITIONS["in_progress"]
    assert "review" in TRANSITIONS["submitted"]
    assert "revision" in TRANSITIONS["review"]
    assert "approved" in TRANSITIONS["review"]
    assert "completed" in TRANSITIONS["approved"]
    assert TRANSITIONS["completed"] == set()


def test_freelancer_work_catalogs():
    assert {"assigned", "acknowledged", "in_progress", "submitted", "review", "revision", "approved", "completed", "cancelled"}.issubset(WORK_STATUSES)
    assert REVIEW_DECISIONS == {"approved", "revision"}


def test_no_direct_execution_to_completion():
    assert "completed" not in TRANSITIONS["assigned"]
    assert "completed" not in TRANSITIONS["in_progress"]
    assert "completed" not in TRANSITIONS["submitted"]


def test_revision_returns_to_execution_or_submission():
    assert TRANSITIONS["revision"] == {"in_progress", "submitted", "cancelled"}
