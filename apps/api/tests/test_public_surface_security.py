# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PUBLIC_SURFACE_SECURITY — Integration tests for public routes
# ROLE: Integration tests for public route exposure (production vs development).
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PUBLIC-SURFACE-SECURITY
# purpose: Verify GET /api/health works, internal routes are hidden in prod/staging, and visible in dev.
# owns:
#   - apps/api/tests/test_public_surface_security.py
# inputs: none
# outputs: test assertions
# dependencies:
#   - fastapi.testclient.TestClient, app.core.config.Settings, app.main.create_app
# side_effects: none
# invariants: none
# failure_policy: raise on failure
# END_MODULE_CONTRACT: M-TEST-PUBLIC-SURFACE-SECURITY

# START_MODULE_MAP: M-TEST-PUBLIC-SURFACE-SECURITY
# public_entrypoints:
#   - test_public_surface_production_vs_development
#   - test_public_surface_local_dev
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_public_surface_security.py
# END_MODULE_MAP: M-TEST-PUBLIC-SURFACE-SECURITY

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app

def test_public_surface_production_vs_development():
    # START_FUNCTION_CONTRACT: F-M-TEST-PUBLIC-SURFACE-SECURITY.test_public_surface_production_vs_development
    # purpose: Verify internal routes are hidden in production settings.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-PUBLIC-SURFACE-SECURITY.test_public_surface_production_vs_development
    # 1. Staging/Production settings simulation
    prod_settings = Settings(
        _env_file=None,
        APP_ENV="production",
        APP_DOMAIN="astro.example.com",
        CORS_ALLOWED_ORIGINS="https://astro.example.com",
        DEV_MODE=False,
        SESSION_COOKIE_SECURE=True,
        TELEGRAM_BOT_TOKEN="real_token_at_least_something",
        GRACE_USER_SALT="a" * 32,
        DATABASE_URL="postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
    )

    app = create_app(prod_settings)
    client = TestClient(app)

    # Health check is always mounted and retains exact contract
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "git_sha" in data
    assert "release_sha" in data
    assert set(data.keys()) == {"status", "version", "git_sha", "release_sha"}

    # Internal routes must return 404 in production/staging
    assert client.get("/api/debug").status_code == 404
    assert client.get("/api/metrics").status_code == 404
    assert client.get("/api/health/extended").status_code == 404
    assert client.get("/api/admin/microcopy/misses").status_code == 404

    # OpenAPI schema should not contain internal routes
    openapi = client.get("/openapi.json").json()
    paths = openapi.get("paths", {})
    assert "/api/debug" not in paths
    assert "/api/metrics" not in paths
    assert "/api/health/extended" not in paths
    assert "/api/admin/microcopy/misses" not in paths


def test_public_surface_local_dev():
    # START_FUNCTION_CONTRACT: F-M-TEST-PUBLIC-SURFACE-SECURITY.test_public_surface_local_dev
    # purpose: Verify internal routes are visible in development settings.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-PUBLIC-SURFACE-SECURITY.test_public_surface_local_dev
    # 2. Local development settings simulation
    dev_settings = Settings(
        _env_file=None,
        APP_ENV="dev",
        APP_DOMAIN="localhost",
        DEV_MODE=True,
    )
    app = create_app(dev_settings)
    client = TestClient(app)

    # Internal routes should be mounted
    openapi = client.get("/openapi.json").json()
    paths = openapi.get("paths", {})
    assert "/api/debug" in paths
    assert "/api/metrics" in paths
    assert "/api/health/extended" in paths
    assert "/api/admin/microcopy/misses" in paths
