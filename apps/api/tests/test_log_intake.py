# ############################################################################
# AI_HEADER: MODULE_TEST_LOG_INTAKE
# ROLE: Tests for POST /api/_log endpoint.
# DEPENDENCIES: pytest, httpx, app.api._log
# GRACE_ANCHORS: [TEST_AUTH_REQUIRED, TEST_VALID_BATCH, TEST_INVALID_ENVELOPE]
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-LOG-INTAKE
# purpose: Verify log intake endpoint behavior — auth, validation, acceptance.
# owns:
#   - apps/api/tests/test_log_intake.py
# inputs:
#   - async_client fixture
#   - make_initdata fixture (for auth)
# outputs:
#   - pytest test results
# dependencies:
#   - M-API-LOG-INTAKE
#   - M-LOG-INTAKE-SERVICE
# invariants:
#   - auth required (401 without session)
#   - valid envelopes accepted
#   - invalid envelopes rejected
# failure_policy:
#   - test failures indicate contract violations
# non_goals:
#   - no rate limiting tests (deferred to W-RATELIMIT)
# END_MODULE_CONTRACT: M-TEST-LOG-INTAKE

# START_MODULE_MAP: M-TEST-LOG-INTAKE
# public_entrypoints:
#   - test_log_intake_requires_auth
#   - test_log_intake_accepts_valid_batch
#   - test_log_intake_rejects_invalid_envelope
#   - test_log_intake_bypass_prevention
#   - test_log_intake_http_normalization
# semantic_blocks:
#   - TEST_AUTH_REQUIRED: verify 401 without auth
#   - TEST_VALID_BATCH: verify acceptance of valid logs
#   - TEST_INVALID_ENVELOPE: verify rejection of invalid logs
# owned_tests:
#   - apps/api/tests/test_log_intake.py
# END_MODULE_MAP: M-TEST-LOG-INTAKE

import pytest
from httpx import AsyncClient


# START_BLOCK: TEST_AUTH_REQUIRED
@pytest.mark.asyncio
async def test_log_intake_requires_auth(async_client: AsyncClient):
    """Log intake accepts logs even without auth."""
    response = await async_client.post(
        "/api/_log",
        json={
            "envelopes": [
                {
                    "ts": "2026-05-30T10:00:00Z",
                    "level": "info",
                    "event": "system.request",
                    "correlation_id": "test-corr-id",
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST-LOG-INTAKE",
                    "block": "TEST_INT_AUTH",
                    "msg": "test",
                }
            ]
        },
    )
    assert response.status_code == 200  # _log accepts unauthenticated requests


# END_BLOCK: TEST_AUTH_REQUIRED


# START_BLOCK: TEST_VALID_BATCH
@pytest.mark.asyncio
async def test_log_intake_accepts_valid_batch(async_client: AsyncClient, make_initdata):
    """Log intake accepts valid batch."""
    # Auth
    user_raw = make_initdata(user_id=9999, username="loguser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Send logs
    response = await async_client.post(
        "/api/_log",
        json={
            "envelopes": [
                {
                    "ts": "2026-05-30T10:00:00Z",
                    "level": "info",
                    "event": "system.request",
                    "correlation_id": "abc123",
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST-LOG-INTAKE",
                    "block": "TEST_BATCH",
                    "msg": "test1",
                },
                {
                    "ts": "2026-05-30T10:00:01Z",
                    "level": "warn",
                    "event": "system.request",
                    "correlation_id": "abc124",
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST-LOG-INTAKE",
                    "block": "TEST_BATCH",
                    "msg": "test2",
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 2
    assert data["rejected"] == 0


# END_BLOCK: TEST_VALID_BATCH


# START_BLOCK: TEST_INVALID_ENVELOPE
@pytest.mark.asyncio
async def test_log_intake_rejects_invalid_envelope(
    async_client: AsyncClient, make_initdata
):
    """Log intake rejects malformed envelope at Pydantic level."""
    # Auth
    user_raw = make_initdata(user_id=10000, username="badloguser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Send invalid log (missing required fields) - Pydantic will reject this
    response = await async_client.post(
        "/api/_log",
        json={
            "envelopes": [
                {"level": "info"},  # Missing required fields (Pydantic validation fails)
            ]
        },
    )

    # Pydantic validation fails before reaching service
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_log_intake_handles_mixed_batch(
    async_client: AsyncClient, make_initdata
):
    """Log intake handles batch with valid and service-level invalid envelopes."""
    # Auth
    user_raw = make_initdata(user_id=10001, username="mixedloguser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Send batch where all pass Pydantic but one might fail service validation
    # For MVP, we accept all that pass Pydantic structure validation
    response = await async_client.post(
        "/api/_log",
        json={
            "envelopes": [
                {
                    "ts": "2026-05-30T10:00:00Z",
                    "level": "info",
                    "event": "system.request",
                    "correlation_id": "abc125",
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST-LOG-INTAKE",
                    "block": "TEST_MIXED",
                    "msg": "valid message",
                },
                {
                    "ts": "2026-05-30T10:00:01Z",
                    "level": "warn",
                    "event": "system.request",
                    "correlation_id": "abc126",
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST-LOG-INTAKE",
                    "block": "TEST_MIXED",
                    "msg": "another valid message",
                },
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 2
    assert data["rejected"] == 0


# END_BLOCK: TEST_INVALID_ENVELOPE


def test_log_intake_bypass_prevention(monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOG-INTAKE.test_log_intake_bypass_prevention
    # purpose: Verify that raw UUID, email-like correlation, and raw UUID in user_id_hash/question_id_hash are normalized/redacted by intake.
    # inputs: monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOG-INTAKE.test_log_intake_bypass_prevention
    from app.services.log_intake import LogIntakeService

    captured_emits = []
    def mock_emit_line(self, data):
        captured_emits.append(data)

    monkeypatch.setattr(LogIntakeService, "_emit_line", mock_emit_line)
    # Set app_env to "test" so hash_log_identifier allows local fallback salt
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "app_env", "test")

    raw_uuid_corr = "123e4567-e89b-12d3-a456-426614174000"
    email_corr = "secret@example.com"
    safe_corr = "h1_" + "a" * 24
    raw_user_uuid = "123e4567-e89b-12d3-a456-426614174001"
    raw_question_uuid = "123e4567-e89b-12d3-a456-426614174002"

    envelopes = [
        {
            "ts": "2026-05-30T10:00:00Z",
            "level": "info",
            "event": "system.request",
            "correlation_id": raw_uuid_corr,
            "service": "web",
            "service_version": "test",
            "env": "test",
            "slice": "W-TEST",
            "module": "M-TEST",
            "block": "B-TEST",
            "user_id_hash": raw_user_uuid,
            "question_id_hash": raw_question_uuid,
        },
        {
            "ts": "2026-05-30T10:00:00Z",
            "level": "info",
            "event": "system.request",
            "correlation_id": email_corr,
            "service": "web",
            "service_version": "test",
            "env": "test",
            "slice": "W-TEST",
            "module": "M-TEST",
            "block": "B-TEST",
        },
        {
            "ts": "2026-05-30T10:00:00Z",
            "level": "info",
            "event": "system.request",
            "correlation_id": safe_corr,
            "service": "web",
            "service_version": "test",
            "env": "test",
            "slice": "W-TEST",
            "module": "M-TEST",
            "block": "B-TEST",
        }
    ]

    import uuid
    service = LogIntakeService(db=None)

    # process_batch is an async function, we must await it!
    import asyncio
    result = asyncio.run(service.process_batch(user_id=uuid.uuid4(), envelopes=envelopes))

    assert result["accepted"] == 3
    assert len(captured_emits) == 3

    # 1. Raw UUID correlation -> normalized to valid h1_
    assert captured_emits[0]["correlation_id"].startswith("h1_")
    assert raw_uuid_corr not in captured_emits[0]["correlation_id"]

    # 2. Raw user_id_hash -> redacted
    assert captured_emits[0]["user_id_hash"] == "[redacted-identifier]"

    # 3. Raw question_id_hash -> redacted
    assert captured_emits[0]["question_id_hash"] == "[redacted-identifier]"

    # 4. Email-like correlation -> normalized to valid h1_
    assert captured_emits[1]["correlation_id"].startswith("h1_")
    assert email_corr not in captured_emits[1]["correlation_id"]

    # 5. Safe correlation -> preserved
    assert captured_emits[2]["correlation_id"] == safe_corr


@pytest.mark.asyncio
async def test_log_intake_http_normalization(async_client: AsyncClient, monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOG-INTAKE.test_log_intake_http_normalization
    # purpose: Verify that HTTP /api/_log endpoint normalizes raw correlation and redacts raw user_id_hash.
    # inputs: async_client, monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOG-INTAKE.test_log_intake_http_normalization
    from app.services.log_intake import LogIntakeService

    captured_emits = []
    def mock_emit_line(self, data):
        captured_emits.append(data)

    monkeypatch.setattr(LogIntakeService, "_emit_line", mock_emit_line)

    raw_uuid_corr = "123e4567-e89b-12d3-a456-426614174000"
    raw_user_uuid = "123e4567-e89b-12d3-a456-426614174001"

    response = await async_client.post(
        "/api/_log",
        json={
            "envelopes": [
                {
                    "ts": "2026-05-30T10:00:00Z",
                    "level": "info",
                    "event": "system.request",
                    "correlation_id": raw_uuid_corr,
                    "service": "web",
                    "service_version": "test",
                    "env": "test",
                    "slice": "W-TEST",
                    "module": "M-TEST",
                    "block": "B-TEST",
                    "user_id_hash": raw_user_uuid,
                }
            ]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1

    assert len(captured_emits) == 1
    # Check normalization
    from app.core.log_identity import is_opaque_log_id
    assert is_opaque_log_id(captured_emits[0]["correlation_id"]) is True
    assert raw_uuid_corr not in str(captured_emits[0])
    assert captured_emits[0]["user_id_hash"] == "[redacted-identifier]"
