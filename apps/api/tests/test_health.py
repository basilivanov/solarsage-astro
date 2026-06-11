
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_HEALTH
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_health.py
# owns:
#   - apps/api/tests/test_health.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

"""Smoke tests for /api/health (W-1.1 exit criterion)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
    assert isinstance(body["git_sha"], str) and body["git_sha"]


def test_health_shape_is_exact() -> None:
    """Contract: exactly three keys. Adding fields silently is forbidden."""
    response = client.get("/api/health")
    assert set(response.json().keys()) == {"status", "version", "git_sha"}
