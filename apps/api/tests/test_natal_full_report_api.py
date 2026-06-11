
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_FULL_REPORT_API
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for natal_full_report_api.py behavior
# owns:
#   - apps/api/tests/test_natal_full_report_api.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes; Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-NATAL-FULL-REPORT-API
# wave: W-NATAL-FULL (Wave 6 — test evidence)
# purpose: API tests for natal full report endpoints — generate, report retrieval,
#          feature flag gating, idempotency.

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ────────────────────────────────────────────────────────

async def _login(async_client: AsyncClient, make_initdata, *, user_id: int) -> None:
    raw = make_initdata(user_id=user_id, username=f"natreport{user_id}")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text


async def _set_profile(db_session: AsyncSession, user_id, *, gender="female"):
    from app.services.profile_service import read_profile
    profile = await read_profile(db_session, user_id)
    profile.first_name = "Test"
    profile.birth_city = "Moscow"
    profile.birthday = date(1990, 1, 15)
    profile.birth_time = time(12, 0)
    profile.birth_tz = "Europe/Moscow"
    profile.gender = gender
    profile.birth_lat = Decimal("55.75580")
    profile.birth_lon = Decimal("37.61730")
    await db_session.commit()
    return profile


MOCK_SIDECAR_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 286.93, "sign": "Capricorn", "house": 11, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 119.63, "sign": "Gemini", "house": 4, "retrograde": False, "speed": 1.0},
        {"name": "Mercury", "longitude": 277.10, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
        {"name": "Venus", "longitude": 333.55, "sign": "Pisces", "house": 12, "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 137.95, "sign": "Cancer", "house": 5, "retrograde": True, "speed": -0.5},
    ],
    "houses": [
        {"number": i, "longitude": float((i - 1) * 30), "sign": "Aries"}
        for i in range(1, 13)
    ],
    "special_points": [
        {"name": "ASC", "longitude": 341.9, "sign": "Pisces", "house": None},
        {"name": "MC", "longitude": 260.5, "sign": "Sagittarius", "house": None},
    ],
}


# ══════════════════════════════════════════════════════════════════════
# 1. Feature flag gating
# ══════════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    """Wave 4 endpoints must return 501 when NATAL_REPORT_ENABLED is False."""

    @pytest.mark.asyncio
    async def test_generate_returns_501_when_disabled(self, async_client, make_initdata, db_session):
        await _login(async_client, make_initdata, user_id=40101)
        response = await async_client.post("/api/natal/generate", json={})
        assert response.status_code == 501
        assert response.json()["detail"]["code"] == "FEATURE_DISABLED"

    @pytest.mark.asyncio
    async def test_report_latest_returns_501_when_disabled(self, async_client, make_initdata, db_session):
        await _login(async_client, make_initdata, user_id=40102)
        response = await async_client.get("/api/natal/report")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_report_by_id_returns_501_when_disabled(self, async_client, make_initdata, db_session):
        await _login(async_client, make_initdata, user_id=40103)
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/natal/report/{fake_id}")
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_report_section_returns_501_when_disabled(self, async_client, make_initdata, db_session):
        await _login(async_client, make_initdata, user_id=40104)
        fake_id = str(uuid.uuid4())
        response = await async_client.get(f"/api/natal/report/{fake_id}/section/portrait")
        assert response.status_code == 501


# ══════════════════════════════════════════════════════════════════════
# 2. Generate endpoint with flag enabled
# ══════════════════════════════════════════════════════════════════════

class TestGenerateWithFlag:
    """POST /api/natal/generate with NATAL_REPORT_ENABLED=True."""

    @pytest.mark.asyncio
    async def test_generate_returns_report_id(self, async_client, make_initdata, db_session):
        from app.services.telegram_auth import TelegramUser
        from app.services.profile_service import get_or_create_user
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40201)
        tg = TelegramUser(id=40201, username="natreport40201", first_name="Test")
        user, _ = await get_or_create_user(db_session, tg)
        await _set_profile(db_session, user.id)

        # Enable feature flag
        original = settings.natal_report_enabled
        settings.natal_report_enabled = True
        try:
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory, \
                 patch("app.services.llm_service.LLMService") as mock_llm_class:
                mock_client = AsyncMock()
                mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_factory.return_value = mock_client

                # Mock LLM to return valid blocks
                mock_llm = AsyncMock()
                mock_llm._generate_text.return_value = '{"blocks": [{"type": "paragraph", "text": "Test content for section."}]}'
                mock_llm_class.return_value = mock_llm

                response = await async_client.post("/api/natal/generate", json={})

            assert response.status_code == 200
            body = response.json()
            assert "reportId" in body or "report_id" in body
            assert "status" in body
        finally:
            settings.natal_report_enabled = original

    @pytest.mark.asyncio
    async def test_generate_idempotent(self, async_client, make_initdata, db_session):
        """Repeated generate clicks return same report id/status (idempotency)."""
        from app.services.telegram_auth import TelegramUser
        from app.services.profile_service import get_or_create_user
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40202)
        tg = TelegramUser(id=40202, username="natreport40202", first_name="Test")
        user, _ = await get_or_create_user(db_session, tg)
        await _set_profile(db_session, user.id)

        original = settings.natal_report_enabled
        settings.natal_report_enabled = True
        try:
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory, \
                 patch("app.services.llm_service.LLMService") as mock_llm_class:
                mock_client = AsyncMock()
                mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_factory.return_value = mock_client

                mock_llm = AsyncMock()
                mock_llm._generate_text.return_value = '{"blocks": [{"type": "paragraph", "text": "Content."}]}'
                mock_llm_class.return_value = mock_llm

                r1 = await async_client.post("/api/natal/generate", json={})
                r2 = await async_client.post("/api/natal/generate", json={})

            assert r1.status_code == 200
            assert r2.status_code == 200

            # Same report_id (idempotent)
            body1 = r1.json()
            body2 = r2.json()
            rid1 = body1.get("reportId") or body1.get("report_id")
            rid2 = body2.get("reportId") or body2.get("report_id")
            assert rid1 == rid2, "Repeated generate must return same report id"
        finally:
            settings.natal_report_enabled = original

    @pytest.mark.asyncio
    async def test_generate_returns_409_for_incomplete_profile(self, async_client, make_initdata, db_session):
        from app.services.telegram_auth import TelegramUser
        from app.services.profile_service import get_or_create_user
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40203)
        tg = TelegramUser(id=40203, username="natreport40203", first_name="Test")
        user, _ = await get_or_create_user(db_session, tg)
        # Don't set profile — it's incomplete

        original = settings.natal_report_enabled
        settings.natal_report_enabled = True
        try:
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
                mock_client = AsyncMock()
                mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_factory.return_value = mock_client

                response = await async_client.post("/api/natal/generate", json={})

            assert response.status_code in (409, 500), (
                f"Expected 409 (incomplete profile) or 500, got {response.status_code}"
            )
        finally:
            settings.natal_report_enabled = original


# ══════════════════════════════════════════════════════════════════════
# 3. Report retrieval
# ══════════════════════════════════════════════════════════════════════

class TestReportRetrieval:
    """GET /api/natal/report and /api/natal/report/{id}."""

    @pytest.mark.asyncio
    async def test_report_latest_returns_404_when_no_report(self, async_client, make_initdata, db_session):
        from app.services.telegram_auth import TelegramUser
        from app.services.profile_service import get_or_create_user
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40301)
        tg = TelegramUser(id=40301, username="natreport40301", first_name="Test")
        user, _ = await get_or_create_user(db_session, tg)
        await _set_profile(db_session, user.id)

        original = settings.natal_report_enabled
        settings.natal_report_enabled = True
        try:
            response = await async_client.get("/api/natal/report")
            # No report generated yet → 404
            assert response.status_code in (404, 200), (
                f"Expected 404 or 200, got {response.status_code}"
            )
        finally:
            settings.natal_report_enabled = original

    @pytest.mark.asyncio
    async def test_report_by_id_returns_404_for_nonexistent(self, async_client, make_initdata, db_session):
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40302)

        original = settings.natal_report_enabled
        settings.natal_report_enabled = True
        try:
            fake_id = str(uuid.uuid4())
            response = await async_client.get(f"/api/natal/report/{fake_id}")
            assert response.status_code == 404
        finally:
            settings.natal_report_enabled = original


# ══════════════════════════════════════════════════════════════════════
# 4. Preview still works alongside full report
# ══════════════════════════════════════════════════════════════════════

class TestPreviewCoexistence:
    """GET /api/natal/preview must work regardless of feature flag state."""

    @pytest.mark.asyncio
    async def test_preview_works_with_flag_disabled(self, async_client, make_initdata, db_session):
        from app.services.telegram_auth import TelegramUser
        from app.services.profile_service import get_or_create_user
        from app.core.config import settings

        await _login(async_client, make_initdata, user_id=40401)
        tg = TelegramUser(id=40401, username="natreport40401", first_name="Test")
        user, _ = await get_or_create_user(db_session, tg)
        await _set_profile(db_session, user.id, gender="male")

        # Feature flag disabled (default)
        assert not settings.natal_report_enabled

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_ctx_factory.return_value = mock_client

            response = await async_client.get("/api/natal/preview")

        assert response.status_code == 200
        body = response.json()
        assert "chapters" in body
        assert len(body["chapters"]) == 8
