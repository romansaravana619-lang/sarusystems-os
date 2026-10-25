from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.company.schemas import CompanyProfileUpdate, DepartmentCreate, GoalCreate, RuleCreate


def test_company_profile_accepts_core_identity_fields() -> None:
    payload = CompanyProfileUpdate(legal_name="Saru Systems", vision="Solve real business problems", mission="Build practical technology")
    assert payload.legal_name == "Saru Systems"
    assert payload.vision is not None


def test_department_requires_name_and_code() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreate(name="", code="DEV")
    with pytest.raises(ValidationError):
        DepartmentCreate(name="Development", code="")


def test_goal_has_safe_defaults() -> None:
    goal = GoalCreate(title="Grow recurring revenue")
    assert goal.status == "active"
    assert goal.priority == "medium"


def test_rule_priority_is_bounded() -> None:
    RuleCreate(name="Founder approval", priority=1)
    with pytest.raises(ValidationError):
        RuleCreate(name="Invalid", priority=0)
    with pytest.raises(ValidationError):
        RuleCreate(name="Invalid", priority=10001)


def test_optional_owner_is_uuid() -> None:
    owner = uuid4()
    assert DepartmentCreate(name="Operations", code="OPS", owner_user_id=owner).owner_user_id == owner
