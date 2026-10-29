from pathlib import Path

from app.core.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_feature_clients_use_shared_api_transport():
    feature_clients = (
        "frontend/src/features/finance/financeApi.ts",
        "frontend/src/features/calendar/calendarApi.ts",
        "frontend/src/features/notifications/notificationsApi.ts",
        "frontend/src/features/analytics/analyticsApi.ts",
    )

    for relative_path in feature_clients:
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        assert "apiRequest" in source
        assert "fetch(" not in source


def test_shared_frontend_transport_uses_configured_api_base_url():
    source = (REPO_ROOT / "frontend/src/services/http.ts").read_text(encoding="utf-8")
    assert "VITE_API_BASE_URL" in source
    assert 'fetch(`${API_BASE_URL}${path}`' in source


def test_cors_origins_are_configurable_and_parsed():
    settings = Settings(
        environment="test",
        secret_key="test-secret",
        cors_origins="https://app.example.com, https://admin.example.com",
    )

    assert settings.cors_origin_list == [
        "https://app.example.com",
        "https://admin.example.com",
    ]
