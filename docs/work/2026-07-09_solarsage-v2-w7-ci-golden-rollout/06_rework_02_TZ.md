# W7 Rework 02 TZ — Finish Portable Golden Gates

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push or deploy.

## Read First

Read:

```text
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/05_rework_01_review.md
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/03_rework_01_TZ.md
```

## Goal

Resolve the remaining blockers in W7 Rework 01. This is a correctness/privacy cleanup, not a new feature wave.

## Required Work

### 1. Make verification truthful and green

- Remove all trailing whitespace.
- Do not use `sudo` in W7 verification.
- Make sure `git show --check HEAD` and the full baseline `git diff ... --check` pass before reporting.

### 2. Make forbidden-token scan return no matches

The exact command below must return no output:

```bash
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\\.9394|32\\.8144|43\\.59699|39\\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
```

Do not store those literal tokens in the rollout checker. If the checker still needs a privacy denylist, construct values from non-matching fragments or use hashes/patterns that do not contain the exact private tokens.

### 3. Remove private-derived raw inputs

Delete or replace:

```text
apps/api/tests/fixtures/golden/inputs/raw_natal_context.json
apps/api/tests/fixtures/golden/inputs/raw_activations.json
apps/api/tests/fixtures/golden/inputs/raw_transits.json
apps/api/tests/fixtures/golden/inputs/raw_signals.csv
```

Do not keep Basil-derived natal longitudes, activation source/target longitudes, or raw sidecar output as W7 committed fixtures.

Preferred replacement:

- `test_golden_basil_2026_07_08.py` validates compact snapshot invariants only.
- `check_v2_performance_budgets.py` uses a small manually-authored synthetic fixture, for example `apps/api/tests/fixtures/golden/performance_case.json`, with enough synthetic signals/activation evidence to exercise scoring and semantic paths.

The following scan must return no output:

```bash
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
```

### 4. Finish rollout checker evidence validation

Update `scripts/check_solarsage_v2_rollout_gates.py` so it verifies:

- W0-W6 acceptance docs exist:
  - `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/29_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/05_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w2-activation-layer/11_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/08_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-2-profections/05_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-3-firdar/14_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-4-returns/08_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-5-progressions/08_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/05_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/17_arch_acceptance.md`
  - `docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/23_rework_07_review.md`
  - `docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/08_arch_accept.md`
- every V1/V2 status flip is represented in a `status_flips` fixture field with `from`, `to`, `explained: true`, and non-empty `evidence_ids`;
- performance budget script actually passes;
- rollback docs include exact env flags, restart/redeploy steps, and a health/smoke verification step;
- frontend compatibility tests exist.

### 5. Centralize top signal normalization or revert it

Current state still has duplicated conversion in `today_interpretation_service.py`.

Choose one:

- revert runtime service changes if W7 no longer needs them;
- or move the helper to a neutral shared module, use it from both services, and add focused tests.

Required behavior:

- dict-shaped signals with required fields are accepted;
- malformed dicts missing `type` or `planet` are ignored or rejected explicitly;
- no empty-string required `AstroSignal` fields.

### 6. Script structure/logging

For W7-created scripts:

```text
scripts/check_audit_golden.py
scripts/check_v2_performance_budgets.py
scripts/check_solarsage_v2_rollout_gates.py
```

Add full header/module contract/module map/function contracts in the style used by `apps/api/app/core/logging.py`.

For logging:

- use the repo's existing structured logging pattern where practical;
- if importing `app.core.logging` is unsuitable for standalone CLI scripts, keep a small local CLI logger but document it in the module contract and keep its envelope consistent;
- no trailing whitespace.

## Required Verification

Run and report exact output:

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\\.9394|32\\.8144|43\\.59699|39\\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
python3 scripts/check_logging_guardrails.py
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

Both `rg` commands must return no matches.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/07_rework_02_report.md
```

Include:

- files changed;
- what was removed from Rework 01;
- fixture privacy/size summary including any remaining synthetic performance fixture;
- rollout checker evidence summary;
- runtime normalization decision and tests;
- exact verification outputs;
- push/deploy status: `NOT_ATTEMPTED`.

Commit implementation and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W7 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/06_rework_02_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
