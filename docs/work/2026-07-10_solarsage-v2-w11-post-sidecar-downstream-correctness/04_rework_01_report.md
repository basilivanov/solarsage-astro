# W11 Rework 01 Report

Date: 2026-07-10
Base reviewed commits: `aecc699` / `a5f2bd6` (review) / current pre-rework tip `895d50a`
Final rework code/tests commit: `a327abd`
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE

## Process

- Normal git index only (no alternate `GIT_INDEX_FILE`)
- No sudo / no `.git/index` deletion / no hard reset / no checkout
- No push/deploy
- Left known untracked alone: `.grace/`, `grace.db`, `skills/`, superpowers plan

## Fixes closed

### P0 independent expected math
- Removed all private production scoring helper calls from expected path
- Independent canon-based reducers for mapping, amounts, unique-family convergence, raw score, dominance cap, day status (incl. `aspect_rules.v1.yml`)
- Exact multiset checks for missing/extra/duplicate activation contributions
- Exact convergence family-set comparison + required convergence contribution
- Cap calculated from independent expected raw scores

### P0 provenance
- Replay/live never synthesize missing V2 body
- V1 replay fails with structured `payload_v2_missing`
- Synthetic mode may build V2 via SemanticV2Service and is labeled `synthetic_fixture`
- `09_payload_v2.json` is normalized copy of actual payload V2 only
- Committed honest valid-V2 replay artifacts `artifacts/audit/2026-07-08/downstream/00..12`

### P0 live day_signals path
- Live mode reconstructs signals via transits → NormalizationService → DayDeltaService → filter_day_scored_signals
- Live still NOT_RUN here due sidecar 404 (implementation present)

### P1 payload/score/why validation
- Payload score contribution source/id policies enforced
- whyToday ids must exist in activationEvidence
- contribution count uses contribution rows

### P1 fixtures/tests
- All 12 fixtures have full `expected` contracts
- Dominance fixture deterministically caps
- Negative mutation tests added (lost id, missing contrib, amount mismatch, convergence mismatch, missing payload evidence, unmapped policy, V1 replay reject)
- Exact mapping/amount invariant tests

### P1 frontend
- `11_frontend_fixture.json` is AdaptedTodayPayload-compatible (camelCase V2)
- assertions derived from same payload (`has_v2` consistency)
- Frontend tests consume committed fixture, validate schema, render real `TodayScreen`, open `WhyExpanded`, render `DevAuditDrawer`

### P2 GRACE
- Module contract/map markup added to new audit script and new test files

## Files changed

- `scripts/audit_downstream_v2.py` (rewrite)
- `apps/api/tests/fixtures/downstream_v2/*`
- `apps/api/tests/test_downstream_v2_audit.py`
- `apps/api/tests/test_scoring_v2_downstream_invariants.py`
- `apps/api/tests/test_payload_v2_downstream_mapping.py`
- `__tests__/components/ActivationEvidenceCard.downstream.test.tsx`
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`
- `artifacts/audit/2026-07-08/downstream/00..12`
- `docs/work/.../04_rework_01_report.md`

## Verification

### Backend W11 + scoring

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_downstream_v2_audit.py \
  tests/test_scoring_v2_downstream_invariants.py \
  tests/test_payload_v2_downstream_mapping.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_breakdown_contract.py -q
```

Result: **32 passed**

### W10 regressions

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py -q
```

Result: **52 passed**

### Frontend

```bash
npx vitest run \
  __tests__/components/ActivationEvidenceCard.downstream.test.tsx \
  __tests__/components/TodayScreen.v2-downstream.test.tsx
```

Result: **4 passed**

### Contracts / typecheck

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result: generate **PASSED**, contracts **zero diff**, typecheck **PASSED**

### Audit modes

| Mode | Status |
|------|--------|
| Synthetic | PASSED |
| Valid V2 artifact replay | PASSED |
| V1 replay negative | PASSED (fails as required) |
| Live | NOT_RUN (sidecar `404 /v1/activation-layer`) |
| Frontend fixture tests | PASSED |

### Whitespace / status

Recorded after commit:

```bash
git diff --check a5f2bd6..HEAD
git show --check HEAD
git status --short --branch
```

## Explicit statements

- Push: NOT_ATTEMPTED
- Deploy: NOT_ATTEMPTED
- Remote CI: REMOTE_CI_NOT_AVAILABLE
- Normal git index used
- Final status clean except known untracked: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
