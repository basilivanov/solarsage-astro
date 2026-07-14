# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LOGGING_PRIVACY — Tests for route template logging
# ROLE: Tests for route template logging and parameter stripping.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-LOGGING-PRIVACY
# purpose: Verify that request routing logs template path instead of raw path parameters.
# owns:
#   - apps/api/tests/test_logging_privacy.py
# inputs: none
# outputs: test assertions
# dependencies:
#   - pytest, app.core.config.Settings, app.main.create_app, app.core.log_identity.hash_user_id
# side_effects: none
# invariants: none
# failure_policy: raise on failure
# END_MODULE_CONTRACT: M-TEST-LOGGING-PRIVACY

# START_MODULE_MAP: M-TEST-LOGGING-PRIVACY
# public_entrypoints:
#   - test_route_template_logging
#   - test_user_id_hash_binding_after_session
#   - test_auth_rejection_no_prints
#   - test_horary_chat_natal_events_no_raw_uuids
#   - test_malformed_hash_bypass
#   - test_correlation_id_normalization
#   - test_envelope_user_id_hash_redaction
#   - test_logging_failures_swallowed
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_logging_privacy.py
# END_MODULE_MAP: M-TEST-LOGGING-PRIVACY

import pytest
from httpx import ASGITransport, AsyncClient
from app.core.config import Settings
from app.main import create_app
from app.core.log_identity import hash_log_identifier

@pytest.mark.asyncio
async def test_route_template_logging(db_session, make_initdata, monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_route_template_logging
    # purpose: Verify that request routing logs template path instead of raw path parameters.
    # inputs: db_session, make_initdata, monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_route_template_logging
    # Setup log capture list
    captured_logs = []

    def mock_log_event(event, level="info", msg="", **kwargs):
        # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_log_event
        # purpose: Mock log_event for capturing telemetry events.
        # inputs: event, level, msg, kwargs
        # returns: none
        # side_effects: appends to captured_logs
        # emitted_logs: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_log_event
        captured_logs.append((event, level, msg, kwargs))

    import app.middleware.correlation as corr_module
    monkeypatch.setattr(corr_module, "log_event", mock_log_event)

    # 1. Dev settings with internal routes enabled
    dev_settings = Settings(
        _env_file=None,
        APP_ENV="dev",
        APP_DOMAIN="localhost",
        DEV_MODE=True,
    )
    app_instance = create_app(dev_settings)

    from app.db.session import get_session
    async def _override():
        yield db_session
    app_instance.dependency_overrides[get_session] = _override

    # Create client using AsyncClient and ASGITransport
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Auth (admin endpoint, simplified for MVP)
        user_raw = make_initdata(user_id=12345, username="test_user")
        await client.post("/api/auth/telegram", json={"initData": user_raw})

        # Call a parameterized route
        await client.get("/api/natal/report/some-uuid-value")

        # Filter system.request logs
        req_logs = [log for log in captured_logs if log[0] == "system.request"]

        assert len(req_logs) > 0
        last_log_http = req_logs[-1][3].get("http", {})
        assert last_log_http.get("route") == "/api/natal/report/{report_id}"

        app_instance.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_id_hash_binding_after_session(db_session, make_initdata, monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_user_id_hash_binding_after_session
    # purpose: Verify that user_id_hash is correctly bound to log context after session validation.
    # inputs: db_session, make_initdata, monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_user_id_hash_binding_after_session
    # Test user_id_hash binding after valid session
    bound_contexts = []

    def mock_bind_log_context(**kwargs):
        # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_bind_log_context
        # purpose: Mock bind_log_context to track context binding.
        # inputs: kwargs
        # returns: none
        # side_effects: appends to bound_contexts
        # emitted_logs: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_bind_log_context
        bound_contexts.append(kwargs)

    import app.core.dependencies as deps_module
    monkeypatch.setattr(deps_module, "bind_log_context", mock_bind_log_context)

    dev_settings = Settings(
        _env_file=None,
        APP_ENV="dev",
        APP_DOMAIN="localhost",
        DEV_MODE=True,
    )
    app_instance = create_app(dev_settings)

    from app.db.session import get_session
    async def _override():
        yield db_session
    app_instance.dependency_overrides[get_session] = _override

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        user_raw = make_initdata(user_id=12345, username="test_user")
        # Login to get cookie
        resp = await client.post("/api/auth/telegram", json={"initData": user_raw})
        assert resp.status_code == 200

        # Access a protected endpoint to trigger dependency resolution
        await client.get("/api/profile")

        # Verify that user_id_hash was bound
        has_user_hash = any("user_id_hash" in ctx for ctx in bound_contexts)
        assert has_user_hash

        # Find the value
        user_hash_val = next(ctx["user_id_hash"] for ctx in bound_contexts if "user_id_hash" in ctx)
        assert user_hash_val.startswith("h1_")
        assert len(user_hash_val) == 27

    app_instance.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_rejection_no_prints(db_session, monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_auth_rejection_no_prints
    # purpose: Verify that authentication rejection does not print raw session/cookie details.
    # inputs: db_session, monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_auth_rejection_no_prints
    # Verify that auth rejection produces no raw prints
    printed_messages = []

    def mock_print(*args, **kwargs):
        # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_print
        # purpose: Mock print statement to capture printed output.
        # inputs: args, kwargs
        # returns: none
        # side_effects: appends to printed_messages
        # emitted_logs: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.mock_print
        printed_messages.append(" ".join(str(arg) for arg in args))

    monkeypatch.setattr("builtins.print", mock_print)

    dev_settings = Settings(
        _env_file=None,
        APP_ENV="dev",
        APP_DOMAIN="localhost",
        DEV_MODE=True,
    )
    app_instance = create_app(dev_settings)

    from app.db.session import get_session
    async def _override():
        yield db_session
    app_instance.dependency_overrides[get_session] = _override

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Request with invalid token / no token
        await client.get("/api/profile")

        # Verify that printed_messages is completely empty
        assert printed_messages == []

    app_instance.dependency_overrides.clear()


def test_horary_chat_natal_events_no_raw_uuids(monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_horary_chat_natal_events_no_raw_uuids
    # purpose: Verify that logged events for horary, chat, and natal do not contain raw UUIDs.
    # inputs: monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_horary_chat_natal_events_no_raw_uuids
    captured_envelopes = []
    def _mock_emit(envelope):
        captured_envelopes.append(envelope)

    import app.core.logging as logging_module
    monkeypatch.setattr(logging_module, "_emit", _mock_emit)

    # Set app_env to "test" so hash_log_identifier allows local fallback salt
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "app_env", "test")

    # Bind required log context to prevent assertion errors
    logging_module.bind_log_context(
        slice="W-TEST",
        module="M-TEST",
        block="B-TEST",
        correlation_id="h1_" + "a" * 24
    )

    raw_uuid = "123e4567-e89b-12d3-a456-426614174000"

    # Representative chat event
    logging_module.log_event(
        "chat.message_sent",
        payload={
            "thread_id_hash": hash_log_identifier("thread", raw_uuid),
            "message_id_hash": hash_log_identifier("message", raw_uuid),
            "role": "user",
        }
    )

    # Representative horary event
    logging_module.log_event(
        "horary.credit_refunded",
        payload={
            "credit_id_hash": hash_log_identifier("credit", raw_uuid),
            "question_id_hash": hash_log_identifier("question", raw_uuid),
        }
    )
    # Representative natal event
    logging_module.log_event(
        "natal.report_generation_succeeded",
        payload={
            "report_id_hash": hash_log_identifier("report", raw_uuid),
        }
    )

    for env in captured_envelopes:
        env_str = str(env)
        assert raw_uuid not in env_str
        assert "h1_" in env_str


def test_malformed_hash_bypass():
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_malformed_hash_bypass
    # purpose: Verify that malformed hash bypass attempts are redacted.
    # inputs: none
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_malformed_hash_bypass
    # Test redactor hash bypass checks
    from app.core.redactor import redact_dict

    # 1. Valid hash preserved
    valid_hash = "h1_" + "a" * 24
    data_valid = {"user_id_hash": valid_hash, "question_id_hash": valid_hash}
    redacted_valid = redact_dict(data_valid)
    assert redacted_valid["user_id_hash"] == valid_hash
    assert redacted_valid["question_id_hash"] == valid_hash
    # 2. Raw UUID redacted
    raw_uuid = "123e4567-e89b-12d3-a456-426614174000"
    data_invalid_1 = {"user_id_hash": raw_uuid}
    redacted_invalid_1 = redact_dict(data_invalid_1)
    assert redacted_invalid_1["user_id_hash"] == "[redacted-identifier]"

    # 3. Integer redacted
    data_invalid_2 = {"question_id_hash": 123456789}
    redacted_invalid_2 = redact_dict(data_invalid_2)
    assert redacted_invalid_2["question_id_hash"] == "[redacted-identifier]"

    # 4. Malformed short hash redacted
    data_invalid_3 = {"user_id_hash": "h1_short"}
    redacted_invalid_3 = redact_dict(data_invalid_3)
    assert redacted_invalid_3["user_id_hash"] == "[redacted-identifier]"


@pytest.mark.asyncio
async def test_correlation_id_normalization(db_session, monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_correlation_id_normalization
    # purpose: Verify correlation_id is normalized/hashed and raw values never leak.
    # inputs: db_session, monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_correlation_id_normalization
    captured_envelopes = []

    def _mock_emit(envelope):
        captured_envelopes.append(envelope)

    import app.core.logging as logging_module
    monkeypatch.setattr(logging_module, "_emit", _mock_emit)

    dev_settings = Settings(
        _env_file=None,
        APP_ENV="dev",
        APP_DOMAIN="localhost",
        DEV_MODE=True,
    )
    app_instance = create_app(dev_settings)

    from app.db.session import get_session
    async def _override():
        yield db_session
    app_instance.dependency_overrides[get_session] = _override

    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Case 1: Raw UUID header -> hashed
        raw_uuid = "123e4567-e89b-12d3-a456-426614174000"
        resp = await client.get("/api/health", headers={"X-Correlation-Id": raw_uuid})
        assert resp.status_code == 200
        # Response header contains normalized/hashed correlation id
        corr_resp = resp.headers.get("X-Correlation-Id")
        assert corr_resp.startswith("h1_")
        assert raw_uuid not in corr_resp

        # Verify captured emitted event
        assert len(captured_envelopes) > 0
        assert captured_envelopes[-1]["correlation_id"] == corr_resp
        assert raw_uuid not in str(captured_envelopes[-1])

        # Case 2: Safe h1_... format -> preserved
        safe_corr = "h1_" + "a" * 24
        resp = await client.get("/api/health", headers={"X-Correlation-Id": safe_corr})
        assert resp.status_code == 200
        assert resp.headers.get("X-Correlation-Id") == safe_corr
        assert captured_envelopes[-1]["correlation_id"] == safe_corr

        # Case 3: Oversized/Control characters -> replaced with minted UUID (which is hashed to h1_ format)
        bad_corr = "a" * 150
        resp = await client.get("/api/health", headers={"X-Correlation-Id": bad_corr})
        assert resp.status_code == 200
        corr_resp = resp.headers.get("X-Correlation-Id")
        # Under R3-2.1, new_correlation_id() returns h1_[0-9a-f]{24} format!
        assert corr_resp.startswith("h1_")
        assert len(corr_resp) == 27
        assert captured_envelopes[-1]["correlation_id"] == corr_resp

    app_instance.dependency_overrides.clear()


def test_envelope_user_id_hash_redaction(monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_envelope_user_id_hash_redaction
    # purpose: Verify that top-level user_id_hash in built envelope is redacted if raw.
    # inputs: monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_envelope_user_id_hash_redaction
    captured_envelopes = []
    def _mock_emit(envelope):
        captured_envelopes.append(envelope)

    import app.core.logging as logging_module
    monkeypatch.setattr(logging_module, "_emit", _mock_emit)

    # 1. Bind raw UUID as user_id_hash
    raw_uuid = "123e4567-e89b-12d3-a456-426614174000"
    # Bind required log context to prevent assertion errors
    logging_module.bind_log_context(
        slice="W-TEST",
        module="M-TEST",
        block="B-TEST",
        correlation_id="h1_" + "a" * 24,
        user_id_hash=raw_uuid
    )

    # 2. Emit log
    logging_module.log_event("system.request")

    assert len(captured_envelopes) == 1
    # Raw UUID is replaced with redacted-identifier
    assert captured_envelopes[0]["user_id_hash"] == "[redacted-identifier]"

    # Clean up context
    logging_module.clear_log_context()

    # R4A-1: Add user_id_hash exactness regression test case with newline
    try:
        logging_module.bind_log_context(
            correlation_id="h1_" + "a" * 24,
            user_id_hash="h1_" + "b" * 24 + "\n",
            slice="W", module="M", block="B",
        )
        envelope = logging_module.build_envelope("system.request")
        assert envelope["user_id_hash"] == "[redacted-identifier]"
    finally:
        logging_module.clear_log_context()

def test_logging_failures_swallowed(monkeypatch):
    # START_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_logging_failures_swallowed
    # purpose: Verify that log_event swallows internal exceptions from redactor or emit.
    # inputs: monkeypatch
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-LOGGING-PRIVACY.test_logging_failures_swallowed
    import app.core.logging as logging_module

    # 1. Monkeypatch redact_dict inside logging_module to raise ValueError
    with monkeypatch.context() as m:
        m.setattr(logging_module, "redact_dict", lambda value: (_ for _ in ()).throw(ValueError("synthetic")))
        # Bind required log context to prevent assertion errors
        logging_module.bind_log_context(
            slice="W-TEST",
            module="M-TEST",
            block="B-TEST",
            correlation_id="h1_" + "a" * 24
        )
        try:
            # Should not raise exception
            logging_module.log_event("system.request")
        finally:
            logging_module.clear_log_context()

    # 2. Monkeypatch _emit inside logging_module to raise RuntimeError
    with monkeypatch.context() as m:
        m.setattr(logging_module, "_emit", lambda envelope: (_ for _ in ()).throw(RuntimeError("emulate disk full")))
        # Bind required log context to prevent assertion errors
        logging_module.bind_log_context(
            slice="W-TEST",
            module="M-TEST",
            block="B-TEST",
            correlation_id="h1_" + "a" * 24
        )
        try:
            # Should not raise exception
            logging_module.log_event("system.request")
        finally:
            logging_module.clear_log_context()

    # 3. Unknown event still raises ValueError (programmer error)
    with pytest.raises(ValueError, match="Unknown log event"):
        logging_module.log_event("unknown.event")
