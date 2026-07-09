# W9 Architect Review

Status: REWORK REQUIRED
Reviewed commit: `ebb1898`
Date: 2026-07-09

## Findings

### P0 — Whitespace gate fails on the committed W9 report

Evidence:

```bash
git diff --check 92fa2fd..HEAD
```

Result:

```text
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md:3: trailing whitespace.
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md:4: trailing whitespace.
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md:5: trailing whitespace.
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md:6: trailing whitespace.
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md:7: trailing whitespace.
```

Impact:

W9 TZ explicitly requires whitespace checks. This blocks acceptance even though the functional focused tests pass.

Required fix:

Remove trailing whitespace, rerun `git diff --check 92fa2fd..HEAD` and `git show --check HEAD`, and record the passing output in the rework report.

### P0 — Agent report records the wrong accepted commit SHA

Evidence:

- actual HEAD: `ebb1898`
- tmux callback: `Commit: ebb1898`
- `01_agent_report.md:183` says ``2e43bcf``
- `01_agent_report.md:185` says `Accepted/agent commit: `2e43bcf``

Impact:

W9 acceptance depends on exact evidence for the final head. A stale or wrong SHA makes the report unsuitable as acceptance evidence and violates the TZ requirement for final commit SHA.

Required fix:

Update the report after the rework commit with the real final commit SHA. Do not leave placeholders or stale SHAs.

### P1 — `frozen-baseline` mode does not provide the payload file that oracle runners read

Evidence:

- In `scripts/audit_today.py:607-610`, frozen mode sets `payload_json = _baseline` but does not write it to `debug/final_today_payload.json`.
- Immediately after that, `run_oracles(...)` is called with `out_dir=debug_dir` at `scripts/audit_today.py:637-644`.
- `run_oracles()` passes `debug/final_today_payload.json` to both scoring and astronomy oracle commands.
- `make audit-day-freeze` does not pass `--skip-oracles`.

Impact:

The new `audit-day-freeze` target can still fail in normal use, or rely on stale debug files from an older run. Frozen mode is supposed to be an honest deterministic baseline review; it must explicitly materialize the exact baseline payload used by the oracle runners.

Required fix:

In frozen mode, write the validated baseline payload to:

- `debug/final_today_payload.json`
- preferably also `debug/final_today_payload.normalized.json` if live mode writes that shape

Do this before `run_oracles()`. Add a regression test that runs frozen mode with oracle runner logic enabled or asserts that `debug/final_today_payload.json` exists before oracle invocation. The test must fail on the current implementation.

### P1 — V1 payload/cache identity can be polluted with V2 calculation version

Evidence:

- `ActivationLayerService.build()` now always returns `calculation_version=CALCULATION_VERSION` at `apps/api/app/services/activation_layer_service.py:120-122`.
- `TodayService.get_today_payload()` always builds an activation layer, even when `should_compute_v2()` is false, at `apps/api/app/services/today_service.py:290-300`.
- `TodayService` then derives `calc_version` from `activation_layer.calculation_version` at `apps/api/app/services/today_service.py:326-328`.
- The payload meta writes that value at `apps/api/app/services/today_service.py:470-483`.

Impact:

V1-only runs can emit/cache `calculation_version="ss-calc-1.1.0"` while still using V1 scoring and `today.v1`. That violates the W9 requirement: "When V1 is selected, the legacy version values may remain, but they must be intentional and covered by tests." It also weakens cache identity because a V1 payload can be keyed with a V2 calculation identity.

Required fix:

Make version identity selected by runtime path, not blindly copied from the local fallback activation layer:

- V1-only path should keep `calculation_version="1"`, `scoring_version=1`, `payload_version="today.v1"`, `frontend_payload_version=1`.
- V2/dual-run selected V2 path should use `ss-calc-1.1.0`, `al-1.0`, `ss-scoring-2.0`, `today.v2`, frontend version 2.
- If local fallback activation layer must carry a calculation version, do not let it overwrite V1 payload/cache identity.

Add regression coverage for a V1-only payload and cache key write identity. Existing tests only assert sidecar is not called; they do not assert the meta/cache versions.

### P2 — Rework process used unsafe git/permission commands

Evidence from tmux:

- `sudo chown ...`
- `rm -f /opt/solarsage-astro/.git/index && git read-tree HEAD`

Impact:

The product diff was recoverable, but deleting `.git/index` and using sudo inside the coder loop can corrupt the shared workspace and makes review evidence harder to trust.

Required fix:

For rework, do not use `sudo`, do not delete `.git/index`, and do not run git repair commands. If a permission issue blocks work, stop and report it. Commit only intended W9 changes.

## Independent Checks Run

Passed:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_meta_versions.py \
  tests/test_activation_layer_contract.py \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_scoring_v2_runtime_flags.py -q
```

Result: `67 passed`.

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest \
  tests/test_activation_layer_endpoint.py \
  tests/test_activation_schema.py \
  tests/test_activation_transits.py \
  tests/test_profections.py \
  tests/test_firdar.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py \
  tests/test_secondary_progressions.py \
  tests/test_solar_arc.py \
  tests/test_eclipse_window.py \
  tests/test_activation_layer_family_coverage.py -q
```

Result: `144 passed, 1 warning`.

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_logging_guardrails.py
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result: all passed; generated contracts diff was empty.

Failed:

```bash
git diff --check 92fa2fd..HEAD
```

Result: failed on trailing whitespace in `01_agent_report.md`.

## Decision

W9 is not accepted at `ebb1898`. The implementation is directionally close, but acceptance evidence is still not trustworthy enough because a required git gate fails, the report names the wrong commit, and frozen-baseline mode can feed missing/stale payload files into oracle runners.
