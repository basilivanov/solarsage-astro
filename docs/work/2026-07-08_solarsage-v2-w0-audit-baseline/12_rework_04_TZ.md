# Wave W0 Rework 04 TZ

Branch: `main`

Push/deploy: do not push/deploy before architect acceptance.

Source review:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/11_rework_03_review.md`

## Context

Rework 03 fixed snake_case extraction and whitespace, and the scoring/astronomy gates pass.

However, W0 is still not acceptable because the audit baseline is not deterministic. A fresh architect run of `make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08` dirtied canonical committed artifacts with new live LLM text.

There may already be dirty files from that architect verification run:

```text
artifacts/audit/2026-07-08/11_final_today_payload.json
artifacts/audit/2026-07-08/14_claims_audit.md
artifacts/audit/2026-07-08/debug/audit_summary.json
artifacts/audit/2026-07-08/debug/final_today_payload.json
```

Treat that dirty diff as evidence of the bug, not as desired final content.

## Task

Make W0 audit artifacts a stable baseline command while preserving real production runtime behavior.

Do not start W1-W7. Do not change scoring semantics. Do not change production frontend. Do not introduce production runtime mocks.

## Architectural Decision

Default `make audit-day` is the deterministic W0 baseline gate.

It must:

- collect fresh deterministic raw astrology/scoring/semantic evidence;
- run independent scoring and astronomy oracles;
- produce the 16 canonical files under `artifacts/audit/<DATE>/`;
- be safe to run repeatedly in the repo;
- leave `git diff --exit-code -- artifacts/audit/2026-07-08` clean after the committed baseline is regenerated.

Live, non-deterministic LLM sampling is not allowed to rewrite committed canonical baseline files by default.

If you need to keep live LLM sampling, put it behind an explicit opt-in flag/target, for example:

```text
scripts/audit_today.py --live-llm-sample
make audit-day-live USER_ID=... DATE=...
```

The live sample must write to a timestamped or ignored debug path and must not be required for the deterministic baseline gate.

## Mandatory Changes

1. Make canonical audit artifacts deterministic.
   - Remove default forced cache invalidation or isolate it to explicit live mode.
   - Normalize volatile fields in canonical output. At minimum, handle:
     - `meta.generated_at`;
     - live LLM headline/reading/notes/why/advice/planet-interpretation text if it can change between runs.
   - Keep deterministic fields intact:
     - profile;
     - raw sidecar transits/natal context;
     - normalized signals;
     - day-scored signals;
     - scoring outputs;
     - semantic contexts;
     - day summary facts;
     - concrete advice keys, labels, verdicts, confidence, evidence;
     - oracle comparisons.

2. Preserve production behavior.
   - Do not change normal `/day` behavior to use audit snapshots.
   - Do not add runtime mocks to production code.
   - Any deterministic audit projection/freeze must live in audit tooling or explicit test-only code.

3. Strengthen the claims audit gate.
   - `14_claims_audit.md` must not contain `N/A` placeholders for present payload fields.
   - The committed canonical W0 baseline must not contain fallback text such as:
     - `Рекомендация временно недоступна.`
   - Add a regression test or script assertion that fails when fallback advice text appears in the canonical claims audit.
   - If live opt-in sampling captures fallback text, mark the live claims audit as degraded/failed instead of reporting a clean baseline.

4. Add determinism verification.
   - Add a test or script-level check for the canonical projection/claims generation.
   - The final manual verification must include:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

5. Regenerate and commit canonical W0 artifacts after the fix.

6. Write report:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/13_rework_04_report.md`

## Required Verification

Run:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

Run:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_ephemeris_retrograde.py \
  tests/test_services.py \
  -q
```

Run:

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Run:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Then verify:

```bash
jq -r '.meta.content_version, .meta.cached' artifacts/audit/2026-07-08/11_final_today_payload.json
jq '.moon_phase, .retrograde_flag_pass' artifacts/audit/2026-07-08/13_astronomy_oracle_summary.json
jq '.comparison.day_status, .comparison.top_signals' artifacts/audit/2026-07-08/12_scoring_oracle_comparison.json
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\\| N/A \\| N/A \\| N/A \\||Рекомендация временно недоступна\\.' artifacts/audit/2026-07-08/14_claims_audit.md
```

The `rg` command must return no matches.

Also run:

```bash
git diff 2f9173f..HEAD --check
git show --check HEAD
git status --short --branch
```

Final `git status` must show only known unrelated untracked files:

```text
.grace/
grace.db
skills/
docs/superpowers/...
```

## Report Requirements

In `13_rework_04_report.md`, include:

- root cause summary;
- exact design chosen for deterministic canonical artifacts;
- whether a live LLM audit mode exists and where it writes;
- verification command outputs;
- confirmation that two consecutive `make audit-day` runs leave audit artifacts clean;
- commit SHA;
- push/deploy status.

## Commit and Callback

Commit intended changes only. Do not stage unrelated untracked files:

```text
.grace/
grace.db
skills/
docs/superpowers/
```

Do not push/deploy.

When done, run:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 04 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/13_rework_04_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/11_rework_03_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/12_rework_04_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
