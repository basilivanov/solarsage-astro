# Agent Report — Wave W4 Scoring V2

## Summary

Implemented `ScoringV2Service` as a pure, separately callable V2 scoring service. Base scores from V1 formula, activation contributions, convergence bonus by unique technique families, anti-dominance cap, and transparent day status breakdown. Runtime `/day` remains V1.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/scoring_v2_service.py` | **New** — Full V2 scoring service |
| `grace/canon/scoring_v2.v1.yml` | Extended with convergence_curve, target_weight_defaults, angle_sphere_map, activation_polarity, dominance_cap |
| `apps/api/tests/test_scoring_v2_convergence.py` | **New** — Convergence + dominance test |
| `apps/api/tests/test_scoring_v2_antidominance.py` | **New** — Anti-dominance cap test |
| `apps/api/tests/test_scoring_v2_thresholds.py` | **New** — Day status threshold tests |
| `apps/api/tests/test_scoring_v2_family_dedup.py` | **New** — Family dedup tests |
| `apps/api/tests/test_scoring_v2_breakdown_contract.py` | **New** — Breakdown contract tests |
| `apps/api/tests/test_basil_2026_07_08_v2_golden.py` | **New** — Basil golden audit test |
| `scripts/audit_scoring_v2.py` | **New** — Audit script for V2 results + V1/V2 diff |
| `artifacts/audit/2026-07-08/22_scoring_v2_result.json` | **New** — V2 result for Basil 2026-07-08 |
| `artifacts/audit/2026-07-08/23_scoring_v2_diff.json` | **New** — V1/V2 diff for Basil |

## Service Interface

```
ScoringV2Service.score_day(
    day_signals: list[AstroSignal],
    activation_layer: ActivationLayer | dict | None = None,
) -> ScoringV2Result
```

## Algorithm

1. **Base score**: V1 sphere formula (without V1 convergence/cap), reused from ScoringService
2. **Activation contribution**: Map each activation to spheres by target type (planet/house/lot/angle/sphere) using canon weights and polarity modifiers
3. **Convergence bonus**: Count unique technique families per sphere, lookup in convergence_curve (0→0, 2→0.40, 3→0.65, 4→0.80, 5→0.90)
4. **Anti-dominance cap**: If raw_score > 65% of sum_all_positive_scores, cap at 65%
5. **Day status**: Aspect-based + activation-based support/tension scores with transparent breakdown

## Canon Keys

| Section | Keys |
|---------|------|
| status_thresholds | positive_ratio: 1.3, positive_min_score: 1.0, negative_ratio: 1.3, negative_min_score: 1.0 |
| convergence_curve | 0:0, 1:0, 2:0.40, 3:0.65, 4:0.80, 5:0.90 |
| target_weight_defaults | house:0.8, lot:0.8, angle:0.7, sphere:1.0 |
| activation_polarity | sphere_amount_modifier, status_support_modifier, status_tension_modifier |
| dominance_cap | enabled:true, threshold:0.65 |
| angle_sphere_map | ASC→body_energy_health, DSC→relationships_partnership, MC→work_status_achievement, IC→home_family_roots |

## Family Dedup

| Techniques | Family | Counts as |
|-----------|--------|-----------|
| transit_to_natal, transit_to_angle, ... | transit | 1 |
| annual_profection, monthly_profection | profection | 1 |
| firdar_major, firdar_minor | firdar | 1 |
| solar_return, lunar_return | return | 1 |
| solar_arc, secondary_progression | progression | 1 |
| eclipse_window | eclipse | 1 |

## Test Results

| Test File | Count |
|-----------|-------|
| test_scoring_v2_contracts | 2 |
| test_scoring_v2_convergence | 1 |
| test_scoring_v2_antidominance | 1 |
| test_scoring_v2_thresholds | 4 |
| test_scoring_v2_family_dedup | 2 |
| test_scoring_v2_breakdown_contract | 2 |
| test_basil_2026_07_08_v2_golden | 1 |
| **Total V2** | **15 passed** |
| Activation layer tests | 38 passed |
| API full suite | 716 passed, 5 skipped |

## Audit Artifacts

| Artifact | Path |
|----------|------|
| V2 result | `22_scoring_v2_result.json` |
| V1/V2 diff | `23_scoring_v2_diff.json` |

The V2 result for Basil 2026-07-08 has 9 sphere scores, multiple with activation_score > 0 and convergence_bonus > 0. V1 status: supportive, V2 status: steady (activation layer adds tension).

## V1 Runtime Proof

```
rg -n 'ss-scoring-2.0' today_service.py final_today_payload.json
→ No matches (expected)
```

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
