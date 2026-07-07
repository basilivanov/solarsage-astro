# Rework 01 TZ: Wave 08 Mobile E2E Stabilization

Date: 2026-07-07
Status: ready for coder
Owner: architect
Coder model: Flash 3.5
Branch: `main`
Reviewed commit: `5f160f1`
Base review: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/02_arch_review.md`

## Goal

Close the remaining default-worker full mobile e2e failure and return the working tree to a clean tracked state.

This is a rework of Wave 08. Do not push.

## Required Fixes

### 1. Fix the remaining full mobile e2e race

Fresh architect verification of the required command failed:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

Failure:

```text
e2e/calendar.spec.ts:11
Calendar Screen - Real Auth > calendar renders real payload grid and lunar state

page.goto: Navigation to "http://localhost:3000/calendar" is interrupted by another navigation to "http://localhost:3000/day/2026-07-07"
```

Root-cause this before changing code.

Likely cause:

- `e2e/calendar.spec.ts` goes to `/`, waits for a fixed 3000 ms, then goes to `/calendar`;
- `/` intentionally redirects to `/day/today` / `/day/YYYY-MM-DD`;
- under default parallel Playwright workers, that redirect can interrupt the second navigation.

Fix the smallest correct layer:

- likely `e2e/calendar.spec.ts`, not product routing;
- prefer direct `/calendar` navigation or an explicit semantic wait for the first redirect to settle;
- do not add arbitrary sleeps;
- do not use `--workers=1` as the fix.

### 2. Restore clean tracked working tree

Architect verification found uncommitted tracked drift:

```text
 M next-env.d.ts
```

Diff:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next/dev/types/routes.d.ts";
```

Required:

- If a temporary `3000` dev server from Wave 08 is still running, stop it before callback.
- Restore `next-env.d.ts` to the committed production/build reference:

```ts
import "./.next/types/routes.d.ts";
```

- Do not commit `next-env.d.ts` unless architect explicitly approves that separately.
- Final `git status --short --branch` must show no uncommitted tracked files.

### 3. Update the Wave 08 report

Update:

```text
docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md
```

Required updates:

- Add a `Rework 01` section.
- Record the remaining calendar race root cause.
- Record the file(s) changed in Rework 01.
- Replace readiness evidence based on `--workers=1` with the required default command:

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

- If you keep the `--workers=1` result, label it as diagnostic only.
- Record the final clean `git status --short --branch` result.
- Keep push status as `NOT_ATTEMPTED`.

## Required Gates

Run and report exact results:

```bash
git status --short --branch
git diff --check origin/main..HEAD
git diff --check
pnpm exec tsc --noEmit --pretty false
npx vitest run
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q && cd ../..
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/calendar.spec.ts:11 --project=mobile
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

The final full mobile command must not include `--workers=1`.

If `localhost:3000` is not serving this repo, start a temporary dev server for the Playwright gates and stop it before callback.

## Guardrail Search

Run and report:

```bash
rg -n "USE_FIXTURES|DEMO_|lib/demo-data|lib/mocks|msw|mock-preview|test\\.skip|test\\.fixme|\\.only\\(" app components lib hooks __tests__ e2e docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization || true
```

Expected:

- no product-path runtime mock/demo imports;
- no new `test.skip`, `test.fixme`, or `.only(`;
- existing test-only mock-visual fixtures remain acceptable.

## Commit Requirements

Create one new commit on `main`:

```bash
git add e2e/calendar.spec.ts docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md
git commit -m "test: fix calendar mobile e2e race"
```

If you change a different test file after root-cause investigation, include it instead and explain why in the report.

Do not commit:

- `next-env.d.ts`
- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- `test-results/`
- `playwright-report/`
- unrelated files

## Required Callback

At the very end, run this callback from the repo root:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 08 Rework 01 ready for architect review. Report: docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md. Review: docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/02_arch_review.md. Rework TZ: docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

Replace `<commit_sha>` with the actual Rework 01 commit SHA.
