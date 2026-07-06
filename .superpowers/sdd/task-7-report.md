# Task 7 Report — Natal Chart Preview Contract And UI

## Context
- Workspace: `/opt/solarsage-astro-real-data-preview`
- Branch: `codex/real-data-frontend-migration`
- Base commit: `daf8b44d921cecd5f277bfedc1b6016bd5fc4eee`

## Partial-edit audit
I audited the existing uncommitted Task 7 edits before changing anything.

Retained as compliant with the brief:
- `apps/api/app/schemas/natal.py`: added `NatalPreviewChart*` schemas and `NatalPreviewRead.chart`.
- `apps/api/app/services/natal_service.py`: populates `preview.chart` directly from real `NatalContextData`.
- `apps/api/app/services/natal_report_service.py`: guards malformed `report_id` with stable `404 REPORT_NOT_FOUND`.
- `apps/api/app/api/natal.py`: route contracts updated to reflect malformed-id handling.
- `lib/contracts/natal.ts`: frontend preview Zod contract extended with real chart payload.
- `app/(grace)/readings/natal/page.tsx`: renders natal chart from `preview.chart`.
- `components/readings/natal-chart-wheel.tsx`: renders only supplied chart data; no demo imports/fallback generation.
- `apps/api/tests/test_natal_endpoints.py`, `__tests__/contracts/natal.test.ts`, `__tests__/api/natal-report.test.ts`, `__tests__/natal/natal-component-states.test.tsx`: cover new chart contract and malformed report ids.

What I corrected on top:
- `__tests__/natal/natal-component-states.test.tsx`: typed the preview fixture as `NatalPreviewRead` so `tsc` accepts the new chart contract.
- `__tests__/natal/natal-no-english.test.tsx`: added `chart: null` to match the updated contract and tightened the heading assertion to avoid a brittle duplicate-text failure.

Explicitly left untouched:
- Dirty root `next-env.d.ts` is unrelated and excluded from staging/commit.
- `lib/api/natal.ts` was already compliant with the brief; no demo/fallback routing changes were needed.

## TDD evidence
### RED
1. Ran targeted backend/frontend tests on the inherited partial edits:
   - `cd apps/api && source .venv/bin/activate && python -m pytest tests/test_natal_endpoints.py -q`
   - `pnpm exec vitest run __tests__/contracts/natal.test.ts __tests__/api/natal-report.test.ts __tests__/natal/natal-component-states.test.tsx`
   - Result: already green, which confirmed the previous worker had implemented most feature behavior.
2. Ran typecheck to find remaining contract breakage:
   - `pnpm exec tsc --noEmit`
   - Result: failed because tests still used pre-Task-7 preview fixtures (`chart` missing / readonly fixture mismatch).

### GREEN
After fixing the affected test fixtures/assertion, I reran typecheck and the verification suite; all passed.

## Verification
- `npm run contracts:generate`
  - Result: passed (`contracts: regenerated openapi.json + _generated.ts`)
- `cd apps/api && source .venv/bin/activate && python -m pytest tests/test_natal_endpoints.py -q`
  - Result: `3 passed`
- `pnpm exec vitest run __tests__/contracts/natal.test.ts __tests__/api/natal-report.test.ts __tests__/natal/natal-component-states.test.tsx`
  - Result: passed before final cleanup; final broader run below also passed
- `pnpm exec vitest run __tests__/contracts/natal.test.ts __tests__/api/natal-report.test.ts __tests__/natal/natal-component-states.test.tsx __tests__/natal/natal-no-english.test.tsx`
  - Result: `55 passed`
- `npm run contracts:check`
  - Result: passed
- `pnpm exec tsc --noEmit`
  - Result: passed

## Notes
- Production paths contain no `DEMO_NATAL_RESPONSE`, demo report ids, or frontend-generated fake natal chart data.
- The wheel keeps the planetary strength radar absent, matching the brief.
