# W7 Architect Review

Status: REWORK REQUIRED
Reviewed range: `13eb6d7..91cad73`

## Findings

### P0 — W7 CI gates are not reproducible outside this host and commit private Basil profile data

Evidence:
- `apps/api/tests/test_golden_basil_2026_07_08.py:15-31` creates a test user with real Telegram id `833478509`, username `basil_ivanov`, real birth date/time/city, birth coordinates, and current coordinates.
- `apps/api/tests/test_golden_basil_2026_07_08.py:42-44` loads `/opt/solarsage-astro/artifacts/audit/2026-07-08`.
- `scripts/check_v2_performance_budgets.py:8` hardcodes `/opt/solarsage-astro/apps/api`; `scripts/check_v2_performance_budgets.py:20-32` hardcodes `/opt/solarsage-astro/artifacts/audit/2026-07-08`.
- `.github/workflows/ci.yml:70-81` runs all backend tests and the new scripts on a GitHub runner checkout, where `/opt/solarsage-astro/...` is not guaranteed.

Impact:
- The new CI gates can pass only on this server shape. They are not deterministic public-CI checks.
- The newly committed W7 test code exposes private production-user identity and birth/profile data.
- This violates the W7 non-negotiable constraints: no private Basil data in CI fixtures/tests, no live/private host state, no production-path assumptions.

Required fix:
- Remove all W7 references to the real Basil Telegram id, username, birth data, city, birth/current coordinates, and private audit path.
- Replace `test_golden_basil_2026_07_08.py` with a synthetic or fully scrubbed fixture-backed test. It must not create a real Basil profile.
- Resolve repo paths from `Path(__file__).resolve()` or pytest fixtures; no absolute `/opt/solarsage-astro` in W7 scripts/tests.
- W7 gates must run from any checkout without production DB, live sidecar, live LLM, or private artifacts.

### P0 — Golden fixtures contain private-derived activation/progression data and are oversized full payload dumps

Evidence:
- New fixtures total more than 2 MB and about 68k added lines.
- `apps/api/tests/fixtures/golden/basil_2026_07_08_v2.json` contains repeated `birth_local_date: "1980-10-30"` and progressed timestamps derived from that private birth date.
- Synthetic fixtures `mercury_convergence_case_v2.json` and `antidominance_case_v2.json` appear to be full copies of the Basil V2 payload with small edits, so they also carry the same private-derived activation/progression data.

Impact:
- The fixtures are not scrubbed, despite the report saying they are.
- Reviewability and maintenance suffer: tiny convergence/anti-dominance cases should not require 700 KB payload dumps each.
- Snapshot churn will be high and noisy.

Required fix:
- Replace the full payload dumps with compact, contract-specific golden snapshots. Keep only the fields actually asserted by W7: status, sphere scores, top signal order, V2 score breakdown/evidence ids/technique families, flip explanations, and metadata.
- Synthetic convergence/anti-dominance fixtures must be truly synthetic and minimal, not Basil payload copies.
- Add a privacy guard in W7 tests or `check_audit_golden.py` that fails on forbidden tokens in W7 fixtures/tests: `833478509`, `basil_ivanov`, `1980-10-30`, `Мончегорск`, raw Basil coordinates, and private audit paths.

### P1 — Rollout gate checker self-certifies markdown checkboxes instead of validating evidence

Evidence:
- `docs/rollout/solarsage_v2_rollout_gates.md:5-12` marks every rollout gate as ready.
- `scripts/check_solarsage_v2_rollout_gates.py:29-43` only parses `- [x] gate_name: true` lines and reports success when the document says true.

Impact:
- The checker does not prove W0-W6 accept docs exist.
- It does not inspect dual-run evidence, unexplained flips, frontend compatibility tests, rollback procedure quality, or performance budget execution.
- Any future edit can make the rollout gate pass by changing text, not by satisfying the gate.

Required fix:
- Make the checker independently validate the gates from repository artifacts.
- At minimum it must verify:
  - required W0-W6 accept/review docs exist;
  - W7 golden fixtures include no unexplained flips;
  - every recorded flip has activation/evidence references;
  - frontend compatibility tests named in the checker exist;
  - rollback docs include exact env flags and restart/redeploy steps;
  - performance budget command exists and passes.
- The markdown may document status, but the checker must not trust checklist text as the source of truth.

### P1 — Runtime service changes are unscoped and not covered by a focused regression

Evidence:
- `apps/api/app/services/today_service.py` and `apps/api/app/services/today_interpretation_service.py` were modified in a W7 guardrail wave.
- `TodayService._build_top_flag()` now accepts dicts but uses direct indexing for dict keys before validation.
- `TodayInterpretationService.build()` creates `AstroSignal` objects from dicts with empty string defaults for required fields.

Impact:
- This changes production behavior while W7 was supposed to add proof/guardrails, not alter scoring/rendering paths.
- Empty-string signal normalization can hide malformed data instead of failing visibly.
- There is no focused test proving dict-shaped `top_signals` are a real supported boundary and that malformed dicts are rejected or ignored safely.

Required fix:
- If these runtime changes were only needed to generate W7 fixtures, revert them.
- If they fix a real production bug, keep them but move normalization into a small shared helper with explicit validation, no arbitrary empty-string required fields, and focused tests.

### P2 — New Python scripts do not follow the repo's GRACE/structured logging standard

Evidence:
- `scripts/check_audit_golden.py`, `scripts/check_v2_performance_budgets.py`, and `scripts/check_solarsage_v2_rollout_gates.py` have no GRACE AI header/module contract.
- They use ad-hoc `print()` only and do not document/employ structured logs.

Impact:
- This violates the repo agent standard for newly created files and makes future audit tooling inconsistent with the rest of the project.

Required fix:
- Add the GRACE header/module contract to every new script.
- Use `GraceLogger` for machine-readable events, while retaining concise CLI output if useful.

## Verification Expected After Rework

The next report must include exact outputs for:

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
