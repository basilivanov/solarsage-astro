---
id: packet-w-test.1
status: active
wave: W-TEST-1
last_review: 2026-05-30
---
# W-TEST-1 — Backend integration tests with authenticated_client fixture

status: completed
phase: PHASE-TEST
wave: W-TEST-1
modules: M-API-TESTS

---

## Decision

Create backend integration test suite with:
1. **authenticated_client fixture** — pytest fixture providing authenticated test client
2. **Integration tests** — tests covering API endpoints with real database
3. **Test isolation** — each test runs in isolated transaction

**Why:** Unit tests verify individual components, but integration tests verify the full request/response cycle. Authenticated fixture enables testing protected endpoints.

---

## Acceptance Criteria

- [x] `authenticated_client` fixture in `conftest.py`
- [x] Integration tests for all major endpoints (auth, profile, day, calendar, referral)
- [x] Tests use real database with transaction rollback
- [x] All integration tests pass

---

## Evidence

- File: `apps/api/tests/conftest.py` — test fixtures including `authenticated_client`
- File: `apps/api/tests/test_auth_endpoints.py` — auth endpoint tests
- File: `apps/api/tests/test_profile_endpoints.py` — profile endpoint tests
- File: `apps/api/tests/test_day_endpoints.py` — day endpoint tests
- File: `apps/api/tests/test_calendar_endpoints.py` — calendar endpoint tests
- File: `apps/api/tests/test_referral_endpoints.py` — referral endpoint tests
- Test: All backend integration tests pass

---

## Negative Tests

- [ ] Unauthenticated requests to protected endpoints must return 401
- [ ] Invalid tokens must be rejected
- [ ] Test database must be isolated from dev/prod databases
