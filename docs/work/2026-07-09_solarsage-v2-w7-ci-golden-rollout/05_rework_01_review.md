# W7 Rework 01 Architect Review

Status: REWORK REQUIRED
Reviewed range: `5ab95c0..81a864e`

## Findings

### P0 — Reported verification is false: whitespace gate fails

Evidence:
- `git show --check HEAD` exits non-zero.
- `git diff --check 5ab95c0..HEAD` reports trailing whitespace in:
  - `scripts/check_audit_golden.py:41,43,50,56`
  - `scripts/check_solarsage_v2_rollout_gates.py:53,55,77,85,89,96,98,157`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/04_rework_01_report.md` says `git show --check HEAD` was clean.

Impact:
- W7 cannot be accepted because a required gate is red.
- The report cannot be trusted as written.

Required fix:
- Remove trailing whitespace.
- Re-run `git show --check HEAD` and `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check`.
- Report the real output. Do not use `sudo` for git checks.

### P0 — Required forbidden-token scan still fails

Evidence:
- The exact command from Rework 01 TZ still returns matches in `scripts/check_solarsage_v2_rollout_gates.py:26-34` because the checker stores the forbidden private strings literally.
- The report says this is an exception, but the TZ explicitly required the command to return no matches.

Impact:
- The privacy gate cannot prove that W7 files are clean using the agreed command.
- Future reviewers will see a red privacy check every time.

Required fix:
- Do not keep literal private tokens inside files covered by the `rg` command.
- The checker may construct forbidden strings at runtime from non-matching fragments, use hashes, or use regex fragments that do not contain the literal secrets.
- The exact `rg` command in the TZ must return no matches.

### P0 — New `golden/inputs` are still private-derived raw natal/activation artifacts

Evidence:
- `apps/api/tests/fixtures/golden/inputs/raw_natal_context.json` contains natal planet/house longitudes.
- `apps/api/tests/fixtures/golden/inputs/raw_activations.json` contains a large activation layer derived from the original private natal context.
- `apps/api/tests/test_golden_basil_2026_07_08.py` still recomputes the day pipeline from these raw inputs.

Impact:
- Replacing explicit name/date with "Mock" is not enough. Raw natal positions and activation outputs are still profile-derived technical data.
- W7 was supposed to keep technical golden outputs only for the scrubbed Basil case, not raw natal/profile-derived inputs.
- The new `inputs/` directory also pushes the golden folder over the requested size target when included.

Required fix:
- Remove private-derived raw inputs from W7 committed fixtures.
- Make the Basil-named fixture test a compact snapshot/invariant test only, or rename it to a synthetic case.
- If performance tests need inputs, use a small manually-created synthetic `performance_case` fixture, not copied private-derived natal/transit/activation data.

### P1 — Rollout checker still does not validate the required gates

Evidence:
- `scripts/check_solarsage_v2_rollout_gates.py` checks only W5/W6 docs, despite W7 requiring W0-W6 evidence.
- It checks that the performance script exists but does not run it.
- It accepts rollback documentation when the markdown merely contains the word `rollback`.
- It only checks that a status flip has some `activationEvidence`, not a structured flip record with explanation and evidence references.

Impact:
- The rollout checker can still pass when core rollout evidence is missing.
- This is not a real readiness gate.

Required fix:
- Validate all W0-W6 acceptance docs explicitly.
- Run the performance budget checker or call an importable helper from it.
- Validate rollback docs contain both env flags and operational steps: service restart/redeploy and health/smoke verification.
- Add/validate `status_flips` records in the golden V2 snapshot: `from`, `to`, `explained: true`, and `evidence_ids`.

### P1 — Runtime normalization is still duplicated and still has unsafe empty defaults

Evidence:
- `apps/api/app/services/today_service.py` now has `_normalize_top_signals`.
- `apps/api/app/services/today_interpretation_service.py:332-351` still contains the old conversion block and still creates `AstroSignalModel(type=... or "", planet=... or "")`.

Impact:
- The runtime fix is not actually centralized.
- Malformed required signal fields can still be silently converted to empty strings in `TodayInterpretationService`.

Required fix:
- Remove the duplicate conversion from `TodayInterpretationService`, or move the helper to a neutral shared module and use it from both services.
- Add focused tests for dict-shaped top signals and malformed dicts.
- Malformed required fields must be ignored with explicit behavior or raise a controlled error; do not create empty-string `AstroSignal` objects.

### P2 — New scripts still do not follow the agreed GRACE/logging standard cleanly

Evidence:
- New scripts have partial headers but not the full canon shape used elsewhere: no module map, no function contracts, and header order is inconsistent with local examples.
- They hand-roll `log_event()` JSON instead of using the repo's structured logging surface or a documented local CLI logging wrapper.
- Some verification output uses `sudo`, which should not be required for CI/local gates.

Impact:
- The scripts are harder to audit and inconsistent with the internal standard.

Required fix:
- Add full AI header, module contract, module map, and function contracts for each new script.
- Use the repo's structured logging pattern where practical, or create a tiny local CLI logger with the same envelope and document why `app.core.logging` is not used.
- All W7 scripts/checks must run as the normal repo user.

## Required Verification After Rework

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

The two `rg` commands must return no matches.
