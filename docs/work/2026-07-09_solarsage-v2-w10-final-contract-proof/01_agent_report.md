# W10 Agent Report — SolarSage V2 Final Contract Proof

Date: 2026-07-09
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE
Final code/tests commit: `37b30ab`
Evidence docs tip: current main HEAD / callback SHA after report packaging.

## Scope

Final acceptance hardening only:

1. Cache read/write identity consistency for V2-selected runs (including frontend flag off).
2. TodayService emits non-null `payload.v2` whenever selected scoring is `ss-scoring-2.0`.
3. Loud failure when V2 is selected but `dual.v2_result` is missing.
4. Live audit `artifact_source.json` runtime/final identity fields.
5. Live audit `activation_evidence_mapping.json` with `all_sidecar_ids_required`.

No astrology features, scoring formula retunes, or frontend redesign.

## Files changed

- `apps/api/app/services/cache_key_service.py`
- `apps/api/app/services/today_service.py`
- `apps/api/app/services/semantic_v2_service.py`
- `scripts/audit_today.py`
- `apps/api/tests/test_today_cache_v2_key.py`
- `apps/api/tests/test_today_meta_versions.py`
- `apps/api/tests/test_audit_today_modes.py`
- `apps/api/tests/test_audit_activation_sidecar_artifacts.py`
- `docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/01_agent_report.md`

## Implementation summary

### Cache identity

`expected_cache_identity()` now derives identity from selected scoring version via `selected_scoring_version_for_flags()`:

- V2 selected → `ss-calc-1.1.0` / `al-1.0` / `ss-scoring-2.0` / frontend `2`
- V1 selected → legacy `1` / frontend `1`

`SOLARSAGE_V2_FRONTEND_ENABLED` is no longer used in expected cache identity.

### TodayService contract

Selected scoring version is source of truth:

- V2 selected forces meta identity `today.v2` / frontend `2`
- V2 body (`why_evidence_packet`, interpretation V2 inputs, `v2_block`) is built on `v2_selected`, not frontend flag
- Missing `dual.v2_result` raises `RuntimeError("V2 selected but v2_result is missing")`
- Defensive invariant: cannot declare `today.v2` / frontend v2 with `v2=None`

### Semantic V2

`build_v2_block()` requires non-null `scoring_result`.

### Audit proof

Live/frozen audit now:

- writes extended `artifact_source.json` runtime/final fields
- writes `activation_evidence_mapping.json` (debug + root)
- live mode fails on:
  - `today.v2` without `v2` block
  - V2 payload with sidecar activations but zero payload evidence
  - unmapped sidecar activation ids under `all_sidecar_ids_required`
- frozen mode remains non-live and does not claim production proof

## Verification commands and results

### API focused tests

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  -q
```

Result: **47 passed**

### Sidecar profections

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_profections.py -q
```

Result: **15 passed, 1 warning**

### Contracts / typecheck

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- contracts generate: **PASSED**
- contracts diff: **zero** (no schema/OpenAPI shape change required)
- typecheck: **PASSED**

### Whitespace

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Result: clean after commit (no trailing whitespace / extra blank EOF on W10 files).

## Live audit vs mocked tests

Live audit was **not** executed against a real sidecar/DB user path in this wave.

Proof is from **mocked unit/integration tests** of:

- `scripts/audit_today.py` helpers/mapping/assertions
- live mode artifact_source fields
- live fail paths for missing V2 block and unmapped activation ids
- frozen mode non-live provenance

## Acceptance criteria (practical answers)

1. Cache read identity equals write identity for V2 frontend-off: **YES** (regression test).
2. `expected_cache_identity()` no longer uses frontend flag for V2 FE version: **YES**.
3. `TodayService` builds `payload.v2` when selected scoring is V2: **YES**.
4. Missing `v2_result` fails loudly: **YES**.
5. Cannot declare `today.v2`/frontend 2 with `v2=None`: **YES** (runtime invariant + audit assert).
6. Interpretation receives V2 inputs when V2 selected: **YES**.
7. LLM why packet uses V2 evidence when V2 selected: **YES**.
8. `artifact_source.json` has runtime flags/final identity fields: **YES** (mocked live audit test).
9. Live audit fails if V2 meta lacks V2 block: **YES**.
10. Live audit records activation mapping: **YES**.
11. Unmapped sidecar ids fail under `all_sidecar_ids_required`: **YES**.
12. Frozen baseline remains non-live: **YES**.
13–16. Existing W9/audit/V1/Feb29 tests covered by focused suites: **PASS**.
17. Contracts/typecheck: **PASS**, zero contract diff.
18–19. Whitespace gates: after commit.
20. W10 report added: **YES**.

## Process

- No `sudo`
- No `.git/index` deletion/repair (used `GIT_INDEX_FILE` alternate index only)
- No push/deploy
- No hard reset/checkout

## Explicit statements

- Push: NOT_ATTEMPTED
- Deploy: NOT_ATTEMPTED
- Remote CI: REMOTE_CI_NOT_AVAILABLE
