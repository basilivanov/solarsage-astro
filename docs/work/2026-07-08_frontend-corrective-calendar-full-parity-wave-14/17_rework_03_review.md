# Wave 14 Calendar Parity Rework 03 Review

Date: 2026-07-08
Reviewed commit: `dcb63fb`
Decision: REWORK REQUIRED

## Summary

The Rework 03 intent is correct: product UI was not changed, CTA lookup is now scoped, comments were updated, and the spec was marked serial. However, the acceptance gate still fails under the exact default Playwright command.

The root issue is that `test.describe.configure({ mode: "serial" })` serializes tests inside one Playwright project, but the current `playwright.config.ts` still runs the `chromium` and `mobile` projects concurrently:

```ts
fullyParallel: true,
workers: process.env.CI ? 1 : undefined,
projects: ["chromium", "mobile"]
```

So the reported serial fix does not actually serialize this command locally.

## Verification Run

With local dev server running on `localhost:3000`:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 1.

Playwright output:

```text
Running 12 tests using 2 workers
1 failed
4 did not run
7 passed
```

Failure:

```text
[chromium] calendar screen renders in ready state with month header, grid, lunar strip, and summary
Expected getByTestId('calendar-screen') to be visible.
Actual page context: "Авторизация..."
```

The mobile project passed in this run, while Chromium remained stuck behind auth loading. This confirms a cross-project/default-worker harness race, not a calendar product UI regression.

## Findings

### P0 — Exact default Playwright gate is still red

Evidence:

- The required command still starts as `Running 12 tests using 2 workers`.
- `test.describe.configure({ mode: "serial" })` did not prevent concurrent `chromium` and `mobile` projects.
- Chromium can remain stuck at `Авторизация...`, so `calendar-screen` never appears.

Required fix:

- Make this exact command pass twice in a row without adding CLI flags:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

- Do not rely on `--workers=1` in the verification command. If serial execution is the chosen solution, it must be encoded in the repo configuration or test harness so the default command is green.

### P1 — Rework report contradicted architect verification

Evidence:

- The report says the exact command passed twice.
- Architect verification immediately after the commit failed under the same command.

Required fix:

- Reproduce from a clean shell with the same command.
- Include exact first lines of Playwright output in the report, especially:

```text
Running 12 tests using N workers
```

- If the fix changes worker policy, report the policy and why it is intentional.

## Recommended Architecture

Preferred stable option:

- Make Playwright e2e default to one worker unless explicitly overridden, for example:

```ts
const configuredWorkers = process.env.E2E_WORKERS
  ? Number(process.env.E2E_WORKERS)
  : 1;

workers: configuredWorkers,
```

Why this is acceptable:

- CI already uses one worker.
- Mock-visual tests are visual/readiness gates against one local/dev app, not high-throughput parallel unit tests.
- Screenshot/visual baseline work benefits from deterministic ordering.
- Developers can still opt into parallelism with `E2E_WORKERS=2` after accepting the risk.

Alternative acceptable option:

- Fix the auth injection race directly so the default command is green with multiple workers.
- If choosing this path, prove it with two consecutive default-command runs and explain the actual race/fix.

Do not fix this by merely increasing timeouts unless you can show the auth transition always completes and the longer timeout only covers Next dev cold compilation. A page stuck at `Авторизация...` is not a visual readiness delay.

## Acceptance Gate For Rework 04

Accept only if:

- `pnpm exec tsc --noEmit --pretty false` passes.
- Targeted Vitest suite passes.
- Backend calendar endpoint tests pass.
- `E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts` passes twice in a row.
- Report includes the Playwright worker count from both successful runs.
- No product UI files are changed unless the report proves they were necessary.
- No push/deploy.
