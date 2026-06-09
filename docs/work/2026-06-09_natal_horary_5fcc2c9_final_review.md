# Final review: Natal/Horary follow-up closure

Date: 2026-06-09
Reviewed commit: 5fcc2c9
Previous review: `docs/work/2026-06-09_natal_horary_bb65453_review.md`
Verdict: ACCEPTED

## Scope reviewed

Commit message: `final follow-up: priority, score pills, happy-path tests`.

Changed files:

- `components/readings/horary/horary-form.tsx`
- `components/readings/natal-preview/planets-row.tsx`
- `components/readings/natal-preview/spheres-strip.tsx`
- `__tests__/horary/horary-form-submit.test.tsx`
- `__tests__/horary/horary-screen-flow.test.tsx`

This final packet targets the remaining follow-up items from the previous review:

1. fix invalid blocked-reason priority;
2. remove/soften technical score pills;
3. add horary happy-path create test;
4. add polling-start test after create.

## Findings

### F1 — blocked reason priority fixed

Status: ACCEPTED

`HoraryForm.handleSubmit()` now checks invalid reasons in product-friendly order:

1. text too short / empty;
2. missing question place;
3. no spendable credit.

This means first empty-form submit now tells the user to write the question first, instead of leading with location or credits.

### F2 — planet score pills removed

Status: ACCEPTED

`PlanetsRow` no longer renders technical score pills like `+4.96` in the card header.

The planet card now focuses on:

- planet name;
- sign/house line;
- human-readable description.

This better matches the landing goal: premium teaser, not debug/scoring dashboard.

### F3 — sphere scores softened to rank

Status: ACCEPTED

`SpheresStrip` now shows `#rank` instead of raw numeric score. This preserves ranking information without exposing technical scoring internals.

### F4 — horary happy-path test added

Status: ACCEPTED

`__tests__/horary/horary-screen-flow.test.tsx` covers the main successful flow:

- mocks quota/profile/list/create/get;
- renders `HoraryScreen`;
- fills a valid question;
- submits;
- asserts `createHoraryQuestion()` is called;
- checks payload fields:
  - text;
  - timezone;
  - questionLat;
  - questionLon;
  - idempotencyKey;
- asserts processing UI appears.

This protects the core user path: valid click → create → visible processing.

### F5 — polling-start test added

Status: ACCEPTED

The same test file verifies that after successful create, `getHoraryQuestion("q-new")` is called.

This is enough for the immediate follow-up requirement: successful create is not left passive; polling starts.

### F6 — existing blocked-reason tests updated

Status: ACCEPTED

`horary-form-submit.test.tsx` was adjusted for the new priority order:

- location-missing test now uses valid text;
- no-credit test now uses valid text and location;
- short-text test still verifies `Напиши вопрос`.

This matches the intended validation order.

## Verification evidence

User-provided local evidence:

- Frontend tests: `504 passed`.
- Backend tests: `277 passed`.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `5fcc2c9`.
- No combined GitHub status checks were visible for the commit.

## Residual notes

No blockers found.

Minor future hardening, not required now:

1. Add an assertion for selected horary category in the happy-path payload if category selection is critical.
2. After next real-device screenshot pass, visually verify the natal page no longer feels technical or cluttered.
3. If CI becomes available, require visible GitHub status checks for this flow.

## Final decision

ACCEPTED.

The wave can be closed. The horary submit UX is no longer a silent no-op, happy-path create and polling are covered by tests, English signs were already fixed in the previous packet, and technical natal score pills were softened/removed.
