from app.services.schemas import PRICING_MODELS, ServiceCreate, ServiceItemCreate


def test_service_pricing_models_are_explicit() -> None:
    assert PRICING_MODELS == {"fixed", "hourly", "monthly", "custom"}


def test_service_create_defaults() -> None:
    payload = ServiceCreate(code="WEB", name="Professional Website")
    assert payload.pricing_model == "custom"
    assert payload.currency == "INR"
    assert payload.base_price is None


def test_service_item_requires_name() -> None:
    payload = ServiceItemCreate(name="Requirements call")
    assert payload.is_mandatory is True
    assert payload.sort_order == 0
