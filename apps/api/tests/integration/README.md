# Integration Tests (W-TEST-1)

Integration tests cover complete user flows against real DB with test fixtures.

## Test Suites

### test_user_flow.py
- `test_complete_user_flow` — signup → onboard → day view → referral claim
- `test_calendar_navigation_flow` — signup → onboard → calendar → day view
- `test_access_expiration_flow` — referral expires → preview mode

## Running

```bash
# Run all integration tests
pytest apps/api/tests/integration/ -v

# Run with marker
pytest -m integration -v

# Run specific test
pytest apps/api/tests/integration/test_user_flow.py::test_complete_user_flow -v
```

## Coverage

Integration tests cover:
- ✅ Auth flow (Telegram login)
- ✅ Onboarding flow (profile creation)
- ✅ Day view flow (TodayPayload generation)
- ✅ Calendar flow (3-month grid)
- ✅ Referral flow (claim bonus)
- ✅ Access control (referral_bonus, subscription, expiration)

## Architecture

Tests use:
- In-memory SQLite database (via `db_session` fixture)
- `async_client` fixture (httpx.AsyncClient over ASGI)
- `make_initdata` fixture (generates valid Telegram initData with HMAC)

Each test is isolated with fresh DB state.
