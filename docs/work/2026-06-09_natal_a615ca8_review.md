# Review: Natal + Gender blocker fixes

Date: 2026-06-09
Reviewed commit: a615ca87910fe521b95bf094790a775817abfeaa
Previous review: `docs/board/2026-06-09_gender_natal_751cb1b_review.md`
Verdict: REJECTED

## Scope reviewed

Commit message: `fix: natal preview review B1-B6 blockers`.

Changed files:

- apps/api/app/api/natal.py
- apps/api/app/services/natal_service.py
- apps/api/app/services/profile_service.py
- apps/api/tests/integration/test_cache.py
- apps/api/tests/integration/test_locked_day.py
- apps/api/tests/integration/test_user_flow.py
- apps/api/tests/test_calendar_endpoints.py
- apps/api/tests/test_critical_gaps.py
- apps/api/tests/test_llm_fallback.py
- apps/api/tests/test_natal_preview.py
- components/onboarding/onboarding-flow.tsx
- components/onboarding/step-gender.tsx
- lib/api/natal.ts
- lib/contracts/profile.ts
- lib/profile.ts
- lib/reducers/onboarding-reducer.ts

## Positive findings

### B1 — gender onboarding mostly implemented

Status: PARTIAL

A real `StepGender` was added with the requested copy and binary options:

- title: `Ты мужчина или женщина?`
- options: `Мужчина`, `Женщина`

The onboarding reducer now includes `gender` between `birthday` and `done`, and `finish()` sends `gender` into `updateProfile()`.

### B2 — profile incomplete parsing fixed

Status: ACCEPTED

`lib/api/natal.ts` now reads both nested FastAPI detail shape and top-level shape:

- `body.detail?.message || body.message`
- `body.detail?.missingFields || body.missingFields`

This fixes the missing-fields propagation problem.

### B3 — natal preview volume fixed

Status: ACCEPTED

The preview now returns:

- up to 7 spheres;
- 8 locked chapters.

This matches the mini-landing/natal preview scope.

### B4 — calculation stats bucket display fixed

Status: ACCEPTED

`total_factors_count` now includes all returned groups:

- planets;
- houses;
- aspects;
- spheres;
- special points;
- scoring factors;
- dignity factors.

`display_label` now follows the required buckets:

- `350+ факторов карты`;
- `300+ факторов карты`;
- `200+ факторов карты`;
- exact count.

### B5 — safe public natal errors fixed

Status: ACCEPTED

The natal API no longer returns raw exception text. It logs raw errors internally and returns safe public codes/messages:

- `NATAL_PREVIEW_FAILED`
- `SOLARSAGE_UNAVAILABLE`

### B6 — backend test coverage added

Status: PARTIAL

A new `test_natal_preview.py` covers important backend/API behavior:

- missing gender;
- missing birth coordinates;
- safe sidecar error;
- 99900 kopeck price;
- male/female wording;
- calculation stats bucket rules;
- 8 chapters;
- at least 5 spheres.

Coder-reported evidence in commit message: `277 passed, 2 skipped, 0 new failures`.

## Remaining blockers

### B1.1 — silent gender default remains in onboarding finish

Status: BLOCKER

`finish()` still silently defaults missing gender to `female`:

```ts
gender: state.gender ?? "female"
```

This violates the explicit product decision and the failure-handling canon: gender must be chosen by the user, not guessed by the application.

Even if the normal UI path currently sets gender before `done`, the save path itself must not contain a silent fallback. If an edge case, reducer event, future refactor, test setup, localStorage restore, or skipped path reaches `finish()` with `state.gender === null`, the app will persist the user as female and generate wrong gendered text.

Required fix:

1. Remove `?? "female"`.
2. Guard `finish()`:
   - if `state.gender` is null, return to `gender` step or show validation error;
   - do not call `saveProfile()` or `updateProfile()`.
3. Add reducer/component test that `finish()` cannot persist gender when it was not selected.

### B6.1 — no frontend tests for onboarding and natal preview states

Status: BLOCKER

The previous review required frontend coverage for the UI parts of this packet. The current commit adds backend tests, but no frontend/component/page tests were added.

Still untested on frontend side:

- gender step is rendered in active onboarding flow;
- onboarding cannot finish without gender;
- `updateProfile()` receives selected gender;
- `fetchNatalPreview()` preserves nested `detail.missingFields`;
- `/readings/natal` renders `profile_incomplete` with missing fields;
- CTA is disabled and does not route to payment;
- successful preview renders 8 chapters and calculation stats.

Required fix:

- Add frontend tests for gender onboarding and natal preview state rendering.
- At minimum, add tests around `onboarding-flow`/reducer and `lib/api/natal.ts` error parsing.

## Major notes

### R1 — `is_onboarded` still does not require full natal-ready profile

`profile_service.update_profile()` now requires `birthday + birth_city + gender` before setting `is_onboarded=true`, but it still does not require birth coordinates, birth timezone, or birth time.

This is not a new blocker for this specific follow-up because `/api/natal/preview` itself correctly returns `409 profile_incomplete` when birth data is missing. But it can still create a confusing state where a user is considered onboarded by the shell while natal immediately asks for missing fields.

Recommended future hardening:

- define separate flags/states: `is_onboarded` vs `is_natal_ready`;
- or require all MVP-required birth fields for `is_onboarded`.

### R2 — CI not visible through connector

No GitHub Actions workflow runs or combined statuses were visible for the reviewed commit via connector.

## Verification evidence

Connector-visible CI evidence:

- no workflow runs visible for `a615ca87910fe521b95bf094790a775817abfeaa`;
- no combined status checks visible for the commit.

Coder/local evidence from commit message:

- `277 passed, 2 skipped, 0 new failures`.

## Final decision

REJECTED.

The core natal backend and mini-landing blockers are mostly fixed. But acceptance still requires two small follow-ups:

1. remove the silent `female` fallback from onboarding save;
2. add frontend tests for gender onboarding / natal preview UI and error parsing.

After that, this should be ready for acceptance.
