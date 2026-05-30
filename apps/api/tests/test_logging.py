# ############################################################################
# AI_HEADER: MODULE_TEST_LOGGING
# ROLE: Tests for logging spine (envelope, correlation, redactor).
# DEPENDENCIES: pytest, httpx, app.core.redactor
# GRACE_ANCHORS: [TEST_REDACTOR, TEST_CORRELATION]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-LOGGING
# purpose: Verify logging spine components (redactor, correlation middleware).
# owns:
#   - apps/api/tests/test_logging.py
# inputs:
#   - app.core.redactor.redact_dict
#   - CorrelationMiddleware via async_client
# outputs:
#   - test results (pass/fail)
# dependencies:
#   - pytest
#   - httpx.AsyncClient
#   - M-OBSERVABILITY-REDACTOR
#   - M-OBSERVABILITY-CORRELATION
# side_effects:
#   - none (tests are isolated)
# invariants:
#   - redactor removes PII keys
#   - redactor handles nested dicts and lists
#   - correlation ID is echoed in response header
#   - correlation ID is minted if not provided
# failure_policy:
#   - test failures must not affect other tests
# non_goals:
#   - no integration tests with external services
#   - no performance tests (deferred)
# END_MODULE_CONTRACT: M-TEST-LOGGING

import pytest
from httpx import AsyncClient

from app.core.redactor import redact_dict


# START_BLOCK: TEST_REDACTOR
def test_redact_pii():
    """Redactor removes PII keys."""
    data = {
        "username": "test",
        "password": "secret123",
        "birth_date": "1990-01-15",
        "public_field": "visible",
    }

    redacted = redact_dict(data)

    assert redacted["username"] == "test"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["birth_date"] == "[REDACTED]"
    assert redacted["public_field"] == "visible"


def test_redact_nested():
    """Redactor handles nested dicts."""
    data = {
        "user": {
            "name": "test",
            "token": "abc123",
        }
    }

    redacted = redact_dict(data)

    assert redacted["user"]["name"] == "test"
    assert redacted["user"]["token"] == "[REDACTED]"


def test_redact_list():
    """Redactor handles lists of dicts."""
    data = {
        "users": [
            {"name": "alice", "password": "secret1"},
            {"name": "bob", "api_key": "key123"},
        ]
    }

    redacted = redact_dict(data)

    assert redacted["users"][0]["name"] == "alice"
    assert redacted["users"][0]["password"] == "[REDACTED]"
    assert redacted["users"][1]["name"] == "bob"
    assert redacted["users"][1]["api_key"] == "[REDACTED]"


def test_redact_case_insensitive():
    """Redactor is case-insensitive."""
    data = {
        "Password": "secret",
        "API_KEY": "key123",
        "Token": "token123",
    }

    redacted = redact_dict(data)

    assert redacted["Password"] == "[REDACTED]"
    assert redacted["API_KEY"] == "[REDACTED]"
    assert redacted["Token"] == "[REDACTED]"
# END_BLOCK: TEST_REDACTOR


# START_BLOCK: TEST_CORRELATION
@pytest.mark.asyncio
async def test_correlation_id_round_trip(async_client: AsyncClient):
    """Correlation ID is echoed in response header."""
    correlation_id = "test-correlation-123"

    response = await async_client.get(
        "/api/health", headers={"X-Correlation-Id": correlation_id}
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == correlation_id


@pytest.mark.asyncio
async def test_correlation_id_minted(async_client: AsyncClient):
    """Correlation ID is minted if not provided."""
    response = await async_client.get("/api/health")

    assert response.status_code == 200
    assert "X-Correlation-Id" in response.headers
    assert len(response.headers["X-Correlation-Id"]) > 0


@pytest.mark.asyncio
async def test_correlation_id_format(async_client: AsyncClient):
    """Minted correlation ID is a valid UUID."""
    response = await async_client.get("/api/health")

    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-Id"]

    # Check UUID format (8-4-4-4-12 hex digits)
    parts = correlation_id.split("-")
    assert len(parts) == 5
    assert len(parts[0]) == 8
    assert len(parts[1]) == 4
    assert len(parts[2]) == 4
    assert len(parts[3]) == 4
    assert len(parts[4]) == 12
# END_BLOCK: TEST_CORRELATION
