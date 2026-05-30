---
id: packet-w-access.2
status: active
wave: W-ACCESS.2
last_review: 2026-05-30
---
# W-ACCESS.2 — Referral codes + signup hook

status: completed
phase: PHASE-ACCESS
wave: W-ACCESS.2
modules: M-REFERRAL-SERVICE

---

## Decision

Implement referral system:
1. **Referral codes** — unique codes per user for sharing
2. **Signup hook** — grants access days when new user signs up with referral code
3. **Referral tracking** — tracks referrer → referee relationships

**Why:** Referral system drives user acquisition. Both referrer and referee get access days, creating viral growth loop.

---

## Acceptance Criteria

- [x] Referral code generation (unique per user)
- [x] Signup endpoint accepts referral code
- [x] Successful referral grants days to both referrer and referee
- [x] Referral tracking in database

---

## Evidence

- File: `apps/api/app/api/referral.py` — referral endpoints
- File: `apps/api/app/schemas/referral.py` — referral schemas
- File: `apps/api/tests/test_referral_endpoints.py` — referral tests
- Implementation: Signup hook in auth service grants access days

---

## Negative Tests

- [ ] Invalid referral code must not grant access days
- [ ] Self-referral must be rejected
- [ ] Duplicate referral code usage must be rejected
