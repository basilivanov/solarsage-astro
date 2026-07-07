# Wave 09 Rework 01 — Valid Evidence Only

> Role: implementer/auditor. Do not change production UI code in this rework.

## Goal

Fix the Wave 09 audit evidence. The previous report is rejected because screenshots were auth/loading screens and visual conclusions were not supported by valid artifacts.

This rework must produce valid, authenticated route evidence and a corrected technical classification. Do not make subjective visual-parity conclusions if your model/tooling cannot inspect images.

## Read First

- Original TZ: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/00_TZ.md`
- Architect review: `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/02_arch_review.md`

The architect review governs this rework.

## Non-Negotiable Constraints

- Do not edit production app/runtime code.
- Do not edit components, app routes, API code, contracts, tests, or configs outside this Wave 09 docs directory.
- Do not run destructive git operations.
- Do not force push.
- Do not claim "visual parity" from screenshots you cannot inspect.
- Do not say "no blockers" if any route screenshot is auth/loading/error.
- Do not classify 3001 local calculations as real backend-backed data.
- Commit only `docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/**`.

## Key Process Change

Your task is **evidence collection and technical audit**, not final visual judgment.

For each route, provide:

1. validated screenshot path,
2. DOM sentinel proof,
3. file/code comparison,
4. data-safety classification,
5. "architect visual review pending" when visual judgment is needed.

## Screenshot Validity Rules

A screenshot is valid only if all are true:

- The page is not showing `Авторизация...`.
- The page is not showing an auth error.
- The page has the expected route-specific sentinel text or `data-testid`.
- The page URL is the expected route.

If a route cannot pass these checks, record it as `BLOCKED_AUTH_CAPTURE` with exact logs and do not use that screenshot for visual conclusions.

## Auth / Session Capture Guidance

Use existing real-auth Playwright helpers where possible:

- `e2e/fixtures.ts`
- `scripts/generate-telegram-test-initdata.py`

The fixture already:

- generates HMAC-valid Telegram initData,
- posts to `/api/auth/telegram`,
- seeds `grace_session_v2`,
- injects `window.Telegram.WebApp`,
- sets up the page before app scripts run.

You may create a temporary script under the Wave 09 docs directory if needed, for example:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/capture-evidence.mjs`

If you create such a script, it is allowed only as an audit artifact and must not be imported by app code.

For `3001`, if the mock-preview app uses the same auth behavior, use the same Telegram/session approach against `baseURL=http://127.0.0.1:3001` and API base `http://127.0.0.1:8000`.

## Required Route Sentinels

Use route-specific DOM checks before screenshots. Prefer stable `data-testid` where present; otherwise use text that proves the route rendered.

Minimum sentinels:

| Route | 3001/3002 Sentinel Examples |
|-------|-----------------------------|
| `/day/2026-07-05` | not `Авторизация...`; `today-screen` if present; text such as `14 дней бесплатного доступа`, `Конкретно сегодня`, `Сегодня важно`, or actual rendered day content |
| `/calendar` | not `Авторизация...`; calendar root/grid; visible month/day cells |
| `/profile` | not `Авторизация...`; profile root; visible profile/account/service rows |
| `/readings` | not `Авторизация...`; readings root; visible readings cards |
| `/readings/horary` | not `Авторизация...`; horary root/form/quota |
| `/readings/natal` | not `Авторизация...`; natal root/hero/preview |

For each route, record:

- URL after navigation,
- matched sentinel,
- whether auth/loading text was absent,
- screenshot path.

## Correct Data-Safety Classification

Re-audit 3001 components for runtime data/calculation safety.

For each 3001 component relevant to the six route families, classify:

- `PRESENTATION_ONLY_SAFE` — markup/styles only; data supplied by parent via real contract.
- `PORT_PRESENTATION_REPLACE_DATA` — UI can be ported, but local mock/demo/calculation logic must be removed and replaced with backend/adapter data.
- `REQUIRES_BACKEND_CONTRACT` — cannot honestly render until backend/Pydantic/OpenAPI/frontend adapter contract exists.
- `TEST_ONLY_OR_DEMO_ONLY` — do not port to production runtime.
- `KEEP_CURRENT_REAL_IMPLEMENTATION` — current main has a real-data implementation that should be preserved.

Explicitly inspect and classify at least:

### `/day`

- `day-summary-card.tsx`
- `concrete-day-advice.tsx`
- `evening-checkin-reminder.tsx`
- `astro-history-widget.tsx`
- `moon-phase-widget.tsx`
- `planetary-day-widget.tsx`
- `void-of-course-indicator.tsx`
- `retrograde-tracker.tsx`
- `planetary-hour-timeline.tsx`
- `daily-affirmation.tsx`
- `day-recommendations.tsx`
- `day-tip-card.tsx`
- 3001 `today-screen.tsx` helper `deriveChartAndEnergy`
- static `NATAL_HOUSES` / `NATAL_PLANETS`

### `/profile`

- `transit-timeline.tsx`
- `lunar-node-widget.tsx`
- `dev-mode-switcher.tsx`
- changed profile cards/rows.

### `/readings`, `/horary`, `/natal`

- `synastry-demo.tsx`
- `celebrity-compatibility.tsx`
- `planetary-strength-radar.tsx`
- changed horary/natal cards/forms/charts.

## Correct Contract Model

Use this model in the report:

`Pydantic schema/API response -> contracts:generate -> packages/contracts generated TypeScript type -> adapter -> optional Zod UI/view-model schema -> component props`

If a field is not in generated `@/packages/contracts`, the frontend must not invent it as production runtime data.

If an oracle component needs a field that does not exist yet, classify it as `REQUIRES_BACKEND_CONTRACT` or `PORT_PRESENTATION_REPLACE_DATA`.

## Required Output

Update or append the report:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/01_agent_report.md`

Also create:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/04_rework_01_report.md`

The rework report must include:

- Whether each screenshot is valid.
- DOM sentinel table for all six route families on 3001 and 3002.
- Screenshot paths for valid captures.
- Any invalid capture paths marked clearly as invalid.
- Corrected decision matrix that avoids subjective visual claims.
- Corrected component data-safety classification.
- Corrected `/day` deep dive.
- Corrected git strategy recommendation with confidence level.
- Exact commands run and results.
- Remaining blockers.

## Artifact Naming

Keep the original invalid screenshots for traceability, but mark them invalid in the report.

Write new captures under:

`docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-01/`

Expected names:

- `3001-day-2026-07-05.png`
- `3002-day-2026-07-05.png`
- `3001-calendar.png`
- `3002-calendar.png`
- `3001-profile.png`
- `3002-profile.png`
- `3001-readings.png`
- `3002-readings.png`
- `3001-horary.png`
- `3002-horary.png`
- `3001-natal.png`
- `3002-natal.png`

If a route cannot be captured, write a small `.txt` next to the expected screenshot name with the blocker details.

## Commit

Commit only Wave 09 docs/artifacts:

```bash
git add docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09
git commit -m "docs: rework corrective frontend migration audit"
```

## Callback

After the commit, notify the architect:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 09 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/04_rework_01_report.md. Review: docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/02_arch_review.md. Branch: <branch>. Commit: <commit>."}'
```

Return only a short completion line in tmux after callback.
