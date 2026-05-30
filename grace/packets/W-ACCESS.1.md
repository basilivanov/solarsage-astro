---
id: packet-w-access.1
status: active
wave: W-ACCESS.1
last_review: 2026-05-30
---
# W-ACCESS.1 — access_ledger, access_service.can_access_day

status: completed
phase: PHASE-ACCESS
wave: W-ACCESS.1
modules: M-ACCESS-SERVICE

---

## Decision

Create access control system with:
1. **access_ledger** table — tracks user access grants (free days, referral unlocks)
2. **AccessService.can_access_day()** — checks if user can access specific date

**Why:** Freemium model requires access control. Ledger provides audit trail. Service method centralizes access logic for use across endpoints.

---

## Acceptance Criteria

- [x] `access_ledger` table created (user_id, date, grant_type, granted_at)
- [x] `AccessService.can_access_day()` method implemented
- [x] Access checks consider free days + referral unlocks
- [x] Tests verify access logic

---

## Evidence

- File: `apps/api/app/services/access_service.py` — access service (7.1KB)
- File: `apps/api/app/schemas/access.py` — access schemas
- File: `apps/api/tests/test_access_service.py` — access service tests
- Migration: `alembic/versions/0002_add_access_ledger.py` — access_ledger table

---

## Negative Tests

- [ ] User without access must not retrieve day payload
- [ ] Expired access grants must not allow access
- [ ] Invalid date must return access denied
