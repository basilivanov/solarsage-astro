---
id: packet-w-access.3
status: active
wave: W-ACCESS.3
last_review: 2026-05-30
---
# W-ACCESS.3 — Preview/locked TodayPayload + soft lock UI

status: completed
phase: PHASE-ACCESS
wave: W-ACCESS.3
modules: M-TODAY-SERVICE, M-FRONTEND-LOCKED-DAY

---

## Decision

Implement soft lock UX:
1. **Preview payload** — locked days return partial `TodayPayload` with preview content
2. **Locked UI component** — frontend shows preview + unlock CTA for locked days
3. **Access check integration** — today endpoint checks access before returning full payload

**Why:** Soft lock shows value before paywall. Preview content teases full reading, increasing conversion. Better UX than hard block.

---

## Acceptance Criteria

- [x] Today endpoint returns preview payload for locked days
- [x] Preview includes day status + top signal (no full reading)
- [x] `LockedDay` component shows preview + unlock CTA
- [x] Access check integrated in today endpoint

---

## Evidence

- File: `apps/api/app/services/today_service.py` — preview payload generation
- File: `components/grace/LockedDay.tsx` — locked day UI component
- File: `apps/api/tests/test_day_endpoints.py` — locked day tests
- Implementation: Today endpoint checks `access_service.can_access_day()` before returning full payload

---

## Negative Tests

- [ ] Locked day must not leak full reading content
- [ ] Preview must not include sensitive personal insights
- [ ] Unlock CTA must redirect to referral/payment flow
