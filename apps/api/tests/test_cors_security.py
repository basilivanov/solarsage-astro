# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_CORS_SECURITY — Unit/integration tests for CORS
# ROLE: Unit/integration tests for CORS preflight and allowed origins.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CORS-SECURITY
# purpose: Verify allowed Origin preflight/GET header values and evil Origin omission.
# owns:
#   - apps/api/tests/test_cors_security.py
# inputs: none
# outputs: test assertions
# dependencies:
#   - fastapi.testclient.TestClient, app.core.config.Settings, app.main.create_app
# side_effects: none
# invariants: none
# failure_policy: raise on failure
# END_MODULE_CONTRACT: M-TEST-CORS-SECURITY

# START_MODULE_MAP: M-TEST-CORS-SECURITY
# public_entrypoints:
#   - test_cors_preflight_and_get_allowed_origin
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_cors_security.py
# END_MODULE_MAP: M-TEST-CORS-SECURITY

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app

def test_cors_preflight_and_get_allowed_origin():
    # START_FUNCTION_CONTRACT: F-M-TEST-CORS-SECURITY.test_cors_preflight_and_get_allowed_origin
    # purpose: Verify that CORS preflight options and standard requests respect configured allowed origins.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-CORS-SECURITY.test_cors_preflight_and_get_allowed_origin
    # Production/Staging simulation
    prod_settings = Settings(
        _env_file=None,
        APP_ENV="production",
        APP_DOMAIN="astro.example.com",
        CORS_ALLOWED_ORIGINS="https://astro.example.com,https://another-allowed.com",
        DEV_MODE=False,
        SESSION_COOKIE_SECURE=True,
        TELEGRAM_BOT_TOKEN="real_token_at_least_something",
        GRACE_USER_SALT="a" * 32,
        DATABASE_URL="postgresql+asyncpg://astro:astro@127.0.0.1:5432/astro",
    )

    app = create_app(prod_settings)
    client = TestClient(app)

    # 1. Allowed Origin (Preflight)
    headers = {
        "Origin": "https://astro.example.com",
        "Access-Control-Request-Method": "GET",
    }
    resp = client.options("/api/health", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://astro.example.com"
    assert resp.headers.get("access-control-allow-credentials") == "true"
    assert "origin" in resp.headers.get("vary", "").lower()
    assert resp.headers.get("access-control-allow-origin") != "*"

    # 1.1 Allowed Origin (GET)
    allowed_get = client.get(
        "/api/health",
        headers={"Origin": "https://astro.example.com"},
    )
    assert allowed_get.status_code == 200
    assert allowed_get.headers["access-control-allow-origin"] == "https://astro.example.com"
    assert allowed_get.headers["access-control-allow-credentials"] == "true"
    assert "origin" in allowed_get.headers.get("vary", "").lower()
    assert allowed_get.headers["access-control-allow-origin"] != "*"

    # 2. Evil Origin (not allowed in preflight)
    headers = {
        "Origin": "https://evil.example",
        "Access-Control-Request-Method": "GET",
    }
    resp = client.options("/api/health", headers=headers)
    assert resp.headers.get("access-control-allow-origin") is None

    # 3. Evil Origin (not allowed in standard GET)
    headers_get = {
        "Origin": "https://evil.example",
    }
    resp_get = client.get("/api/health", headers=headers_get)
    assert resp_get.status_code == 200
    assert resp_get.headers.get("access-control-allow-origin") is None

    # 4. No Origin
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") is None
