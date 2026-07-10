# W11 Rework 02 TZ

Status: READY_FOR_CODER
Date: 2026-07-10
Base reviewed commit: `28ec337`
Architect review: `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/05_rework_01_review.md`

## Goal

Close the remaining exact-trace, reproducibility, and frontend assertion gaps without changing production astrology, scoring formulas, rollout, or UI design.

## Required fixes

### 1. Exact convergence and status checks

- For every sphere with expected convergence bonus greater than zero, require:
  - production debug entry exists;
  - exact `families` set;
  - exact `family_count`;
  - exactly one `source=convergence` contribution;
  - `source_id=convergence:<sphere>`;
  - contribution amount equals expected bonus within `0.0001`.
- Compare every day-status breakdown component:
  - numeric values with tolerance;
  - `rule` and other strings exactly;
  - null/non-null exactly.
- Add regressions for missing convergence debug trace and wrong status `rule`/ratio.

### 2. Complete `05_contribution_trace.csv`

- Store formula metadata while building expected mappings.
- Fill `strength`, `family_weight`, `target_weight`, and `polarity_modifier` for every mapped expected contribution row.
- Add a test that reads the CSV and asserts those fields are non-empty numeric values for `status=ok` mapped rows.

### 3. Exact cap trace

- Require exactly one cap contribution when cap is expected.
- Require zero cap contributions when cap is not expected.
- Reject duplicate/unexpected cap contributions.
- Keep exact source id and amount checks.
- Add a mutation regression for an unexpected cap contribution.

### 4. Payload contribution source policy

- Treat missing/unknown payload score contribution `source` or `source_id` as a hard failure, not a warning.
- Add a mutation regression.

### 5. Reproducible committed replay

Use a two-stage commit flow:

1. Commit code/tests first.
2. At that code SHA, regenerate the deterministic evidence and commit it with the report.

Commit under `artifacts/audit/2026-07-08/downstream/debug/`:

- `raw_today_payload.json`;
- `day_signals.json`.

The committed replay command must work using only committed paths:

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

Regenerate committed `00..12` so `00_input_metadata.json.git_head` equals the immutable code/test commit SHA used for evidence generation.

### 6. Complete frontend proof

- `ActivationEvidenceCard.downstream.test.tsx` must assert target and technique plus evidence from the committed fixture.
- `TodayScreen.v2-downstream.test.tsx` must assert `screen.getByTestId("today-screen")` directly.
- WhyExpanded test must assert title, body, and technique from the committed fixture.
- Assert all activation contribution ids in `scoreBreakdown` exist in `activationEvidence`.

### 7. Report

Create:

```text
docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/07_rework_02_report.md
```

Include:

- immutable code/test commit SHA;
- evidence-generation base SHA;
- exact synthetic and committed replay commands/results;
- backend/frontend/contracts/typecheck/whitespace results;
- live audit status;
- remote CI, push, deploy status.

Do not claim the SHA of the commit that contains the report itself. Architect acceptance will record the final accepted tip.

## Required verification

Run the two backend suites, frontend suite, contracts generation/diff, typecheck, synthetic audit, committed-path replay command, `git diff --check`, `git show --check`, and final status exactly as in the previous TZ plus the new mutation/CSV tests.

## Git/process constraints

- No subagents.
- Normal git index only.
- No sudo for repository writes.
- Do not push or deploy.
- Preserve the known unrelated untracked paths.
