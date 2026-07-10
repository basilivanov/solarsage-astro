# W11 Agent Report — SolarSage V2 Post-Sidecar Downstream Correctness

Date: 2026-07-10
Base commit: `87adec4c827f9bc7e16007294f74e630981e62ad`
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE
Final code/tests commit: `aecc699`
Evidence docs tip: `6f5883c` (report SHA packaging).

## Scope delivered

Implemented post-sidecar downstream correctness audit treating sidecar `ActivationLayer` as trusted astronomy boundary.

### Core deliverables

1. `scripts/audit_downstream_v2.py`
   - modes: live, artifact_replay, synthetic_fixture
   - independent mapping/contribution/convergence/cap recalculation from canon YAML
   - production actual via `ScoringV2Service.score_day` once
   - hard fails for lost ids, missing contributions, amount mismatches, payload evidence gaps
   - required artifacts `00..12` + debug copies

2. Makefile target `audit-downstream-v2`

3. Fixtures under `apps/api/tests/fixtures/downstream_v2/` (12 synthetic cases)

4. Backend tests:
   - `tests/test_downstream_v2_audit.py`
   - `tests/test_scoring_v2_downstream_invariants.py`
   - `tests/test_payload_v2_downstream_mapping.py`

5. Frontend tests:
   - `__tests__/components/ActivationEvidenceCard.downstream.test.tsx`
   - `__tests__/components/TodayScreen.v2-downstream.test.tsx`

6. This report (`01_agent_report.md`)

Did **not** create architect review/acceptance docs.

## Files changed / added

- `scripts/audit_downstream_v2.py` (new)
- `Makefile`
- `apps/api/tests/fixtures/downstream_v2/*.json` (12 files)
- `apps/api/tests/test_downstream_v2_audit.py` (new)
- `apps/api/tests/test_scoring_v2_downstream_invariants.py` (new)
- `apps/api/tests/test_payload_v2_downstream_mapping.py` (new)
- `__tests__/components/ActivationEvidenceCard.downstream.test.tsx` (new)
- `__tests__/components/TodayScreen.v2-downstream.test.tsx` (new)
- `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/01_agent_report.md` (new)
- `artifacts/audit/2026-07-08/downstream/*` (generated replay artifacts; not necessarily committed)

## Architectural decisions (minimal within TZ)

1. **Artifact replay with V1 payload**: if input final payload is not V2-selected, audit synthesizes `payload.v2` via `SemanticV2Service` for scoring/evidence proof and records warning `payload_v2_synthesized_for_replay`. Hard fail remains for true V2-selected payloads missing body/ids.

2. **Day-status expected values**: independent recalculation uses pure `_compute_day_status_v2` on same inputs (not `score_day` post-processing), matching canon thresholds.

3. **`--fail-on-unmapped`**: default true in CLI; fixture/replay demos may set false when intentionally including unmapped targets.

4. **No scoring weight retunes**: no production scoring formula changes.

## Verification results

### Backend W11 + related scoring tests

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_downstream_v2_audit.py \
  tests/test_scoring_v2_downstream_invariants.py \
  tests/test_payload_v2_downstream_mapping.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_breakdown_contract.py \
  -q
```

Result: **29 passed**

### Existing W10 regression suite

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  -q
```

Result: **52 passed**

### Frontend fixture tests

```bash
npx vitest run \
  __tests__/components/ActivationEvidenceCard.downstream.test.tsx \
  __tests__/components/TodayScreen.v2-downstream.test.tsx
```

Result: **6 passed**

### Artifact replay audit

```bash
apps/api/.venv/bin/python scripts/audit_downstream_v2.py \
  --user-id synthetic \
  --date 2026-07-08 \
  --out artifacts/audit/2026-07-08/downstream \
  --input-activation-layer artifacts/audit/2026-07-08/16_activation_layer.json \
  --input-final-payload artifacts/audit/2026-07-08/11_final_today_payload.json \
  --input-day-signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --fail-on-unmapped false
```

Result: **PASSED (`status=ok`)**
Note: input payload is historical V1; audit synthesized V2 body for downstream scoring evidence and recorded warning.

### Synthetic fixture audit

```bash
apps/api/.venv/bin/python scripts/audit_downstream_v2.py \
  --synthetic-fixture apps/api/tests/fixtures/downstream_v2/08_convergence_multi_family.json \
  --date 2026-07-08 \
  --out /tmp/w11-synth \
  --fail-on-unmapped false
```

Result: **PASSED (`status=ok`)**

### Live downstream audit

```bash
make audit-downstream-v2 USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

Result: **NOT_RUN / FAILED_TO_CONNECT**
Sidecar returned `404 Not Found` for `http://127.0.0.1:18091/v1/activation-layer`.
Honest status: live mode implemented, but live service path was unavailable in this environment.

### Contracts / typecheck

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- contracts generate: **PASSED**
- contracts diff: **zero**
- typecheck: **PASSED**

### Whitespace

```bash
git diff --check
git show --check HEAD
```

Result: clean (`git show --check HEAD`).

## Audit mode status summary

| Mode | Status |
|------|--------|
| Synthetic fixture | PASSED |
| Artifact replay | PASSED |
| Live downstream | NOT_RUN (sidecar 404) |
| Frontend fixture tests | PASSED |

## Explicit statements

- Push: NOT_ATTEMPTED
- Deploy: NOT_ATTEMPTED
- Remote CI: REMOTE_CI_NOT_AVAILABLE
- No architect review/acceptance docs created
- Unrelated untracked paths preserved (`.grace/`, `grace.db`, `skills/`, superpowers plan)
