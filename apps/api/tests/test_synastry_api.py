"""Unit tests for synastry API routes."""

from fastapi.testclient import TestClient
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
