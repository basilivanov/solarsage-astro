# Review: W-NATAL-REDESIGN + W-HORARY-SUBMIT-FIX

Date: 2026-06-09
Reviewed commit: 08e5e1a65f8a6c0261dfc1dc538fd045f4c045fd
Base commit: 062e9b9d9858180ccd7d533330f825db455809b9
Verdict: REJECTED

## Scope reviewed

Commit message: `natal redesign + horary submit fix`.

Changed files:

- `app/(grace)/readings/natal/page.tsx`
- `apps/api/app/services/natal_service.py`
- `components/readings/horary/horary-form.tsx`
- `components/readings/horary/horary-screen.tsx`
- `components/readings/natal-preview/calculation-depth.tsx`
- `components/readings/natal-preview/hero-section.tsx`
- `components/readings/natal-preview/locked-chapters.tsx`
- `components/readings/natal-preview/planets-row.tsx`
- `components/readings/natal-preview/spheres-strip.tsx`
- `lib/api/horary.ts`

## Positive findings

### P1 — Horary submit no longer silently ignores invalid clicks

Status: ACCEPTED

`HoraryForm` now keeps the button clickable as `type="submit"` and handles invalid form clicks inside `handleSubmit()`.

It now shows a visible blocked reason for invalid state:

- no credit → `Нужен доступный хорарный вопрос`;
- no coordinates/place → `Укажи место вопроса`;
- short question → `Напиши вопрос (минимум 5 символов)`.

This fixes the original UX issue where the disabled button gave no feedback.

### P2 — Horary API errors are shown inline

Status: ACCEPTED

`HoraryScreen` now stores `submitError`, passes it into `HoraryForm`, and shows both inline error and destructive toast when create fails.

`createHoraryQuestion()` now throws `HoraryApiError` instead of a plain `Error`, preserving status/code semantics.

### P3 — Horary loading label improved

Status: ACCEPTED

Submit label now says `Считаем карту...`, which better matches the actual user expectation.

### P4 — Natal top-level layout is materially improved

Status: PARTIAL

The page structure is cleaner than before:

- hero;
- personal hook;
- compact highlights;
- calculation depth;
- spheres;
- planets;
- locked chapters;
- bullets;
- CTA.

`CalculationDepth` no longer makes the weak `50 факторов карты` headline the main product proof and instead shows a structured list of what is considered.

Spheres and planets are limited to top 3 by default and can expand.

Locked chapters are visually lighter compact rows.

## Blockers

### B1 — English zodiac signs still leak in the planets UI

Status: BLOCKER

The TZ explicitly required no visible English signs in the natal UI.

Backend `_build_planets()` correctly builds a Russian description using `sign_ru`, but it still returns the raw English `sign` field:

```python
sign=sign
```

Frontend `PlanetsRow` then renders that raw field directly:

```tsx
{[planet.sign, planet.house ? `${planet.house} дом` : null].filter(Boolean).join(" · ")}
```

Result: planet cards can still show user-visible English zodiac names such as `Scorpio`, `Leo`, `Libra`, `Sagittarius`.

Required fix:

1. Either return Russian sign labels from backend for `NatalPlanetPreview.sign`, or add a frontend sign translation helper in `PlanetsRow`.
2. Add regression test that planet cards do not show English signs.
3. Check all visible natal UI for English zodiac names, not just hero/highlights.

### B2 — The claimed new tests are not present in this commit

Status: BLOCKER

The implementation commit does not include test files in the diff. The changed files list contains no `__tests__` or backend test files.

The TZ required tests for both parts:

Natal:

- no English visible in natal UI;
- Russian signs in hero/planet cards;
- compact sections;
- 8 full-report topics;
- CTA safety.

Horary:

- button click triggers submit;
- invalid form shows blocked reason;
- create API error shows real message;
- successful create inserts question;
- processing card appears / polling starts.

User-provided test counts are useful evidence, but without changed tests in the commit they do not prove coverage for this new behavior.

Required fix:

1. Add frontend tests for `HoraryForm` invalid click and API error display.
2. Add frontend tests for natal no-English signs, especially planets.
3. Add/adjust tests for compact locked chapters / CTA state if not already covered elsewhere.
4. Provide test command evidence again.

## Major notes

### R1 — Invalid horary reason priority may be confusing

Current invalid-click reason checks no credit, then missing place, then short text.

If the user opens the blank form and taps submit, and both text and place are missing, the UI will show `Укажи место вопроса` before `Напиши вопрос`.

This may be acceptable if location is the real observed blocker, but product-wise the first empty-form click usually should say `Напиши вопрос` first.

Recommended follow-up:

- If `text.trim().length < 5`, show text reason before location reason.
- Or show all missing reasons at once.

### R2 — Technical score pills still appear in planets and spheres

The redesign reduced clutter, but planets still show score pills like `+4.96` when score exists, and spheres still show numeric score.

The TZ said scores should only be shown if they clearly help. This is not a blocker if the screenshots look good, but product review should verify visually.

### R3 — `CalculationDepth` accepts `stats` but no longer uses it

The component receives `stats` but renders a static list. That is fine for Path B, but consider removing the unused prop or adding a small accessible detail if needed.

## Verification evidence

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `08e5e1a65f8a6c0261dfc1dc538fd045f4c045fd`.
- No combined GitHub status checks were visible for the commit.

User-provided local evidence:

- Frontend: `496 passed`.
- Backend: `277 passed`.

## Final decision

REJECTED.

Horary submit UX is directionally fixed and should be close. Natal redesign is improved, but cannot be accepted while English zodiac signs still leak in planet cards and the claimed new test coverage is not present in the implementation commit.

Required next packet:

1. translate planet signs in visible UI;
2. add tests for no-English natal UI and horary invalid/API-error submit states;
3. optionally adjust invalid-click reason priority.
