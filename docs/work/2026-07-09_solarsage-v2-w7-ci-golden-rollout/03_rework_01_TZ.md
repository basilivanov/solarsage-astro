# W7 Rework 01 TZ — Make Golden/CI Gates Real, Portable, and Private-Safe

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push or deploy.

## Read First

Read:

```text
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/00_TZ.md
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/02_arch_review.md
```

## Goal

Rework W7 so it is a real deterministic CI/rollout gate:

- no private Basil identity/profile data in new W7 files;
- no dependency on `/opt/solarsage-astro` absolute paths or local private artifacts;
- compact golden snapshots, not full private-derived payload dumps;
- rollout checker validates evidence, not checkbox text;
- new scripts follow the repo GRACE/structured logging standard.

## Required Fixes

### 1. Remove private Basil data and host-specific paths

Remove from all new W7 files:

```text
833478509
basil_ivanov
1980-10-30
Мончегорск
67.9394
32.8144
43.59699
39.72477
/opt/solarsage-astro
```

Scope: at least these files/dirs:

```text
apps/api/tests/fixtures/golden/
apps/api/tests/test_golden_basil_2026_07_08.py
scripts/check_audit_golden.py
scripts/check_v2_performance_budgets.py
scripts/check_solarsage_v2_rollout_gates.py
```

Use repo-relative paths derived from `Path(__file__).resolve()`.

### 2. Replace oversized fixtures with compact snapshots

Delete/rewrite the current full payload dumps.

Keep fixture file names if useful, but the contents must be compact and scrubbed. Preferred shape:

```json
{
  "meta": {
    "fixture_id": "...",
    "source": "synthetic-or-scrubbed-audit-summary",
    "baseline_commit": "...",
    "payload_version": "today.v1|today.v2",
    "scoring_version": "...",
    "canon_versions": {},
    "tolerances": {}
  },
  "date": "2026-07-08",
  "day_status": "...",
  "top_flags": [],
  "sphere_scores": [],
  "v2": {
    "score_breakdown": {},
    "activation_evidence": [],
    "activation_summary": {},
    "status_flips": []
  }
}
```

Rules:

- Do not store full `TodayPayload` dumps.
- Do not store raw natal/profile-derived activation internals such as `birth_local_date` or progressed timestamps derived from private birth data.
- Synthetic convergence and anti-dominance cases must be truly synthetic minimal cases.
- Add a fixture size guard. W7 golden fixtures should be small enough to review; target under 200 KB total for the W7 golden directory unless there is a documented reason.

### 3. Make tests fixture-only and CI-portable

Rewrite `apps/api/tests/test_golden_basil_2026_07_08.py` so it does not create a real Basil profile and does not call private audit artifacts.

Acceptable options:

- Compare compact fixture snapshots against deterministic expected values and invariants.
- Or use a synthetic test profile and committed synthetic raw inputs under `apps/api/tests/fixtures/golden/inputs/`.

Do not require:

- production DB;
- live sidecar;
- live LLM;
- private audit artifacts;
- absolute checkout path.

### 4. Make rollout gate checker validate actual evidence

`scripts/check_solarsage_v2_rollout_gates.py` must not pass just because markdown says `true`.

It must independently verify repository evidence, including:

- W0-W6 accept/review docs exist;
- W7 golden fixtures exist and pass privacy/size checks;
- no status flip is unexplained;
- every status flip has activation/evidence references;
- frontend compatibility tests exist;
- rollback docs contain exact env flags and operational steps;
- performance budget script exists and passes or is invoked through an importable helper.

The markdown document should describe gates and rollback, but the script is the source of truth.

### 5. Runtime changes

For changes in:

```text
apps/api/app/services/today_service.py
apps/api/app/services/today_interpretation_service.py
```

Choose one:

- revert them if they were only needed for fixture generation;
- or keep them only with a small shared normalization helper, explicit malformed-data behavior, and focused regression tests.

Do not silently convert malformed required signal fields to empty strings.

### 6. GRACE/structured logging

Add the GRACE AI header/module contract to every new Python script created by W7.

Use `GraceLogger` for key events. CLI `print()` output may remain, but structured log events must be documented in each module contract.

## Required Verification

Run and report exact output:

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\\.9394|32\\.8144|43\\.59699|39\\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

The `rg` command must return no matches. If it returns matches in old unrelated files, narrow the command only after explaining why the match is outside W7 scope.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/04_rework_01_report.md
```

Include:

- files changed;
- what was removed/replaced from W7 initial implementation;
- fixture privacy/size summary;
- rollout checker evidence summary;
- runtime service decision: reverted or kept with tests;
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
  -d "{\"prompt\":\"Wave W7 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/03_rework_01_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
