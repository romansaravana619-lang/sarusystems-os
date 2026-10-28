from app.services.schemas import PRICING_MODELS, ServiceCreate, ServiceItemCreate


def test_service_pricing_models_are_explicit() -> None:
    assert PRICING_MODELS == {"fixed", "hourly", "monthly", "custom"}


def test_service_create_defaults() -> None:
    payload = ServiceCreate(code="WEB", name="Professional Website")
    assert payload.pricing_model == "custom"
    assert payload.currency == "INR"
    assert payload.base_price is None


def test_service_create_accepts_catalog_fields() -> None:
    payload = ServiceCreate(
        code="SOFT",
        name="Custom Software",
        category="Development",
        pricing_model="fixed",
        base_price=25000,
        currency="INR",
        typical_duration_days=30,
        required_skills="Python, FastAPI",
        freelancer_roles="Backend Developer",
        workflow_template="Discovery > Build > Review > Launch",
        deliverable_template="Application > Documentation",
    )
    assert payload.category == "Development"
    assert payload.base_price == 25000
    assert payload.typical_duration_days == 30


def test_service_item_requires_name() -> None:
    payload = ServiceItemCreate(name="Requirements call")
    assert payload.is_mandatory is True
    assert payload.sort_order == 0
