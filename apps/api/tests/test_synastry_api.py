"""Unit tests for synastry API routes and security."""

from app.api.synastry import router


def test_synastry_router_import():
    assert router is not None
    assert router.prefix == "/api/synastry"


def test_synastry_static_routes_ordering():
    # Verify static routes (/capabilities, /quota) are registered before dynamic routes (/{partner_id})
    paths = [route.path for route in router.routes]
    cap_index = paths.index("/api/synastry/capabilities")
    quota_index = paths.index("/api/synastry/quota")
    dynamic_index = paths.index("/api/synastry/{partner_id}")

    assert cap_index < dynamic_index
    assert quota_index < dynamic_index


def test_synastry_route_definitions():
    # Verify exact required routes exist
    route_map = {(r.path, tuple(r.methods)): r for r in router.routes}
    
    assert ("/api/synastry/capabilities", ("GET",)) in route_map
    assert ("/api/synastry/quota", ("GET",)) in route_map
    assert ("/api/synastry", ("GET",)) in route_map
    assert ("/api/synastry/partners", ("POST",)) in route_map
    assert ("/api/synastry/{partner_id}", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/status", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/aspect/{aspect_id}", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/feedback", ("POST",)) in route_map
    assert ("/api/synastry/{partner_id}", ("DELETE",)) in route_map
