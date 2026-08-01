# Packet 02 — event-first impulse drilldown

## Packet title

Today impulse drilldown: exact event before sphere context

## Phase / Wave

W-TODAY-MOBILE-READABILITY / 02

## Modules

- M-TODAY-CONVERGENCE-IMPULSES
- M-TODAY-IMPULSE-DRILLDOWN
- M-TODAY-CONVERGENCE-NARRATIVE

## Goal

Make each impulse explain the exact event first, with a readable mobile hierarchy and a non-blocking unavailable narrative state. Resolve `events[].title` by `eventId`; show `meaning` when present; keep sphere/period context collapsed or secondary.

## Exact write scope

- `components/today-convergence/impulses-list.tsx`
- `components/today-convergence/impulse-drilldown-sheet.tsx`
- `components/today-convergence/today-narrative.tsx`
- the narrowest existing Today component tests needed for the new hierarchy

## Frozen / out of scope

- No API/Pydantic/OpenAPI schema changes.
- No changes to event calculation or narrative generation prompt.
- No changes to calendar.
- No baseline PNG changes.

## Must preserve

- Exact event fact fields, peak/start/end precision, polarity, sphere, and action.
- Existing modal accessibility (`role=dialog`, `aria-modal`, labelled title, Escape).
- Existing public test IDs unless a new structural ID is added.
- No fabricated personalized claims when `meaning` is absent.

## Verification

`npx vitest run components/today-convergence/__tests__/today-screen.test.tsx`

Also run `git diff --check` and frontend GRACE marker check.

## Expected evidence

Targeted tests green; event title rendered from payload ledger; unavailable state leaves deterministic facts visible; no long expanded technical block above the event explanation.

## Escalation

If event-specific deterministic fallback copy or a contract field is required, stop and report instead of changing backend in this packet.

## No-commit rule

Do not commit or push. The reviewer will integrate and commit.
