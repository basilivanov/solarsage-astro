# Review: Horary blocker fixes B1–B4

Date: 2026-06-09
Reviewed commit: 433db53be666b53a8821f8af09910d5506ab6e92
Base commit: e8066a8f0c71aed4f3a727a24f241794f2cb0e01
Previous review: `docs/work/2026-06-09_horary_7e24f70_review.md`
Verdict: REJECTED

## Scope reviewed

Commit message: `fix: horary review B1-B4 blockers`.

Changed files:

- apps/api/app/api/day.py
- apps/api/app/api/horary.py
- apps/api/app/schemas/horary.py
- apps/api/app/services/today_service.py
- apps/api/tests/test_day_no_birthday_fallback.py
- apps/api/tests/test_horary_answer_quality.py
- apps/api/tests/test_horary_api_error_mapping.py
- apps/api/tests/test_horary_failure_metadata.py
- apps/api/tests/test_horary_schema_strictness.py
- lib/api/horary.ts

## Positive findings

### B2 — birthday-location fallback removed

Status: ACCEPTED

The dangerous fallback from `birth_lat/birth_lon` to `birthday_lat/birthday_lon` was removed from both readiness checks and Today calculation.

- `day.py` now requires real `profile.birth_lat` and `profile.birth_lon`.
- `today_service.py` now raises `409` if birth coordinates are missing and passes only real birth coordinates to SolarSage.
- Regression tests were added in `test_day_no_birthday_fallback.py`.

### B3 — horary schema strictness restored

Status: ACCEPTED

The public schema is strict again:

- `VerdictCardBlock.confidence_label` is required.
- `VerdictCardBlock.confidence_explanation` is required.
- `TimingBlock.status` is required.

Backward compatibility is handled before response serialization by normalizing old stored blocks in `_normalize_horary_blocks()`.

### B4 — backend test coverage added

Status: PARTIALLY ACCEPTED

The commit adds backend tests for:

- day calculation no longer using birthday-location fallback;
- horary API empty/401/404 behavior;
- horary failure metadata persistence;
- horary schema strictness;
- adjusted horary answer quality fixture.

Coder-reported evidence in commit message: `267 passed, 2 skipped`.

Connector-visible CI still shows no workflow runs and no combined status checks for the commit.

## Remaining blocker

### B1 — Detail page still renders server/load failures as “Вопрос не найден”

Status: BLOCKER

The API client part of B1 is improved:

- `listHoraryQuestions()` now throws on non-OK instead of returning `[]`.
- `getHoraryQuestion()` now returns `null` only on `404`, and throws on other non-OK responses.

But the detail page still treats every thrown `getHoraryQuestion()` error as `loadError=true` and renders the same “Вопрос не найден” state:

```tsx
.catch((err) => {
  console.error("[HoraryAnswerPage] Error loading question:", err)
  setLoadError(true)
  setLoading(false)
})
...
if (loadError || !question) {
  return <...>Вопрос не найден...</...>
}
```

This means:

- `500` backend error;
- auth/session problem;
- network/server issue;
- contract/runtime API failure;

can still become a false user-facing “Вопрос не найден”. That was the core failure-handling issue in B1: do not replace real failures with plausible not-found/empty states.

Required fix:

1. Keep separate states:
   - `not_found` only when `getHoraryQuestion()` returns `null` from real 404;
   - `load_error` when `getHoraryQuestion()` throws.
2. Render honest load error copy for thrown errors, for example:
   - `Не удалось загрузить вопрос`;
   - `Попробуй ещё раз позже.`
3. Preserve `Вопрос не найден` only for real 404.
4. Add frontend test or at least component-level test for:
   - 404 → not found;
   - 500/401/network error → load error, not not-found.

## Major risk

### R1 — Frontend behavior is still not covered by frontend tests

The new commit adds backend tests, but no frontend tests changed. The previous review explicitly required frontend coverage for the changed async/error UI behavior.

This is especially important because the remaining B1 issue is in frontend state rendering, not backend API behavior.

Recommended tests:

- `listHoraryQuestions` non-OK does not become empty history without error state;
- detail page 404 renders not-found;
- detail page 500/network error renders load-error;
- processing detail page still polls and transitions.

## Verification evidence

Connector-visible CI evidence:

- No GitHub Actions workflow runs visible for `433db53be666b53a8821f8af09910d5506ab6e92`.
- No combined GitHub status checks visible for the commit.

Coder/local evidence from commit message:

- `267 passed, 2 skipped`.

## Final decision

REJECTED.

B2, B3, and backend-side B4 are fixed. The API client half of B1 is improved. But B1 is not fully fixed because the horary detail page still maps thrown load/server/API failures to the false “Вопрос не найден” state.

This needs one small frontend follow-up plus tests before acceptance.
