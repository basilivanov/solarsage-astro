# W11 Rework 01 Architect Review

Status: REWORK REQUIRED
Reviewed commits: `a710bec`, `28ec337`
Date: 2026-07-10

## Decision

Rework 01 closes the original P0 architecture failures and all reported suites pass. A small second rework is still required because several artifact and hard-comparison contracts remain incomplete.

## Findings

### P0 — Convergence and status comparisons are still not exact

Evidence:

- `scripts/audit_downstream_v2.py` checks convergence families only when `prod_families` is truthy:

```python
if prod_families and prod_families != families:
```

If production omits the convergence debug entry entirely while keeping the numeric bonus, the audit accepts it. Rework 01 required exact family-set comparison.

- Day-status comparison skips `rule` completely and only compares values when both are numeric. It therefore accepts:
  - wrong `rule`;
  - expected `ratio=null` with an actual numeric ratio;
  - missing/non-numeric components.

Section 7.9 requires a hard fail if status or any component differs.

Required fix:

- When convergence is expected, require the debug entry, exact family set, exact family count, convergence contribution source id, and contribution amount.
- Compare all status-breakdown keys. Numeric values use tolerance; strings and nullability use exact equality.
- Add mutation regressions for missing convergence debug families and wrong status `rule`/ratio.

### P1 — Contribution trace omits the formula inputs

Evidence:

Committed `05_contribution_trace.csv` has empty values for:

```text
strength,family_weight,target_weight,polarity_modifier
```

The script explicitly writes empty strings at lines 931-934.

Impact:

The artifact contains an expected amount but does not show the inputs needed to independently review the required formula.

Required fix:

- Preserve the formula input metadata per expected `(activation_id, sphere)` row.
- Fill all required columns for mapped contributions.
- For missing/extra actual rows, retain every independently known input and leave only genuinely unavailable values empty.
- Add an artifact test asserting mapped rows have all four numeric inputs.

### P1 — Cap trace does not reject unexpected cap contributions

Evidence:

The audit validates cap contribution details only when `expected_capped` is true. An unexpected `source=cap` contribution on a sphere that should not be capped is not independently rejected if final score/flag are otherwise unchanged.

Required fix:

- Hard-fail when a non-capped sphere has any cap contribution.
- Hard-fail on duplicate cap contributions.
- Add a mutation regression.

### P1 — Unknown payload score sources are warnings

Evidence:

An unknown payload score contribution source records `payload_score_unknown_source` as a warning, leaving summary status `ok`.

Impact:

Acceptance criterion 13 allows only activation ids or the known base/convergence/cap sources. Unknown sources are not traceable.

Required fix:

- Make unknown or missing payload contribution source/id a structured hard failure.
- Add a mutation regression.

### P1 — Committed replay proof is not reproducible from committed inputs

Evidence:

- `00_input_metadata.json` says `artifact_replay`, but the input full V2 payload and day-signals bundle used to create it was generated under a temporary `downstream_valid_v2_src` directory and is not committed.
- The committed folder contains `09_payload_v2.json`, but not the full `raw_today_payload.json` required by `--input-final-payload`.
- The report lists replay as passed but does not include the exact replay command.
- Committed metadata has `git_head=895d50a`, the pre-rework review commit, rather than the code commit that generated the evidence.

Required fix:

- Commit the optional replay inputs under `artifacts/audit/2026-07-08/downstream/debug/`, at minimum:
  - `raw_today_payload.json`;
  - `day_signals.json`.
- Ensure the committed replay can be rerun using only committed paths, for example with committed `01_sidecar_activation_layer.json` plus those debug inputs.
- Generate evidence after the code/test commit so `00_input_metadata.json.git_head` names that code commit.
- Record the exact synthetic and replay commands in the rework report.

### P1 — Frontend assertions are weaker than the TZ

Evidence:

- `ActivationEvidenceCard.downstream.test.tsx` checks evidence text but not rendered technique and target.
- `TodayScreen.v2-downstream.test.tsx` accepts either `today-screen` or the child card for its root check instead of asserting the stable `today-screen` contract.
- `WhyExpanded` test checks title and ids, but not body and technique.
- The frontend test does not validate activation contribution ids from `scoreBreakdown` against `activationEvidence`.

Required fix:

- Assert the actual `today-screen` root.
- Assert target label/key, technique chip, and evidence text from the committed fixture.
- Assert WhyExpanded title, body, and technique.
- Assert every activation contribution id in fixture `scoreBreakdown` is present in fixture `activationEvidence`.

### P2 — Rework report tip is inaccurate

Evidence:

`04_rework_01_report.md` records evidence tip `685871f`; actual tip is `28ec337`.

Required fix:

- Do not invent a self-referential report commit SHA.
- In the next report, record the immutable code/test commit and evidence-generation base SHA. Let architect acceptance record the final docs tip.

## Architect verification

- W11 backend: `32 passed`.
- W10 regressions: `52 passed`.
- Frontend downstream: `4 passed`.
- `pnpm contracts:generate`: zero contract diff.
- `pnpm typecheck`: passed.
- Synthetic audit: passed.
- Valid V2 replay constructed in `/tmp`: passed.
- Whitespace/status: clean except known pre-existing untracked paths.

## Required decision

W11 is not accepted at `28ec337`. Rework 02 is limited to the proof gaps above; no production astrology or scoring changes are needed.
