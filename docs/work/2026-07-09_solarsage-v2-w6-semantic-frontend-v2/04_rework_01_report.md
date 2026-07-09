# W6 Rework 01 Report

## Goal
Resolve all findings from the W6 Architect Review (`02_arch_review.md`) and ensure green typecheck, E2E, unit tests, and whitespace checks.

## Changed Files
- `apps/api/app/services/today_service.py` (wired evidence packet for `generate_why_sections`)
- `apps/api/app/services/semantic_v2_service.py` (fixed `canon_versions` types, sorted techniques list)
- `apps/api/tests/test_semantic_v2_service.py` (added deterministic technique sorting & string audit canon versions unit tests)
- `apps/api/tests/test_today_v2_payload.py` (added focused test verifying why sections receive evidence packet)
- `lib/adapters/today-payload.ts` (implemented `buildV2Block` boundary mapper to normalize Zod V2 defaults)
- `lib/contracts/today.ts` (updated Zod schemas for V2 block and evidence)
- `components/today/dev-audit-drawer.tsx` (gated query-param visibility by localhost/non-production environments)
- `__tests__/components/TodayScreen.test.tsx` (updated/added unit tests for V2 drawer and activation card)
- `__tests__/hooks/useDay.test.ts` (added new meta version fields)
- `__tests__/lib/adapt-payload.test.ts` (added new meta version fields, added contract-valid adapter tests)
- `e2e/mock-visual/fixtures/day-2026-07-05.ts` (added new meta version fields)
- `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts` (added default fields `phase` and `polarity` to mock activations)
- `e2e/mock-visual/day-v2.spec.ts` (added `toHaveScreenshot` visual regression assertion, awaited mock route installation)
- `next-env.d.ts` (reverted unrelated local Next.js build route reference changes)
- `docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/02_arch_review.md` (cleaned trailing whitespace)
- `docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/03_rework_01_TZ.md` (cleaned trailing whitespace)

## Resolutions of Architect Review Findings

### 1. P0 — `pnpm typecheck` fails after W6 contract changes
- Added missing `payloadVersion` and `frontendPayloadVersion` to `meta` objects in all old fixtures/tests.
- Updated `ActivationEvidence` in mock visual fixtures to include `phase` and `polarity`.
- Created a robust `buildV2Block` mapper in `lib/adapters/today-payload.ts` to cleanly map/normalize generated API types to Adapted Zod types, applying default values for `active`, `phase`, `polarity`, and `debug`.
- `pnpm typecheck` now exits with code 0.

### 2. P0 — whitespace gate fails
- Stripped all trailing whitespaces and extra EOF blank lines from all touched files.
- `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check` now exits with 0 and reports no issues.

### 3. P1 — Playwright mock visual test has no screenshot assertion
- Added `await expect(actCard).toHaveScreenshot("activation-evidence-card.png")` in `day-v2.spec.ts`.
- Ran the test with `--update-snapshots` to generate the baseline snapshot file and committed it.

### 4. P1 — `generate_why_sections` accepts `evidence_packet`, but TodayService never passes it
- Wired `SemanticV2Service().build_llm_evidence_packet(...)` to generate a why sections evidence packet (with empty `concrete_rows` and `forbidden_claims` since they aren't computed yet) and passed it to `llm_service.generate_why_sections(...)`.
- Added a focused unit test in `test_today_v2_payload.py` to assert that the `generate_why_sections` mock is called with the non-empty V2 `evidence_packet`.

### 5. P1 — `TodayV2Audit.canonVersions` violates its own contract at runtime
- Modified `SemanticV2Service.build_v2_block(...)` to populate `canon_versions` from `scoring_result.canon_versions` when available, or `get_canon_versions()` from config. It maps all keys/values as strings (`dict[str, str]`).
- Added a unit test proving `block.audit.canon_versions` contains only string keys/values.

### 6. P1 — Dev audit drawer is enabled in production by `?audit=1`
- Gated `?audit=1` visibility in `dev-audit-drawer.tsx` to localhost or non-production environment checks (`window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || process.env.NODE_ENV !== "production"`).
- Added unit tests in `TodayScreen.test.tsx` verifying that `DevAuditDrawer` is hidden by default and only renders when `forceShow` is active.

### 7. P2 — V2 semantic output is not fully deterministic
- Wrapped set-derived technique lists in `sorted(...)` to guarantee stable deterministic order.
- Added a unit test proving technique array order is stable and sorted.

### 8. P2 — generated Next env file was committed with local production build state
- Reverted the Next.js routes reference in `next-env.d.ts` back to `import "./.next/types/routes.d.ts";`.

## Verification Outputs

### Typecheck
```text
pnpm typecheck

> my-project@0.1.0 typecheck /opt/solarsage-astro
> tsc --noEmit
(Exited with 0)
```

### Target Verification Tests
```text
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_semantic_v2_service.py \
  tests/test_today_v2_payload.py \
  tests/test_llm_claim_validator.py \
  tests/test_llm_service.py \
  tests/test_today_concrete_advice.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py -q

47 passed, 1 warning in 2.37s
```

### Vitest Unit Tests
```text
npx vitest run \
  __tests__/contracts/today.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx

Test Files  3 passed (3)
     Tests  55 passed (55)
  Duration  1.61s
```

### Playwright E2E Test
```text
sudo E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile

Running 1 test using 1 worker
  ✓  1 [mobile] › e2e/mock-visual/day-v2.spec.ts:46:7 › W6 V2 Day Screen mock visual ... (5.9s)
  1 passed (6.8s)
```

### Logging Guardrails
```text
python3 scripts/check_logging_guardrails.py

drift gate: OK
backend logger gate: OK
frontend console gate: OK
All guardrails PASSED.
```

### Whitespace Check
```text
sudo git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
(No output, completely clean)
```

## Push / Deploy Status
Push: NOT_ATTEMPTED

## Commit SHA
Commit: see callback/current HEAD
