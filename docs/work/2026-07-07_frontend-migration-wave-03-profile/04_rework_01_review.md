# Architect Review: Wave 03 Rework 01 `/profile`

Date: 2026-07-07
Status: ACCEPTED
Reviewed branch: `wave-03-profile-visual-migration`
Reviewed commit: `6133832`
Base review: `docs/work/2026-07-07_frontend-migration-wave-03-profile/02_arch_review.md`
Rework TZ: `docs/work/2026-07-07_frontend-migration-wave-03-profile/03_rework_01_TZ.md`

## Verdict

Wave 03 is accepted.

The rework resolves the blocking findings from `02_arch_review.md`:

- `profile-screen` root `data-state` is hydration-first: loaded profile stays `ready` even if a later save error exists.
- Profile loading/error, check-in loading/error, and edit sheet save error now expose `role="status"` / `role="alert"` semantics.
- `daysPerInvite` mapping is covered by API tests, including non-14 reward days and missing-field fallback.
- Mock visual `/profile` e2e asserts fixture-backed `14 дней доступа`.
- New `e2e/mock-visual/profile.*` files now include GRACE module contract/map blocks.
- Runtime mock guardrails remain intact: no MSW, runtime mock mode, mock-preview API, static transit/lunar-node widget, YooKassa, root layout, systemd, nginx, bot, or `3002` changes.

The report still uses `Rework commit: (this commit)` wording, but the handoff callback and git history identify the actual reviewed commit as `6133832`; this is not blocking.

## Fresh Verification

Architect reran these gates on `6133832`:

```bash
git diff --check main..HEAD
```

Result: passed, exit code 0.

```bash
git diff --check
```

Result: passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/api/profile-meta.test.ts
```

Result: 2 files passed, 15 tests passed.

```bash
npx vitest run __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts __tests__/api/profile-meta.test.ts __tests__/api/access.test.ts __tests__/contracts/profile.test.ts __tests__/contracts/access.test.ts __tests__/lib/profile.test.ts __tests__/lib/access.test.ts
```

Result: 8 files passed, 93 tests passed.

```bash
npx vitest run
```

Result: 84 files passed, 874 tests passed. Existing unrelated React `act(...)` warnings appeared in several older tests.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 12 passed.

## Accepted Scope

Accepted implementation commits:

- `76f36ab` — initial Wave 03 `/profile` screen visual migration.
- `6133832` — Wave 03 rework 01 semantic contract and reward-day assertion fixes.

Accepted docs commits:

- `b3888ec` — Wave 03 TZ.
- `30ab90f` — Wave 03 review/rework request.

## Notes For Next Wave

Wave 03 did not add real backend contracts for profile transit timeline or lunar node widgets. Those mock-preview blocks remain intentionally deferred until real data contracts exist.

Next frontend migration wave can proceed.
