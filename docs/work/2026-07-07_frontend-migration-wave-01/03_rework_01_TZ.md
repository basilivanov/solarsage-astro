# Rework 01 TZ: Frontend Migration Wave 01

Date: 2026-07-07
Status: ready for coder
Scope: fix only the blockers from `02_arch_review.md`

## Fix Only These Findings

### 1. Make the branch handoff-safe

Create one Wave 01 commit on `wave-01-day-visual-migration`.

Include only relevant Wave 01 files:

- modified `components/today/*` files;
- modified `__tests__/components/TodayScreen.test.tsx`;
- new `e2e/mock-visual/*` files;
- `docs/work/2026-07-07_frontend-migration-wave-01/01_agent_report.md`;
- `04_rework_01_report.md` after rework is done.

Do not stage or commit:

- `.grace/`;
- `grace.db`;
- `skills/`;
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
- unrelated generated artifacts.

### 2. Make mock-visual e2e fail on missing API fixtures

The test must not pass if any `/api/**` request is missing from the fixture set.

Implement one of these approaches:

- add test-level tracking of HTTP 501 `missing_mock_visual_fixture` responses and assert the missing list is empty after navigation; or
- extend `installMockApiRoutes()` with an explicit missing-request recorder and assert it in the spec.

Then add contract-valid fixtures for all API calls made by `/day/2026-07-05` in this test, including:

- `/api/calendar?month=2026-07` or the helper's pathname-equivalent fixture;
- week-strip `/api/day/<date>` calls for the rendered week.

The ready-state fixture must render actual lunar data for `2026-07-05`; it must not leave the day overview card saying `Лунные данные загружаются`.

### 3. Do not render raw `sphereScores[].key` to users

Real backend sphere keys are technical ids. Add deterministic display mapping before rendering them in:

- `components/today/day-overview-card.tsx`;
- `components/today/today-practical-list.tsx`;
- any other first-viewport Wave 01 UI that shows sphere labels.

Acceptable for this wave:

- frontend constant/helper mapping known keys such as `work_status_achievement`, `relationships_partnership`, `body_energy_health`;
- fallback that formats unknown snake_case keys into readable Russian only if no explicit mapping exists.

Better but optional:

- backend contract extension with display label, if done narrowly and with tests.

Update tests and fixtures:

- use raw technical keys in `e2e/mock-visual/fixtures/day-2026-07-05.ts`;
- add a unit assertion that raw key `work_status_achievement` is displayed as a human label, not as the raw key.

### 4. Cleanup while touching files

- Remove unused imports and dead code in `today-practical-list.tsx`.
- Remove leading blank lines before AI headers in newly created files.
- Keep product code free of `lib/mocks/*`, `lib/demo-data.ts`, MSW, and mock-preview runtime imports.

## Required Gates

Run and report exact results in:

```text
docs/work/2026-07-07_frontend-migration-wave-01/04_rework_01_report.md
```

Commands:

```bash
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use `3000` for branch-local dev verification unless the architect explicitly approves rebuilding/restarting `3002`.

## Acceptance For Rework

Rework is acceptable when:

- Wave 01 changes are committed on the feature branch;
- no unrelated files are staged/committed;
- mock-visual e2e fails on missing API fixtures;
- all API calls made by the mock visual day route are fixture-covered;
- ready-state mock visual day screen renders real fixture lunar data;
- raw sphere keys are not visible to users;
- required gates pass;
- `04_rework_01_report.md` documents changed files, commit id, commands, and remaining risks.
