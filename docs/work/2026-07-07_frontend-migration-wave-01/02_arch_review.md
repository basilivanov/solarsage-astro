# Architecture Review: Frontend Migration Wave 01

Date: 2026-07-07
Reviewer: architect
Branch reviewed: `wave-01-day-visual-migration`
Status: `REWORK_REQUIRED`

## Summary

Wave 01 is close enough to continue, but it is not acceptable yet.

The main presentation direction is reasonable: the `/day/[date]` screen now has an oracle-like header, access card, day overview card, practical list, reading, week strip, and semantic test ids. The changes stay frontend-only and preserve the `TodayPayload -> adaptTodayPayload -> UI` direction.

However, there are three blocking issues:

1. The branch has no commits and several wave files are still untracked.
2. The mock-visual e2e test passes while hiding missing API fixtures.
3. The new UI displays `sphereScores[].key` directly; real backend keys are technical ids, but the fixture uses friendly Russian labels and masks the issue.

## Reviewed Inputs

- `docs/work/2026-07-07_frontend-migration-wave-01/00_TZ.md`
- `docs/work/2026-07-07_frontend-migration-wave-01/01_agent_report.md`
- Working tree on branch `wave-01-day-visual-migration`

## Findings

### 1. Blocking: branch is not handoff-safe

Evidence:

- Current branch points at the same commit as `main`: `ebda0c1 docs: add frontend migration wave 01 TZ`.
- `01_agent_report.md` says: `Commits: (working branch, not yet committed)`.
- New wave files are untracked:
  - `components/today/day-overview-card.tsx`
  - `components/today/today-practical-list.tsx`
  - `e2e/mock-visual/day.spec.ts`
  - `e2e/mock-visual/fixtures/day-2026-07-05.ts`
  - `docs/work/2026-07-07_frontend-migration-wave-01/01_agent_report.md`

Why this blocks acceptance:

The protocol requires a reviewable branch with commits. In the current state, another agent or reviewer cannot reliably fetch/review the work from git, and merge to `main` is impossible without manually reconstructing the intended file set.

Required fix:

Stage and commit only Wave 01 files. Do not include unrelated `.grace/`, `grace.db`, `skills/`, or old plan files.

### 2. Blocking: mock-visual e2e hides missing fixtures

Evidence:

- `e2e/mock-visual/day.spec.ts` fixtures only:
  - `/api/day/2026-07-05`
  - `/api/auth/dev`
- The page also calls:
  - `/api/calendar?month=2026-07` via `getMonthCalendar()`;
  - multiple `/api/day/<date>` calls from `WeekStrip`.
- `installMockApiRoutes()` returns HTTP 501 for unmatched API calls, but the product code catches these failures and renders fallback UI, so the test can still pass.
- A manual fixture screenshot showed ready-state UI with `Лунные данные загружаются`, meaning the test did not actually cover the lunar/calendar data path.

Why this blocks acceptance:

The TZ requires unmatched mock visual API calls to fail fast so fixture gaps are visible. The current test does not enforce that. It can pass while the visual baseline is missing real sections.

Required fix:

Add fixture coverage or explicit missing-request assertions so any unmocked `/api/**` request fails the test even if the app catches the HTTP error.

### 3. Blocking: real `sphereScores[].key` is rendered as user text

Evidence:

- `components/today/day-overview-card.tsx` renders `topSphere.key`.
- `components/today/today-practical-list.tsx` renders `sphere.key`.
- Backend builds `SphereScore.key` from scoring ids in `apps/api/app/services/today_service.py`.
- `apps/api/app/schemas/today.py` defines only `{ key, score, rank }`, with no display label.
- Existing backend/service docs and code show technical keys such as `work_status_achievement`, `relationships_partnership`, `body_energy_health`.
- The new e2e fixture uses friendly strings such as `Дом и семья`, which hides the real-data problem.

Why this blocks acceptance:

The wave goal is real-data visual migration. Showing technical scoring ids in the first-viewport UI is not acceptable product copy, and the test fixture currently makes that bug invisible.

Required fix:

Add a deterministic display mapping for known sphere keys or extend the real contract with a display label. For Wave 01, a frontend display mapping is acceptable if it is explicit, tested, and does not fabricate astrology.

The e2e fixture should use real-shaped technical keys, not already-localized labels, so tests catch display mapping regressions.

## Verification Run By Reviewer

Commands run:

```bash
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Results:

- `git diff --check`: passed for tracked diff.
- Additional whitespace check on new untracked wave files: passed.
- TypeScript: passed.
- Vitest: passed, `83` files / `861` tests.
- Mock visual e2e:
  - first run failed because Playwright WebKit was not installed;
  - after `pnpm exec playwright install webkit`, rerun against local branch dev server on port `3000` passed: `3 passed`.

Note:

I used local dev server on `3000` because `3002` is the canonical systemd build and does not represent the uncommitted working tree. Do not restart or replace `3002` during rework unless explicitly approved.

## Non-Blocking Notes

- `components/today/today-practical-list.tsx` contains unused/dead code: `ICON_MAP`, `PlanetInfluence` import, and an empty `if` block.
- New files have a leading blank line before the AI header. Clean this up while touching them.
- Direct unauthenticated screenshot of `/day/2026-07-05` shows the expected auth error; visual checks for this wave should use either Telegram/dev-auth correctly or the explicit mock-visual fixture route.

## Decision

`REWORK_REQUIRED`

Do not merge Wave 01 yet. Apply `03_rework_01_TZ.md`, then produce `04_rework_01_report.md`.
