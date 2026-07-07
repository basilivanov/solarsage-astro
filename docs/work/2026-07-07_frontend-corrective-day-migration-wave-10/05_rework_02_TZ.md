# Rework 02 TZ: Wave 10 — Final Day Oracle Corrections

Date: 2026-07-07
Branch: `main`
Role: coding executor

## Goal

Fix the remaining `/day/2026-07-05` visual mismatches found in `04_rework_01_review.md`.
This is a narrow rework on top of commit `59506ba`.

## Required Changes

### 1. Remove non-today check-in placeholder

In `components/today/today-screen.tsx`:

- Render the check-in/echo section only when `isToday === true`.
- For non-today selected dates, omit the section entirely.
- Do not render `DayCheckinReminder` for `/day/2026-07-05`.
- Remove `DayCheckinReminder` if it is no longer needed.

Expected top order for `/day/2026-07-05`:

1. `day-header`
2. `access-card`
3. `day-summary-card`
4. `concrete-day-advice`

Expected top order for actual today may still include `evening-checkin-reminder` after `access-card`.

### 2. Port the 3001 bottom history widget safely

Add a main component equivalent to:

```text
/opt/solarsage-astro-mock-preview/components/today/astro-history-widget.tsx
```

Requirements:

- Put it under `components/today/astro-history-widget.tsx`.
- Add/keep the GRACE module contract header.
- Add `data-testid="astro-history-widget"` on the section.
- Render after `WeekStrip` and before `today-bottom-disclaimer`.
- Use deterministic curated static educational content by date.
- Do not import runtime mocks, demo data, mock-preview files, or fake backend payloads.
- It is acceptable to keep the small curated event list in this component because it is educational copy, not simulated personal astrology/API data.

### 3. Restore generated `next-env.d.ts`

Restore `next-env.d.ts` to:

```ts
import "./.next/types/routes.d.ts";
```

Do not include generated `.next/dev` or `.next-prod` path changes in the commit.

### 4. Tests

Update and run:

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit --pretty false
E2E_BASE_URL=http://localhost:4444 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile
```

Test expectations:

- `/day/2026-07-05` does not show `evening-checkin-reminder`.
- `/day/2026-07-05` shows `astro-history-widget` near the bottom.
- Section order for `/day/2026-07-05` includes:
  - `day-header`
  - `access-card`
  - `day-summary-card`
  - `concrete-day-advice`
  - `day-chart` or `day-chart-unavailable`
  - `day-reading`
  - `why-expanded`
  - `week-strip`
  - `astro-history-widget`
  - `today-bottom-disclaimer`

### 5. Visual Evidence

Create new evidence under:

```text
docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-02/
```

Capture at minimum:

- `3001-day-2026-07-05-top.png`
- `3001-day-2026-07-05-middle.png`
- `3001-day-2026-07-05-bottom.png`
- `main-day-2026-07-05-top.png`
- `main-day-2026-07-05-middle.png`
- `main-day-2026-07-05-bottom.png`
- `summary.json`

The main top image must show no non-today check-in card.
The main bottom image must show `astro-history-widget` before the disclaimer.

### 6. Report And Commit

Update:

```text
docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/01_agent_report.md
```

Include:

- commit hash
- exact files changed
- tests run and results
- evidence paths and hashes
- note that 3002 was or was not restarted

Commit only intentional files. Do not include unrelated untracked files.

After commit, run callback:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 10 Rework 02 ready for architect review. Report: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/01_agent_report.md. Review: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/04_rework_01_review.md. Rework TZ: docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/05_rework_02_TZ.md. Branch: main. Commit: <commit-hash>."}'
```
