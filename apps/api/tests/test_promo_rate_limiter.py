# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROMO_RATE_LIMITER
# ROLE: Unit and integration tests for PromoRateLimiter service and API 429 rate limit integration.
# DEPENDENCIES: pytest, httpx, app.services.promo_rate_limiter, app.api.promo
# GRACE_ANCHORS: [TEST_PROMO_RATE_LIMITER]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROMO-RATE-LIMITER
# purpose: Validate 10-attempt rolling window, 11th attempt 429 with Retry-After header, window expiry restoration, shared preview/redeem bucket, per-user isolation, LRU eviction at 10,000 keys, concurrent call atomicity, and privacy safety (no token/hash in limiter state).
# owns:
#   - apps/api/tests/test_promo_rate_limiter.py
# inputs: AsyncClient, make_initdata, promo_rate_limiter
# outputs: pytest execution assertions
# dependencies:
#   - app.services.promo_rate_limiter (PromoRateLimiter, RateLimitResult, promo_rate_limiter)
# side_effects: in-memory limiter cache mutations
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-PROMO-RATE-LIMITER

# START_MODULE_MAP: M-TEST-PROMO-RATE-LIMITER
# public_entrypoints:
#   - test_limiter_10_attempts_allowed_11th_rejected_with_retry_after
#   - test_limiter_rolling_window_expiry_restores_allowance
#   - test_limiter_shared_preview_and_redeem_bucket
#   - test_limiter_per_user_isolation
#   - test_limiter_lru_capacity_eviction
#   - test_limiter_concurrent_asyncio_atomicity
#   - test_promo_api_http_429_integration_and_headers
#   - test_privacy_no_token_in_limiter_state
# owned_tests:
#   - apps/api/tests/test_promo_rate_limiter.py
# END_MODULE_MAP: M-TEST-PROMO-RATE-LIMITER

import asyncio
import uuid
import pytest
from httpx import AsyncClient

from app.services.promo_rate_limiter import PromoRateLimiter, promo_rate_limiter


@pytest.fixture(autouse=True)
def reset_global_rate_limiter():
    promo_rate_limiter.reset()
    yield
    promo_rate_limiter.reset()


def test_limiter_10_attempts_allowed_11th_rejected_with_retry_after() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(clock_fn=lambda: current_time)
    user_id = uuid.uuid4()

    # 10 attempts allowed
    for _ in range(10):
        res = limiter.check_and_record(user_id)
        assert res.allowed is True
        assert res.retry_after_seconds == 0

    # 11th attempt rejected
    res11 = limiter.check_and_record(user_id)
    assert res11.allowed is False
    assert res11.retry_after_seconds == 600


def test_limiter_rolling_window_expiry_restores_allowance() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(clock_fn=lambda: current_time)
    user_id = uuid.uuid4()

    for _ in range(10):
        limiter.check_and_record(user_id)

    assert limiter.check_and_record(user_id).allowed is False

    # Advance clock by 601 seconds (past 10 min window)
    current_time += 601.0

    res = limiter.check_and_record(user_id)
    assert res.allowed is True


def test_limiter_shared_preview_and_redeem_bucket() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(clock_fn=lambda: current_time)
    user_id = uuid.uuid4()

    # 5 preview + 5 redeem
    for _ in range(5):
        assert limiter.check_and_record(user_id).allowed is True
    for _ in range(5):
        assert limiter.check_and_record(user_id).allowed is True

    # 11th overall attempt rejected
    assert limiter.check_and_record(user_id).allowed is False


def test_limiter_per_user_isolation() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(clock_fn=lambda: current_time)
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    # User A reaches limit
    for _ in range(10):
        limiter.check_and_record(user_a)

    assert limiter.check_and_record(user_a).allowed is False

    # User B is unaffected
    assert limiter.check_and_record(user_b).allowed is True


def test_limiter_lru_capacity_eviction() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(max_keys=100, clock_fn=lambda: current_time)

    # Fill 100 users
    user_keys = [uuid.uuid4() for _ in range(100)]
    for u in user_keys:
        limiter.check_and_record(u)

    assert len(limiter._cache) == 100
    first_user = user_keys[0]
    assert first_user in limiter._cache

    # Add 101st user -> evicts oldest (first_user)
    new_user = uuid.uuid4()
    limiter.check_and_record(new_user)

    assert len(limiter._cache) == 100
    assert first_user not in limiter._cache
    assert new_user in limiter._cache


@pytest.mark.asyncio
async def test_limiter_concurrent_asyncio_atomicity() -> None:
    current_time = 1000.0
    limiter = PromoRateLimiter(clock_fn=lambda: current_time)
    user_id = uuid.uuid4()

    async def call_limiter():
        return limiter.check_and_record(user_id)

    # 20 concurrent coroutines
    results = await asyncio.gather(*[call_limiter() for _ in range(20)])

    allowed_count = sum(1 for r in results if r.allowed)
    rejected_count = sum(1 for r in results if not r.allowed)

    assert allowed_count == 10
    assert rejected_count == 10


@pytest.mark.asyncio
async def test_promo_api_http_429_integration_and_headers(
    async_client: AsyncClient, make_initdata
) -> None:
    raw_init = make_initdata(user_id=887700, username="rate_user")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    # First 10 preview attempts return 400 INVALID_CODE
    for _ in range(10):
        resp = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kd"})
        assert resp.status_code == 400
        assert resp.headers.get("Cache-Control") == "no-store"

    # 11th attempt returns 429 RATE_LIMITED
    resp11 = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kd"})
    assert resp11.status_code == 429
    assert resp11.headers.get("Cache-Control") == "no-store"
    assert "Retry-After" in resp11.headers
    assert int(resp11.headers["Retry-After"]) > 0

    err_detail = resp11.json()["detail"]
    assert err_detail["code"] == "RATE_LIMITED"
    assert "Слишком много попыток" in err_detail["message"]

    # Unauthenticated request still returns 401 Unauthorized
    from app.main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as unauth_client:
        resp_unauth = await unauth_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kd"})
        assert resp_unauth.status_code == 401


def test_privacy_no_token_in_limiter_state() -> None:
    limiter = PromoRateLimiter()
    user_id = uuid.uuid4()
    limiter.check_and_record(user_id)

    # Key is strictly user UUID, value is list of floats
    assert user_id in limiter._cache
    val = limiter._cache[user_id]
    assert isinstance(val, list)
    for t in val:
        assert isinstance(t, float)
