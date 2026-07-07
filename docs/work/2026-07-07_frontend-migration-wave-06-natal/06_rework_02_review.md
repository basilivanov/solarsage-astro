# Architect Review: Wave 06 `/readings/natal` Rework 02

Date: 2026-07-07
Status: ACCEPTED
Reviewed branch: `wave-06-natal-visual-migration`
Reviewed implementation commit: `dfa58ed`
Docs correction: agent report Rework 02 SHA corrected in this acceptance docs commit
Base rework TZ: `docs/work/2026-07-07_frontend-migration-wave-06-natal/05_rework_02_TZ.md`
Agent report: `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md`

## Verdict

Wave 06 is accepted.

Rework 02 closed the remaining test-contract gaps:

- `fullReportAvailable=true` component coverage now asserts the CTA button remains disabled and `aria-disabled="true"`;
- `natal-hero-badges` is asserted in component and mock-visual e2e coverage;
- `/readings/natal` remains on the real `fetchNatalPreview()` / `NatalPreviewRead` data flow;
- no backend, payment, runtime mock, MSW, mock-preview API, systemd, nginx, bot config, or canonical `3002` changes were introduced.

The agent report initially listed the Rework 02 commit as `2198b39`, while the callback and git history identify the reviewed commit as `dfa58ed`. I corrected that single docs-only SHA line before acceptance instead of sending another rework round.

## Reviewed Changes

Rework 02 changed only:

- `__tests__/natal/natal-component-states.test.tsx`
- `e2e/mock-visual/natal.spec.ts`
- `docs/work/2026-07-07_frontend-migration-wave-06-natal/01_agent_report.md`

Product code was unchanged in Rework 02.

## Fresh Verification

Architect ran these checks on `dfa58ed` plus the docs-only SHA correction:

```bash
git diff --check main..HEAD
git diff --check
```

Result: passed, exit code 0.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: passed, exit code 0.

```bash
npx vitest run __tests__/natal/natal-component-states.test.tsx __tests__/api/natal-report.test.ts __tests__/contracts/natal.test.ts __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: 4 files passed, 63 tests passed.

```bash
npx vitest run
```

Result: 85 files passed, 896 tests passed.

```bash
E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile
```

Result: 25 tests passed.

## Acceptance Notes

The Wave 06 branch is ready to proceed to the next frontend migration wave after integration policy is decided.
