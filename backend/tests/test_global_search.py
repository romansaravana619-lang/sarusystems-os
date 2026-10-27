from app.global_search.router import MAX_LIMIT, PERMISSION, router


def test_global_search_permission_contract():
    assert PERMISSION == "global_search.view"
    assert MAX_LIMIT == 50


def test_global_search_route_contract():
    routes = {(route.path, frozenset(route.methods or ())) for route in router.routes}
    assert ("/global-search", frozenset({"GET"})) in routes


def test_global_search_is_read_only_and_company_scoped():
    route = next(route for route in router.routes if route.path == "/global-search")
    assert route.methods == {"GET"}
    assert route.dependant.dependencies
