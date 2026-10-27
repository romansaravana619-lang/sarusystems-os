from app.global_search.router import MAX_LIMIT, PERMISSION, router


def test_global_search_permission_contract():
    assert PERMISSION == "global_search.view"
    assert MAX_LIMIT == 50


def test_global_search_route_contract():
    route = next(route for route in router.routes if route.path == "/global-search")
    assert route.methods == {"GET"}


def test_global_search_route_is_registered():
    assert any(route.path == "/global-search" for route in router.routes)
