# Rework 01 Report — Wave W4 Scoring V2

## Summary

Fixed P1 base score mismatch (V1 helper reuse), P1 inactive activation handling, P1 V1 aspect thresholds in day status, P1 convergence bounds, P1 Basil test artifact deletion, P2 snake_case serialization, P2 hidden fallback removal, P2 stale comments, P2 GRACE style.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/scoring_v2_service.py` | Reuse V1 helper; filter inactive; V1 thresholds; strict helpers; no hidden fallbacks |
| `apps/api/tests/test_scoring_v2_convergence.py` | Restored exact W4 bounds (1.4x–2.0x); adjusted strengths |
| `apps/api/tests/test_scoring_v2_thresholds.py` | Added V1 base parity test; weak-aspect threshold test |
| `apps/api/tests/test_scoring_v2_breakdown_contract.py` | Added inactive activation regression test |
| `apps/api/tests/test_basil_2026_07_08_v2_golden.py` | Uses `tmp_path` — no tracked artifact deletion |
| `scripts/audit_scoring_v2.py` | Snake_case serialization; GRACE module contract; function contracts |
| `artifacts/audit/2026-07-08/22_scoring_v2_result.json` | Regenerated (snake_case keys) |

## Fixes

### P1: Base score matches V1
Replaced duplicated `_compute_v1_base_scores()` with `ScoringService()._calculate_sphere_scores(day_signals)`. Added regression test `test_v2_base_score_matches_v1()`.

### P1: Inactive activations filtered
`active is not None and not active is False` filter applied in sphere contribution loop, status computation, and top activations. Regression test proves zero activation_score for inactive.

### P1: V1 aspect thresholds in day status
V2 day status now applies `_aspect_threshold(_is_major(...))` before accumulating, matching V1. Weak aspects below threshold produce zero score. Test proves 7 weak trines give `positive_aspect_score = 0`.

### P1: Convergence bounds restored
Mercury convergence test asserts `post_bonus >= 1.4 * base` and `post_bonus <= 2.0 * base` with adjusted fixture strengths to avoid dominance cap interference.

### P1: Basil test uses tmp_path
Generated artifacts written to pytest tmp_path, not tracked paths. No deletion of tracked artifacts.

### P2: Snake_case serialization
Audit script writes `v2_result.model_dump(mode="json", by_alias=False)`. Verification command passes with `result["scoring_version"]`.

### P2: Hidden fallbacks removed
`_required_float()` and `_required_mapping()` strict helpers raise `KeyError` for missing canon keys. `_get_family_independence_weight` raises on unknown families. No hidden `0.8`, `0.7`, `1.0`, `0.65`, `1.3` fallbacks.

### P2: Contract comments corrected
Module invariant updated: "Every active activation-sphere match contributes" (not "strongest"). Audit script has GRACE header, module contract, module map, and function contracts.

## Verification

| Gate | Result |
|------|--------|
| V2 tests (all) | 18 passed |
| Activation layer tests | 38 passed |
| API full suite | 719 passed, 5 skipped, 1 warning |
| Base score V1=V2 | `test_v2_base_score_matches_v1` ✓ |
| Inactive ignored | `test_inactive_activation_ignored` ✓ |
| Weak aspects | `test_weak_aspects_below_threshold_ignored` ✓ |
| Artifact snake_case | `result["scoring_version"]` ✓ |
| V1 runtime proof | No `ss-scoring-2.0` in today_service.py ✓ |
| Working tree | Tracked artifacts present, not deleted |
| Whitespace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
