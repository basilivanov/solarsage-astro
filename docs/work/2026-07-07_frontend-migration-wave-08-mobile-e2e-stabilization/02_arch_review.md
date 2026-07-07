# Architect Review: Wave 08 Mobile E2E Stabilization

Date: 2026-07-07
Status: REWORK_REQUIRED
Reviewed branch: `main`
Reviewed commit: `5f160f1`
TZ: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/00_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md`

## Verdict

Wave 08 is not accepted yet.

The targeted fixes closed the original Wave 07 failures, but the full mobile gate required by the TZ is still not green under the default Playwright worker settings. The report proves a sequential run with `--workers=1`, while the TZ required the normal command without overriding workers.

There is also an uncommitted tracked generated change in `next-env.d.ts`, so the working tree is not clean.

## Findings

### 1. Critical: required full mobile gate fails without `--workers=1`

The Wave 08 TZ required:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

The agent report recorded a different command:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile --workers=1
```

Fresh architect verification ran the required default command.

Result:

```text
Running 49 tests using 2 workers
1 failed
48 passed
```

Failure:

```text
e2e/calendar.spec.ts:11
Calendar Screen - Real Auth > calendar renders real payload grid and lunar state

page.goto: Navigation to "http://localhost:3000/calendar" is interrupted by another navigation to "http://localhost:3000/day/2026-07-07"
```

Artifact:

```text
test-results/calendar-Calendar-Screen---f13f4-ayload-grid-and-lunar-state-mobile/error-context.md
```

This blocks acceptance because the main goal was to make the real-auth full mobile gate trustworthy, not only green in serial mode.

Required fix:

- Root-cause and fix the remaining `e2e/calendar.spec.ts` navigation race.
- Rerun the full mobile command exactly without `--workers=1`.
- Record the default-worker result in the report.

### 2. Critical: working tree has an uncommitted tracked generated change

Fresh architect verification found:

```text
 M next-env.d.ts
```

Diff:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next/dev/types/routes.d.ts";
```

This file was not part of the Wave 08 commit and leaves `main` dirty.

Required fix:

- Stop any temporary dev server started for Wave 08 if it is still running.
- Restore `next-env.d.ts` to the committed production/build reference.
- Do not commit `next-env.d.ts` unless there is a separate architect-approved reason.
- Final `git status --short --branch` must show no uncommitted tracked files.

### 3. Important: same home-redirect race still exists in `e2e/calendar.spec.ts`

`e2e/calendar.spec.ts` still does:

```ts
await page.goto('/');
await page.waitForTimeout(3000);
...
await page.goto('/calendar');
```

`app/(grace)/page.tsx` intentionally redirects `/` to `/day/today` / `/day/YYYY-MM-DD`. Under parallel load, that redirect can race with the second navigation to `/calendar`.

This is the same class of issue the Wave 08 commit fixed in `e2e/locked-features.spec.ts`.

Required fix:

- Prefer direct `/calendar` navigation or an explicit wait for the first redirect to fully settle before any second navigation.
- Do not change product routing to satisfy this test.
- Do not add arbitrary sleeps as the fix.

### 4. Important: report currently overstates readiness

The report says:

```text
49/49 (100%) passing
Status: READY
```

That is only true for the serial `--workers=1` run. It is not true for the required default full mobile gate.

Required fix:

- Update the report after rework with the actual default full mobile command and result.
- Keep `--workers=1` only as optional diagnostic evidence if desired, not as the acceptance gate.

## Fresh Verification

Architect ran:

```bash
git status --short --branch
```

Result:

- branch: `main`;
- ahead of `origin/main` by 44 commits;
- tracked dirty file: `next-env.d.ts`;
- known unrelated untracked files remain: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check origin/main..HEAD
git diff --check
```

Result: both passed, exit code 0.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

Result: failed, 48 passed / 1 failed, with the `e2e/calendar.spec.ts:11` navigation race above.

Because the required e2e gate is red, I did not rerun the rest of the full suite gates before requesting rework.

## Rework

Rework instructions are in:

```text
docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/03_rework_01_TZ.md
```
