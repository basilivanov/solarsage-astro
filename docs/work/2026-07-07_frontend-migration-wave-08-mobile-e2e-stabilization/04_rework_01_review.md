# Architect Review: Wave 08 Mobile E2E Stabilization Rework 01

Date: 2026-07-07
Status: ACCEPTED
Reviewed branch: `main`
Reviewed head: `e58d496`
Base review: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/02_arch_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/03_rework_01_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md`

## Verdict

Wave 08 is accepted.

Rework 01 closed the remaining default-worker mobile e2e race:

- `e2e/calendar.spec.ts` no longer navigates through `/`, so the intentional home redirect to `/day/YYYY-MM-DD` cannot interrupt `/calendar`;
- `next-env.d.ts` is back to the committed state and no longer dirty;
- the full mobile Playwright command passes with default workers, without `--workers=1`;
- no product code, runtime mocks, MSW, systemd, nginx, Telegram bot config, `.env.production`, or canonical `3002` files changed.

The agent report's Rework 01 section names commit `7825fb9`, but the actual reviewed callback/HEAD commit is `e58d496`. This acceptance review supersedes that report typo; the reviewed diff is `e58d496`.

## Reviewed Scope

Rework 01 changed only:

```text
docs/work/2026-07-07_frontend-migration-wave-08-mobile-e2e-stabilization/01_agent_report.md
e2e/calendar.spec.ts
```

The `e2e/calendar.spec.ts` change removes the preflight `/` navigation and goes directly to `/calendar`.

## Fresh Verification

Architect ran:

```bash
git status --short --branch
```

Result:

- branch: `main`;
- ahead of `origin/main` by 46 commits before this acceptance docs commit;
- no uncommitted tracked files;
- known unrelated untracked files remain: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check origin/main..HEAD
git diff --check
```

Result: both passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run
```

Result: 85 files passed, 896 tests passed.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result: 626 passed, 2 skipped, 1 warning.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=mobile
```

Result: 49 passed, default 2 workers, no `--workers=1`.

## Accepted State

Accepted state:

- waves 01-06 visual migration is integrated into local `main`;
- Wave 08 stabilizes the real-auth full mobile e2e suite after integration;
- local `main` is ready for a guarded non-force push after this acceptance docs commit.
