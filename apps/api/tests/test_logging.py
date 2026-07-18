# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

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
        "user_id": "some_raw_id",
        "session_id": "some_session_id",
    }

    redacted = redact_dict(data)

    assert redacted["username"] == "[redacted]"
    assert redacted["password"] == "[redacted]"
    assert redacted["birth_date"] == "[redacted]"
    assert redacted["public_field"] == "visible"
    assert redacted["user_id"] == "[redacted]"
    assert redacted["session_id"] == "[redacted]"


def test_redact_user_id_hash():
    """Redactor preserves user_id_hash but redacts other keys."""
    valid_hash = "h1_" + "a" * 24
    data = {
        "user_id_hash": valid_hash,
        "other_id_hash": valid_hash,
    }
    redacted = redact_dict(data)
    assert redacted["user_id_hash"] == valid_hash
    assert redacted["other_id_hash"] == valid_hash

    # R4-B1: Parametrized exactness checks for opaque log ID
    from app.core.log_identity import is_opaque_log_id

    # 1. h1_ + 24 lowercase hex -> true
    assert is_opaque_log_id("h1_" + "a" * 24) is True

    # 2. h1_ + 23 hex -> false
    assert is_opaque_log_id("h1_" + "a" * 23) is False

    # 3. h1_ + 25 hex -> false
    assert is_opaque_log_id("h1_" + "a" * 25) is False

    # 4. h1_ + 24 hex + suffix -> false
    assert is_opaque_log_id("h1_" + "a" * 24 + "extra") is False

    # 5. h1_ + 24 hex + newline -> false
    assert is_opaque_log_id("h1_" + "a" * 24 + "\n") is False

    # 6. h1_ + uppercase hex -> false
    assert is_opaque_log_id("h1_" + "A" * 24) is False

    # 7. integer / None -> false
    assert is_opaque_log_id(12345) is False
    assert is_opaque_log_id(None) is False


def test_log_identity_hashing():
    """Test log identity hashing invariants."""
    from app.core.log_identity import hash_log_identifier, hash_user_id
    h1 = hash_user_id("user123")
    h2 = hash_user_id("user123")
    h3 = hash_log_identifier("question", "user123")
    assert h1.startswith("h1_")
    assert len(h1) == 27 # h1_ + 24 chars
    assert h1 == h2
    assert h1 != h3 # namespaces isolate hashes


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
    assert redacted["user"]["token"] == "[redacted]"


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
    assert redacted["users"][0]["password"] == "[redacted]"
    assert redacted["users"][1]["name"] == "bob"
    assert redacted["users"][1]["api_key"] == "[redacted]"


def test_redact_case_insensitive():
    """Redactor is case-insensitive."""
    data = {
        "Password": "secret",
        "API_KEY": "key123",
        "Token": "token123",
    }

    redacted = redact_dict(data)

    assert redacted["Password"] == "[redacted]"
    assert redacted["API_KEY"] == "[redacted]"
    assert redacted["Token"] == "[redacted]"
# END_BLOCK: TEST_REDACTOR


# START_BLOCK: TEST_CORRELATION
@pytest.mark.asyncio
async def test_correlation_id_round_trip(async_client: AsyncClient):
    """Correlation ID is echoed in response header."""
    # A valid correlation id in the test environment (using h1_ format)
    correlation_id = "h1_" + "a" * 24

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
    """Minted correlation ID is a valid opaque log id."""
    response = await async_client.get("/api/health")

    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-Id"]

    # Check h1_ + 24 hex digits format
    assert correlation_id.startswith("h1_")
    assert len(correlation_id) == 27
# END_BLOCK: TEST_CORRELATION
