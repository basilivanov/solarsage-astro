# Wave 14 Calendar Parity Rework 04 Review

Date: 2026-07-08
Reviewed commit: `4a22bb5`
Decision: ACCEPTED

## Summary

Rework 04 resolves the remaining mock-visual calendar gate failure.

The previous fix serialized tests only inside the calendar describe block, while Playwright still ran `chromium` and `mobile` projects concurrently. The accepted fix moves the deterministic worker policy into `playwright.config.ts`: E2E now defaults to one worker locally and in CI, with explicit local opt-in via validated `E2E_WORKERS`.

No calendar product UI files were changed in this rework.

## Architect Verification

```bash
git status --short --branch && git diff --check HEAD~1..HEAD
```

Result: exit 0. Tracked tree clean; only pre-existing untracked local files remain.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.20s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

First exact Playwright run:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0.

```text
Running 12 tests using 1 worker
12 passed (59.5s)
```

Second exact Playwright run:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0.

```text
Running 12 tests using 1 worker
12 passed (57.7s)
```

## Review Notes

- The worker policy is intentionally conservative. It aligns local default E2E behavior with CI and removes cross-project contention for Telegram auth/runtime setup.
- `E2E_WORKERS` gives an explicit escape hatch for local parallel runs without making visual/readiness gates flaky by default.
- The remaining runtime/deploy question is outside this rework: production `3002` must be rebuilt/restarted only when we decide to deploy the accumulated main commits.
