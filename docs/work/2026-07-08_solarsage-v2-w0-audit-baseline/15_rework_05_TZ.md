# Wave W0 Rework 05 TZ

Branch: `main`

Push/deploy: do not push/deploy before architect acceptance.

Source review:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/14_rework_04_review.md`

## Task

Resolve the remaining W0 audit architecture and trust issues. Do not start W1-W7. Do not change scoring semantics. Do not change production frontend.

## Mandatory Changes

1. Make default `make audit-day` deterministic without relying on a pre-existing DB cache row.
   - Default `make audit-day` is a baseline verifier.
   - It must not silently refresh canonical LLM text.
   - It must not call live LLM generation for volatile text in order to create root canonical artifacts.
   - Implement one of these architectures:
     - stable canonical projection: recompute deterministic astronomy/scoring/evidence fields, but freeze/normalize/hash/load baseline LLM text from committed fixture data;
     - fail-fast baseline verifier: if the exact expected baseline payload is missing, exit before writing canonical artifacts and tell the operator to run a separate non-destructive live refresh command.
   - Preferred: stable projection that can run in CI without an existing `TodayPayloadCache`.

2. Make `--live-llm-sample` non-destructive.
   - It must not overwrite `artifacts/audit/<DATE>/00_*` through `15_*` by default.
   - Write live samples to a separate path, for example:

```text
artifacts/audit/<DATE>/live/<timestamp>/
```

   - If you keep a custom `--out`, ensure live mode cannot accidentally clobber the canonical root path.
   - Update `docs/audits/README.md` and the report to describe default baseline mode vs live sample mode accurately.

3. Remove payload-level advice contradictions in `WhyThisHappens`.
   - Fix `apps/api/app/services/semantic_service.py` practical bullets so they are evidence-aware or generic.
   - Do not say relationships are favorable when `ConcreteAdvice.relationships.verdict == "avoid"`.
   - Avoid hardcoded domain-specific positive claims based only on `day_status`.
   - Regenerate the W0 canonical artifacts after the fix.

4. Add regression coverage.
   - Test default audit determinism without relying on cache or, if you implement fail-fast, test that it fails before writing canonical artifacts when baseline input is missing.
   - Test that live sample mode writes outside canonical root and does not dirty root `artifacts/audit/2026-07-08`.
   - Test that payload-level practical advice has no relationship outreach contradiction when relationships verdict is `avoid`.

5. Write report:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/16_rework_05_report.md`

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

Run deterministic baseline verification:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

Run live mode isolation verification:

```bash
git diff --exit-code -- artifacts/audit/2026-07-08
# run your live sample command here
git diff --exit-code -- artifacts/audit/2026-07-08
```

Then verify:

```bash
jq -r '.meta.content_version, .meta.cached, .meta.generated_at' artifacts/audit/2026-07-08/11_final_today_payload.json
jq '.moon_phase, .retrograde_flag_pass' artifacts/audit/2026-07-08/13_astronomy_oracle_summary.json
jq '.comparison.day_status, .comparison.top_signals' artifacts/audit/2026-07-08/12_scoring_oracle_comparison.json
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\\| N/A \\| N/A \\| N/A \\||Рекомендация временно недоступна\\.|Общайся с близкими.*отнош' artifacts/audit/2026-07-08/14_claims_audit.md artifacts/audit/2026-07-08/11_final_today_payload.json
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

In `16_rework_05_report.md`, include:

- exact architecture chosen for cold-cache-safe deterministic baseline;
- exact live sample output path;
- proof that live sample does not modify canonical root artifacts;
- proof that `WhyThisHappens` has no relationship outreach contradiction when relationships verdict is `avoid`;
- verification command outputs;
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
  -d '{"prompt":"Wave W0 Rework 05 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/16_rework_05_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/14_rework_04_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/15_rework_05_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
