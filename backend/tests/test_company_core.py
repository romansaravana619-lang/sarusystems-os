from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.company.schemas import CompanyProfileUpdate, CompanyServiceSummary, DepartmentCreate, GoalCreate, PolicyCreate, PolicyUpdate, RuleCreate, RuleUpdate


def test_company_profile_accepts_core_identity_fields() -> None:
    payload = CompanyProfileUpdate(legal_name="Saru Systems", vision="Solve real business problems", mission="Build practical technology", business_model="Founder-led project-based software company")
    assert payload.legal_name == "Saru Systems"
    assert payload.vision is not None
    assert payload.business_model is not None


def test_department_requires_name_and_code_and_normalizes_code() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreate(name="", code="DEV")
    with pytest.raises(ValidationError):
        DepartmentCreate(name="Development", code="")
    assert DepartmentCreate(name="Development", code=" dev ").code == "DEV"


def test_goal_has_safe_defaults() -> None:
    goal = GoalCreate(title="Grow recurring revenue")
    assert goal.status == "active"
    assert goal.priority == "medium"
    assert goal.is_active is True


def test_policy_and_rule_have_operating_defaults() -> None:
    policy = PolicyCreate(title="Client confidentiality")
    assert policy.status == "active"
    assert policy.is_active is True
    rule = RuleCreate(name="Founder approval")
    assert rule.is_enabled is True
    assert RuleUpdate(is_enabled=False).is_enabled is False
    assert PolicyUpdate(status="inactive", is_active=False).status == "inactive"


def test_company_service_summary_matches_authoritative_service_fields() -> None:
    service = CompanyServiceSummary(id=uuid4(), code="WEB", name="Professional Websites", category="Web", pricing_model="custom", base_price=25000, currency="INR", typical_duration_days=14, is_active=True)
    assert service.code == "WEB"
    assert service.currency == "INR"
    assert service.is_active is True


def test_rule_priority_is_bounded() -> None:
    RuleCreate(name="Founder approval", priority=1)
    with pytest.raises(ValidationError):
        RuleCreate(name="Invalid", priority=0)
    with pytest.raises(ValidationError):
        RuleCreate(name="Invalid", priority=10001)


def test_optional_owner_is_uuid() -> None:
    owner = uuid4()
    assert DepartmentCreate(name="Operations", code="OPS", owner_user_id=owner).owner_user_id == owner
