# Wave W0 Rework 02 TZ

Source review:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/05_rework_01_review.md`

Branch: `main`
Push/deploy: do not push/deploy before architect acceptance

## Task

Resolve every finding from Rework 01 review. Keep scope inside W0. Do not implement W1-W7 activation/scoring v2.

## Mandatory Changes

1. Make scoring oracle fail on top-signal mismatch:
   - include `comparison.top_signals.pass` in non-zero exit logic;
   - add a regression test where day status and sphere scores pass but top signals mismatch.
2. Replace hardcoded `14_claims_audit.md` generation:
   - base it on the actual generated `TodayPayload` and artifact values;
   - no stale Basil-specific old text in generic runs;
   - if automatic evidence classification is incomplete, state that honestly and list actual payload excerpts for manual review.
3. Fix audit docs:
   - `docs/audits/README.md` says 16 canonical root files, not 18;
   - document optional `debug/`;
   - update or clearly label `docs/audits/2026-07-08-solarsage-independent-audit.md` so it does not present pre-fix failures as current post-W0 state.
4. Remove remaining silent retrograde defaults:
   - `NatalPreviewChartPlanet.retrograde`;
   - `NatalChartPlanet.retrograde`;
   - add regression coverage so missing retrograde is not silently interpreted as `False`.
5. Fix final report commit identity.
6. Leave a clean tracked worktree after commit.

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
```

The final audit must prove:

```text
day_status pass=true
all sphere score deltas <= 0.02
top_signals pass=true
retrograde_flag_pass=true
moon_phase.pass=true
Moon display is 44% for oracle 43.792%
final payload meta.content_version=6
final payload meta.cached=false
```

Also run:

```bash
git show --check HEAD
git status --short --branch
```

## Deliverables

- implementation and tests;
- regenerated or intentionally restored canonical W0 artifacts;
- report:
  `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/07_rework_02_report.md`;
- commit, no push.

## Callback

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 02 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/07_rework_02_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/05_rework_01_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
