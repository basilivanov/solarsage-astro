# W6 Rework 01 TZ — Green Main + Evidence Contract Closure

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push or deploy.

## Inputs

Read first:

```text
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/00_TZ.md
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/01_agent_report.md
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/02_arch_review.md
```

## Goal

Fix only the W6 review findings. Do not expand scope. The result must keep the W6 architecture:

- backend owns V2 semantic/evidence data;
- frontend renders and normalizes contract data only;
- no production runtime mocks;
- old V1 payloads still render;
- V2 payloads are contract-valid and typecheck-clean.

## Required Fixes

### 1. Make `pnpm typecheck` pass

Fix the current type errors without `any`, `ts-ignore`, or broad casts.

Expected direction:

- Update old static TodayPayload fixtures/tests to include `meta.payloadVersion="today.v1"` and `meta.frontendPayloadVersion=1` where the generated TS type requires them.
- For V2 fixture `ActivationEvidence`, include required defaulted generated fields if needed, or normalize through the adapter boundary.
- In `lib/adapters/today-payload.ts`, do not assign raw `api.v2` directly if its generated input type does not match the adapted Zod output type. Normalize/validate the V2 block at the adapter boundary, applying defaults for fields such as `active`, `phase`, `polarity`, and `debug`.
- Add/update tests in `__tests__/contracts/today.test.ts` and `__tests__/lib/adapt-payload.test.ts` proving:
  - an old payload without `v2` still validates/adapts;
  - a V2 payload preserves V2 data;
  - adapter does not fabricate V2 when backend omits it.

### 2. Fix whitespace verification

Remove all whitespace errors reported by:

```bash
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

### 3. Add the missing mock visual screenshot assertion

In `e2e/mock-visual/day-v2.spec.ts`, add at least one deterministic screenshot assertion with `toHaveScreenshot(...)`.

Prefer a stable V2 section locator, for example `activation-evidence-card`, `why-today`, or a stable visible section instead of the whole page if the full viewport is noisy.

If Playwright creates/updates a snapshot file, commit it.

### 4. Actually pass evidence packet into `generate_why_sections`

`LLMService.generate_why_sections(...)` now supports `evidence_packet`; wire the caller.

Expected direction:

- Build the packet via the deterministic helper in `SemanticV2Service`, or refactor that helper to support the why-section use case cleanly.
- Use `ActivationLayer` and `dual.v2_result` as sources.
- For why sections, `concrete_rows` and `forbidden_claims` may be empty because concrete rows are not built yet. Do not hardcode forbidden claims globally.
- Add a focused test proving the TodayService/LLM call path passes a non-empty V2 evidence packet when V2 frontend is enabled and activation data exists.

### 5. Fix `TodayV2Audit.canonVersions`

`TodayV2Audit.canon_versions` must always be `dict[str, str]`.

Required:

- Do not populate it from `load_canon_bundle()` full YAML dicts.
- Prefer `scoring_result.canon_versions` when `ScoringV2Result` exists; otherwise use `get_canon_versions()`.
- Add a unit test that `SemanticV2Service.build_v2_block(...).audit.canon_versions` contains only string values.
- Avoid Pydantic serializer warnings for this field.

### 6. Gate DevAuditDrawer visibility correctly

`?audit=1` must not expose the drawer in production.

Required:

- Keep `forceShow` for component tests.
- Allow query-param visibility only in non-production/test environment.
- Add/update a unit test for hidden by default and visible with `forceShow`.
- If practical, add a small test for production env query-param not showing the drawer.

### 7. Make V2 semantic output deterministic

Sort technique arrays and any other set-derived arrays before returning contract data.

Add a unit assertion that a known activation input produces stable sorted technique order.

### 8. Revert unrelated `next-env.d.ts` churn

Unless you can justify it as source-level config, restore:

```ts
import "./.next/types/routes.d.ts";
```

Do not commit generated local build mode churn.

## Required Verification

Run and report exact commands/results:

```bash
pnpm contracts:generate
```

```bash
pnpm typecheck
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_semantic_v2_service.py \
  tests/test_today_v2_payload.py \
  tests/test_llm_claim_validator.py \
  tests/test_llm_service.py \
  tests/test_today_concrete_advice.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py -q
```

```bash
npx vitest run \
  __tests__/contracts/today.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx
```

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
```

If no frontend server is available for Playwright, report that explicitly. Do not claim screenshot verification passed unless Playwright exits 0.

Also run:

```bash
python3 scripts/check_logging_guardrails.py
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/04_rework_01_report.md
```

Include:

- files changed;
- how each finding from `02_arch_review.md` was resolved;
- exact verification outputs;
- push/deploy status: `NOT_ATTEMPTED`;
- current commit SHA may be only in callback.

Commit implementation and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W6 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/03_rework_01_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
