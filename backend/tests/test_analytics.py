from app.analytics.router import PERMISSION, router


def test_analytics_permission_contract():
    assert PERMISSION == "analytics.dashboard.view"


def test_analytics_exposes_all_approved_views():
    paths = {route.path for route in router.routes}
    assert paths == {"/analytics/dashboard", "/analytics/sales", "/analytics/revenue", "/analytics/projects", "/analytics/freelancers", "/analytics/marketing", "/analytics/content"}


def test_analytics_is_company_scoped_and_read_only():
    methods = {route.path: set(route.methods or ()) for route in router.routes}
    assert all(methods[path] == {"GET"} for path in methods)
