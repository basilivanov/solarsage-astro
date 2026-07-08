# Wave W0 Rework 01 TZ

Source review:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/02_arch_review.md`

Branch: `main`
Push/deploy: do not push/deploy before architect acceptance

## Task

Resolve every P0, P1, and P2 finding in the architect review. Keep scope inside W0. Do not implement W1-W7 activation/scoring v2.

## Mandatory Changes

1. Make Moon phase fix effective through production cache:
   - bump `TODAY_CONTENT_VERSION` to `6`;
   - use nearest integer display rounding;
   - update version tests;
   - verify fresh production payload and audit oracle.
2. Make oracle failures fail:
   - astronomy/scoring scripts exit non-zero when required checks fail;
   - `make audit-day` propagates failure;
   - add regression coverage.
3. Complete retrograde contract:
   - no `retrograde=False` defaults in audited sidecar/API transport schemas;
   - transit and natal sidecar calculators emit `retrograde = speed < 0`;
   - API derives from speed if explicit flag is omitted;
   - API validation fails when both flag and speed are absent;
   - add sidecar and API tests.
4. Complete day/natal separation:
   - day contexts use `day_scored_signals`;
   - natal background uses `natal_background_signals` only with explicit baseline labeling;
   - tests cover both natal houses and natal aspects.
5. Fix advice consistency:
   - forbidden direct action fails;
   - exact allowed mitigation from docs/15 passes;
   - LLM prompt contains verdict-specific `avoid` rule.
6. Make Moon test cover production implementation, not only a duplicated oracle formula.
7. Make audit reports input/computation-driven; no false Basil/date/score claims for arbitrary runs.
8. Keep canonical 16 root artifacts. Put optional debug details under `debug/` and document them, or remove redundant duplicate artifacts.
9. Make `git show --check HEAD` pass.
10. Correct final report counts and commit identity.

## Required Verification

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

```bash
apps/solarsage/venv/bin/python -m pytest \
  apps/solarsage/tests/test_ephemeris_retrograde.py \
  apps/solarsage/tests/test_services.py \
  -q
```

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

The final audit must prove:

```text
day_status pass=true
all sphere score deltas <= 0.02
retrograde_flag_pass=true
moon_phase.pass=true
Moon display is 44% for oracle 43.792%
final payload contentVersion=6
```

Also run:

```bash
git show --check HEAD
git status --short --branch
```

## Deliverables

- implementation and tests;
- regenerated canonical W0 artifacts;
- report:
  `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/04_rework_01_report.md`;
- commit, no push.

## Callback

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 01 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/04_rework_01_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/02_arch_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
