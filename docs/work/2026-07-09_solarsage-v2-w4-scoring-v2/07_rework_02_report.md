# Rework 02 Report — Wave W4 Scoring V2

## Summary

Finished W4 acceptance: committed both audit artifacts, removed all hidden runtime fallbacks, added strict canon missing-key tests, removed dead state, left tracked tree clean.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/scoring_v2_service.py` | Removed hidden fallbacks for 5 canon sections; removed dead `_ACTIVE_ACTIVATIONS`; strict `technique_families` lookup |
| `apps/api/tests/test_scoring_v2_breakdown_contract.py` | Added 4 strict canon missing-key tests |
| `artifacts/audit/2026-07-08/23_scoring_v2_diff.json` | Regenerated and committed |

## Fixes

### P1: Both artifacts committed
`22_scoring_v2_result.json` and `23_scoring_v2_diff.json` both committed. Working tree has no tracked modifications after this commit.

### P2: Hidden fallbacks removed
All remaining required canon value lookups now raise `KeyError` instead of using silent defaults:

- `convergence_curve[capped_n]` — raises if entry missing
- `support_mod[pol]` / `tension_mod[pol]` — raises if polarity modifier missing
- `polarity_mod[pol]` — raises if sphere_amount_modifier missing
- `dominance_cap["enabled"]` — raises if key missing
- `technique_families` — uses `_required_mapping` instead of `rules.get(..., {})`

`rg` proof: no match for `_ACTIVE_ACTIVATIONS` or any `.get(0.0/1.0/0.65/1.3/0.8/0.7/True)` fallback pattern.

### P2: Dead state removed
`_ACTIVE_ACTIVATIONS: list[ActivationEvidence] | None = None` removed.

## Verification

| Gate | Result |
|------|--------|
| V2 tests | 22 passed |
| API full suite | 723 passed, 5 skipped, 1 warning |
| Artifact snake_case | `scoringVersion` absent, `scoring_version` present |
| Strict canon missing-key | 4 tests: sphere_amount, status_support, status_tension, convergence_curve |
| `rg` fallback patterns | No matches |
| V1 runtime proof | No `ss-scoring-2.0` in today_service.py |
| Working tree | Clean (except pre-existing untracked `.grace/`, `grace.db`, `skills/`) |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
