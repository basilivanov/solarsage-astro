# W9 Agent Report — SolarSage V2 Audit Acceptance Hardening

Date: 2026-07-09  
Branch: `main`  
Push: NOT_ATTEMPTED  
Deploy: NOT_ATTEMPTED  
Remote CI: REMOTE_CI_NOT_AVAILABLE  

## Scope delivered

Implemented W9 audit/acceptance hardening only:

1. **Audit mode split**
   - `scripts/audit_today.py` requires explicit mode:
     - `--mode live-production` (alias `--live-llm-sample`)
     - `--mode frozen-baseline` (alias `--frozen-baseline`)
   - No-mode fails fast.
   - Makefile:
     - `make audit-day` → fail-fast with guidance
     - `make audit-day-live`
     - `make audit-day-freeze`

2. **`artifact_source.json`**
   - Written for every audit run with:
     - `mode`
     - `final_payload_source` (`TodayService.get_today_payload` | `committed_baseline_fixture`)
     - `activation_layer_source` (`sidecar` | `local_fallback` | `unavailable`)
     - `uses_llm_live_text`
     - `cache_invalidated_before_payload`
     - target date/time/tz + optional `git_head`

3. **Sidecar activation artifacts**
   - Audit fetches `client.get_activation_layer(...)`
   - Writes:
     - `debug/raw_sidecar_activation_layer.json`
     - `debug/sidecar_activation_layer.json`
   - Root `16_activation_layer.json` is sidecar-only in acceptance mode
   - Local fallback is debug-only: `debug/local_fallback_activation_layer.json`
   - Live + V2 enabled fails loudly on sidecar outage unless `--allow-activation-fallback`

4. **Version identity hardening**
   - New constants:
     - `apps/api/app/core/versions.py`
     - `apps/solarsage/solarsage/core/versions.py`
   - Wired into:
     - sidecar activation builder
     - API activation layer fallback
     - TodayService meta/cache identity
     - scoring/runtime/semantic services
   - Canonical values:
     - `CALCULATION_VERSION=ss-calc-1.1.0`
     - `ACTIVATION_LAYER_VERSION=al-1.0`
     - `SCORING_V2_VERSION=ss-scoring-2.0`
     - `TODAY_V2_PAYLOAD_VERSION=today.v2`

5. **Feb 29 profection hardening**
   - Added `safe_replace_year(..., feb29_policy="feb28")`
   - Used in annual/monthly profection year boundaries
   - Added profection tests for:
     - `2000-02-29` → `2026-02-28`
     - `2000-02-29` → `2026-03-01`
     - `2000-02-29` → `2028-02-29`
     - monthly determinism

6. **Tests/docs**
   - `apps/api/tests/test_audit_today_modes.py`
   - `apps/api/tests/test_audit_activation_sidecar_artifacts.py`
   - `apps/solarsage/tests/test_activation_layer_family_coverage.py`
   - extended `test_today_meta_versions.py`, `test_profections.py`
   - updated `docs/audits/README.md` so audit command names are not misleading

## Exact command results

### Backend focused tests

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_meta_versions.py \
  tests/test_activation_layer_contract.py \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_scoring_v2_runtime_flags.py -q
```

Result: **67 passed**

### Sidecar focused tests

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest \
  tests/test_activation_layer_endpoint.py \
  tests/test_activation_schema.py \
  tests/test_activation_transits.py \
  tests/test_profections.py \
  tests/test_firdar.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py \
  tests/test_secondary_progressions.py \
  tests/test_solar_arc.py \
  tests/test_eclipse_window.py \
  tests/test_activation_layer_family_coverage.py -q
```

Result: **144 passed**

### Gates

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
```

Result: **all PASSED**

### Contracts / frontend

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
```

Results:
- contracts generate: **PASSED**
- contracts diff: **zero diff**
- typecheck: **PASSED**
- vitest: **60 passed**
- playwright: **1 passed**

### Audit command safety

```bash
make audit-day
```

Result: fails fast with message to choose `audit-day-live` or `audit-day-freeze`.

## Files changed (intended W9 set)

Code:
- `scripts/audit_today.py`
- `Makefile`
- `apps/api/app/core/versions.py` (new)
- `apps/solarsage/solarsage/core/versions.py` (new)
- `apps/api/app/services/today_service.py`
- `apps/api/app/services/activation_layer_service.py`
- `apps/api/app/services/cache_key_service.py`
- `apps/api/app/services/day_scoring_runtime_service.py`
- `apps/api/app/services/scoring_v2_service.py`
- `apps/api/app/services/semantic_v2_service.py`
- `apps/solarsage/solarsage/services/activation_builder.py`

Tests:
- `apps/api/tests/test_audit_today_modes.py` (new)
- `apps/api/tests/test_audit_activation_sidecar_artifacts.py` (new)
- `apps/api/tests/test_today_meta_versions.py`
- `apps/solarsage/tests/test_profections.py`
- `apps/solarsage/tests/test_activation_layer_endpoint.py`
- `apps/solarsage/tests/test_activation_schema.py`
- `apps/solarsage/tests/test_activation_layer_family_coverage.py` (new)

Docs:
- `docs/audits/README.md`
- `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md` (this file)

## Git status (before commit)

Intended dirty set is limited to W9 files above. Pre-existing unrelated dirty/untracked paths may exist outside scope and are not committed.

## Commit SHA

`2e43bcf`

Accepted/agent commit: `2e43bcf`

## Remote CI evidence

`REMOTE_CI_NOT_AVAILABLE`

No GitHub Actions run was executed/available for this head in this environment. Local focused tests + gates + contracts/typecheck/vitest/playwright are the available evidence.

## Notes / environment

- Temporary ownership issues on `_generated.ts` / `test-results` required ownership repair to run contracts/E2E; product contents were regenerated with zero contracts diff.
- Privacy scan hits under `scripts/` and historical docs are pre-existing / not new golden fixture leakage from this wave.
- Product scoring formulas were not retuned.
- No push/deploy attempted.
