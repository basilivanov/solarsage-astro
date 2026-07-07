# Rework 02 TZ: Frontend Migration Wave 02 Calendar

Date: 2026-07-07
Status: ready for coder
Scope: handoff/report and metadata cleanup only

## Fix Only These Items

### 1. Add missing gate evidence to `01_agent_report.md`

Add a distinct subsection for:

```bash
git diff --check
```

Report the actual result. Do not replace `git diff --check main..HEAD`; both entries must be present.

### 2. Fix stale metadata in `calendar.spec.ts`

Current comments say the test explicitly selects the target day. The implementation now freezes browser time with:

```ts
await page.clock.install({ time: new Date("2026-07-05T12:00:00Z") });
```

Update the module contract/comment text to match that implementation. Do not change test behavior unless a comment-only edit is impossible.

### 3. Fix stale dependency comment in `day.spec.ts`

The file now imports:

```ts
expectNoMissingApiFixtures
```

from `./route-interception`.

Update the dependency comment so it mentions the shared helper correctly.

## Do Not Change

- No product UI changes.
- No backend changes.
- No systemd/nginx/3002 changes.
- Do not touch `.grace/`, `grace.db`, `skills/`, or `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

## Required Gates

Run and report:

```bash
git diff --check main..HEAD
git diff --check
```

If you change executable code beyond comments/report text, also rerun:

```bash
pnpm exec tsc --noEmit --pretty false
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Use local `3000` only. Do not restart or replace canonical `3002`.

If `next dev` changes `next-env.d.ts`, revert only that generated edit before committing.

## Commit Requirements

Create one new commit on `wave-02-calendar-visual-migration`.

Commit must include only:

- updated `01_agent_report.md`;
- updated comments in `e2e/mock-visual/calendar.spec.ts`;
- updated comments in `e2e/mock-visual/day.spec.ts`;
- this rework review/TZ if not already committed by the architect.

## Callback Requirement

After committing, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 02 Rework 02 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-02-calendar/04_rework_01_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-02-calendar/05_rework_02_TZ.md. Branch: wave-02-calendar-visual-migration. Commit: <PUT_COMMIT_SHA_HERE>"}'
```

Replace `<PUT_COMMIT_SHA_HERE>` with the actual new commit SHA.
