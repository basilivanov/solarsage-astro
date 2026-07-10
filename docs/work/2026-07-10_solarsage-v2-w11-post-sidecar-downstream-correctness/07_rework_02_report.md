# W11 Rework 02 Report

Date: 2026-07-10
Base reviewed commit: `d5f1242` / prior tip `28ec337`
Architect review: `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/05_rework_01_review.md`
Rework TZ: `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/06_rework_02_TZ.md`

## Immutable SHAs

| Role | SHA |
|------|-----|
| **Immutable code/test commit** | `2891217` |
| **Evidence-generation base** | `2891217` |

Do not treat this report file's own commit as the code/test SHA. Architect acceptance records the final docs tip.

Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE

## Process

- Normal git index only
- No sudo repository writes
- No push / deploy
- Known unrelated untracked left alone: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- Two-stage flow: code/tests commit first (`2891217`), then evidence regeneration at that SHA + report packaging

## Closed findings

### 1. Exact convergence and status checks

- When expected convergence bonus > 0, audit now requires:
  - production `debug.convergence_by_sphere[sphere]` entry
  - exact `families` set
  - exact `family_count`
  - exactly one `source=convergence` contribution
  - `source_id=convergence:<sphere>`
  - contribution amount equals expected bonus within `0.0001`
- Day-status compares **every** breakdown key:
  - numerics with tolerance
  - `rule` and other strings exactly
  - null / non-null exactly
- Mutations: missing convergence debug; wrong status `rule`; ratio nullability mismatch

### 2. Complete `05_contribution_trace.csv`

- Formula metadata stored while building expected mappings
- Mapped rows fill `strength`, `family_weight`, `target_weight`, `polarity_modifier`
- Test asserts non-empty numeric inputs for `status=ok` rows

### 3. Exact cap trace

- Exactly one cap contribution when cap expected
- Zero cap contributions when not expected (including raw ≤ 0 spheres)
- Hard-fail unexpected / duplicate cap
- Mutation: unexpected cap contribution

### 4. Payload contribution source policy

- Missing / unknown `source` or `source_id` → hard failure (`payload_score_unknown_source`)
- Mutation regression added

### 5. Reproducible committed replay

Committed under `artifacts/audit/2026-07-08/downstream/debug/`:

- `raw_today_payload.json`
- `day_signals.json`

`00_input_metadata.json.git_head` = `2891217` (code/test commit used for evidence generation).

### 6. Frontend proof

- `ActivationEvidenceCard`: evidence text + target label + technique chips from committed fixture
- `TodayScreen`: asserts `screen.getByTestId("today-screen")` directly
- `WhyExpanded`: title, body, technique
- All activation contribution ids in `scoreBreakdown` must exist in `activationEvidence`

## Commands

### Synthetic

```bash
apps/api/.venv/bin/python scripts/audit_downstream_v2.py \
  --synthetic-fixture apps/api/tests/fixtures/downstream_v2/08_convergence_multi_family.json \
  --date 2026-07-08 \
  --out /tmp/w11-synthetic-final \
  --fail-on-unmapped false
```

Result: **PASSED** (`status=ok`, `failure_count=0`)

### Committed-path replay (only committed inputs)

```bash
apps/api/.venv/bin/python scripts/audit_downstream_v2.py \
  --user-id synthetic \
  --date 2026-07-08 \
  --out /tmp/w11-replay-final \
  --input-activation-layer artifacts/audit/2026-07-08/downstream/01_sidecar_activation_layer.json \
  --input-final-payload artifacts/audit/2026-07-08/downstream/debug/raw_today_payload.json \
  --input-day-signals artifacts/audit/2026-07-08/downstream/debug/day_signals.json \
  --fail-on-unmapped false
```

Result: **PASSED** (`status=ok`, `failure_count=0`); metadata `git_head=2891217`, mode `artifact_replay`

### Live

```bash
make audit-downstream-v2 USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

Result: **NOT_RUN** (sidecar still returns 404 on `/v1/activation-layer`; same environmental block as Rework 01)

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

Result: **38 passed**

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

### Whitespace / status

```bash
git show --check 2891217
git status --short --branch
```

Result: clean whitespace on code commit; working tree after evidence packaging contains only intended artifact/report paths plus known untracked.

## Modified files (code/test commit `2891217`)

- `scripts/audit_downstream_v2.py`
- `apps/api/tests/test_downstream_v2_audit.py`
- `__tests__/components/ActivationEvidenceCard.downstream.test.tsx`
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`

## Evidence packaging (post-code commit)

- `artifacts/audit/2026-07-08/downstream/00..12` regenerated at `2891217`
- `artifacts/audit/2026-07-08/downstream/debug/raw_today_payload.json`
- `artifacts/audit/2026-07-08/downstream/debug/day_signals.json`
- `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/07_rework_02_report.md`

## Scope discipline

- No production astrology / scoring formula retunes
- No frontend redesign
- No rollout / push / deploy
