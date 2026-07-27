# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_ENGINE
# ROLE: Comprehensive unit tests covering all 14 norm trap cases for M-DAY-VALENCE.
# DEPENDENCIES: pytest, app.services.day_valence_service, app.services.day_factor_ledger
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-ENGINE
# purpose: Verify DayValenceService against all 14 norm trap cases (§14.1) and norm invariants (§6-7).
# owns:
#   - apps/api/tests/test_day_valence_engine.py
# inputs: synthetic ledger and factor fixtures
# outputs: assertions
# dependencies: app.services.day_valence_service, app.services.day_factor_ledger, app.schemas.day_valence
# side_effects: none
# failure_policy: test failure identifies valence engine regressions
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-ENGINE

# START_MODULE_MAP: M-TEST-DAY-VALENCE-ENGINE
# public_entrypoints:
#   - test_trap_1_production_basil_salience_does_not_create_good
#   - test_trap_2_tense_high_salience_verdict
#   - test_trap_3_balanced_support_tension
#   - test_trap_4_mixed_polarity_50_50_split
#   - test_trap_5_signal_activation_dedup_single_count
#   - test_trap_6_input_permutation_invariance
#   - test_trap_7_fourth_factor_family_decay_zero
#   - test_trap_8_three_families_independent_rank1
#   - test_trap_9_technical_double_map_single_count
#   - test_trap_10_zero_denominator_no_division_by_zero
#   - test_trap_11_boundary_0_75_good_threshold
#   - test_trap_12_boundary_1_30_ratio_threshold
#   - test_trap_13_boundary_1_50_avoid_threshold
#   - test_trap_14_boundary_2_00_avoid_ratio_threshold
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_engine.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-ENGINE

import random
import pytest
from app.schemas.activation import ActivationEvidence
from app.schemas.day_valence import DayValenceFactor, FactorLedger
from app.schemas.normalization import AstroSignal
from app.services.day_factor_ledger import build_factor_ledger
from app.services.day_valence_service import DayValenceService


@pytest.fixture
def service():
    return DayValenceService()


def test_trap_1_production_basil_salience_does_not_create_good(service):
    """Trap 1 (P-BASIL): High salience without valence support does NOT make sphere 'good'."""
    # Factor with high salience score (e.g. 8.5) but neutral polarity
    factor = DayValenceFactor(
        factor_id="act:neutral_high",
        semantic_key="activation:neutral_high",
        source="activation",
        technique="firdar",
        technique_family="firdar",
        polarity="neutral",
        strength=0.90,
        technical_spheres=["work_status_achievement"],
        target_type="natal_planet",
        target_key="SATURN",
    )
    ledger = FactorLedger(factors=[factor])
    assessments, _, _ = service.compute(ledger, sphere_scores_v2={"work_status_achievement": {"final_score": 8.5}})

    work = assessments["work"]
    assert work.salience_score == 8.5
    assert work.support_score == 0.0
    assert work.tension_score == 0.0
    assert work.verdict == "neutral"
    assert work.verdict_rule == "neutral_low_evidence"


def test_trap_2_tense_high_salience_verdict(service):
    """Trap 2: High salience + high tension -> verdict is 'avoid' or 'caution', never 'good'."""
    factor = DayValenceFactor(
        factor_id="act:tense_high",
        semantic_key="activation:tense_high",
        source="activation",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="tense",
        strength=0.95,
        technical_spheres=["work_status_achievement"],
        target_type="natal_planet",
        target_key="SATURN",
        aspect_type="square",
    )
    ledger = FactorLedger(factors=[factor])
    assessments, _, _ = service.compute(ledger, sphere_scores_v2={"work_status_achievement": {"final_score": 9.0}})

    work = assessments["work"]
    assert work.salience_score == 9.0
    assert work.tension_score > 1.0
    assert work.verdict in ("avoid", "caution")
    assert work.verdict != "good"


def test_trap_3_balanced_support_tension(service):
    """Trap 3: Equal support and tension -> verdict is 'neutral' with rule 'neutral_balanced'."""
    f_supp = DayValenceFactor(
        factor_id="act:supp",
        semantic_key="activation:supp",
        source="activation",
        technique="firdar",
        technique_family="firdar",
        polarity="supportive",
        strength=0.90,
        technical_spheres=["work_status_achievement"],
        target_type="natal_planet",
        target_key="SUN",
    )
    f_tens = DayValenceFactor(
        factor_id="act:tens",
        semantic_key="activation:tens",
        source="activation",
        technique="profection",
        technique_family="profection",
        polarity="tense",
        strength=0.90,
        technical_spheres=["work_status_achievement"],
        target_type="natal_planet",
        target_key="SATURN",
    )
    ledger = FactorLedger(factors=[f_supp, f_tens])
    assessments, _, _ = service.compute(ledger)

    work = assessments["work"]
    assert work.support_score > 0.75
    assert work.tension_score > 0.75
    assert work.verdict == "neutral"
    assert work.verdict_rule == "neutral_balanced"


def test_trap_4_mixed_polarity_50_50_split(service):
    """Trap 4: Mixed polarity splits magnitude 50/50 between support and tension."""
    factor = DayValenceFactor(
        factor_id="act:mixed_1",
        semantic_key="activation:mixed_1",
        source="activation",
        technique="transit_to_natal",
        technique_family="transit",
        polarity="mixed",
        strength=1.00,
        technical_spheres=["work_status_achievement"],
        target_type="natal_planet",
        target_key="SUN",
    )
    ledger = FactorLedger(factors=[factor])
    assessments, _, _ = service.compute(ledger)

    work = assessments["work"]
    # raw_mag = 1.00 * 1.0 (family_ind) * 1.2 (Sun weight) = 1.20
    # support = 0.60, tension = 0.60
    assert work.support_score == 0.60
    assert work.tension_score == 0.60
    assert work.balance == 0.0


def test_trap_5_signal_activation_parity_single_count(service):
    """Trap 5: Signal and Activation matching same physical factor counted once."""
    sig = AstroSignal(type="aspect", planet="Transit_Venus", target_planet="Uranus", aspect_type="sextile", strength=0.80)
    act = {
        "id": "act_1",
        "activation_id": "act_1",
        "active": True,
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "polarity": "supportive",
        "strength": 0.90,
        "planet": "Venus",
        "target_type": "planet",
        "target_key": "URANUS",
        "aspect_type": "sextile",
        "technical_spheres": ["relationships_partnership"],
    }
    ledger = build_factor_ledger(day_signals=[sig], activations=[act])

    assessments, breakdown, _ = service.compute(ledger)

    rel = assessments["relationships"]
    assert rel.factor_count == 1
    assert ledger.duplicate_count == 1


def test_trap_6_input_permutation_invariance(service):
    """Trap 6: Input permutation does NOT change scores, assessments, or day status."""
    f1 = DayValenceFactor(factor_id="act:1", semantic_key="act:1", source="activation", technique="t1", technique_family="transit", polarity="supportive", strength=0.90, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SUN")
    f2 = DayValenceFactor(factor_id="act:2", semantic_key="act:2", source="activation", technique="t2", technique_family="profection", polarity="tense", strength=0.80, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SATURN")
    f3 = DayValenceFactor(factor_id="act:3", semantic_key="act:3", source="activation", technique="t3", technique_family="firdar", polarity="mixed", strength=0.70, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="JUPITER")

    base_ledger = FactorLedger(factors=[f1, f2, f3])
    base_ass, base_bd, base_st = service.compute(base_ledger)

    for _ in range(5):
        shuffled = [f1, f2, f3]
        random.shuffle(shuffled)
        shuffled_ledger = FactorLedger(factors=shuffled)
        ass, bd, st = service.compute(shuffled_ledger)

        assert st == base_st
        assert bd.support_score == base_bd.support_score
        assert bd.tension_score == base_bd.tension_score
        assert ass["work"].verdict == base_ass["work"].verdict
        assert ass["work"].support_score == base_ass["work"].support_score


def test_trap_7_fourth_factor_family_decay_zero(service):
    """Trap 7: 4th factor in same technique family gets decay multiplier 0.0 for valence."""
    factors = [
        DayValenceFactor(factor_id=f"act:fam_{i}", semantic_key=f"act:fam_{i}", source="activation", technique="transit", technique_family="transit", polarity="supportive", strength=1.00, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SUN")
        for i in range(1, 5)
    ]
    ledger = FactorLedger(factors=factors)
    assessments, _, _ = service.compute(ledger)

    work = assessments["work"]
    # 4 factors, decay multipliers [1.0, 0.5, 0.25, 0.0]
    # effective factor count should be 3
    assert work.factor_count == 4
    assert work.effective_factor_count == 3


def test_trap_8_three_families_independent_rank1(service):
    """Trap 8: Factors from 3 distinct technique families do not decay each other."""
    f1 = DayValenceFactor(factor_id="act:1", semantic_key="act:1", source="activation", technique="transit", technique_family="transit", polarity="supportive", strength=1.00, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SUN")
    f2 = DayValenceFactor(factor_id="act:2", semantic_key="act:2", source="activation", technique="profection", technique_family="profection", polarity="supportive", strength=1.00, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SUN")
    f3 = DayValenceFactor(factor_id="act:3", semantic_key="act:3", source="activation", technique="firdar", technique_family="firdar", polarity="supportive", strength=1.00, technical_spheres=["work_status_achievement"], target_type="natal_planet", target_key="SUN")

    ledger = FactorLedger(factors=[f1, f2, f3])
    assessments, _, _ = service.compute(ledger)

    work = assessments["work"]
    # All 3 factors get rank 1 in their own family -> multiplier 1.0 each!
    assert work.effective_factor_count == 3
    assert work.independent_family_count == 3


def test_trap_9_technical_double_map_single_count(service):
    """Trap 9: Factor mapping to product sphere through 2 technical spheres counted once with max magnitude."""
    # Factor touches work_status_achievement and crisis_transformation_control, both map to 'decisions'
    factor = DayValenceFactor(
        factor_id="act:double_map",
        semantic_key="act:double_map",
        source="activation",
        technique="transit",
        technique_family="transit",
        polarity="supportive",
        strength=1.00,
        technical_spheres=["work_status_achievement", "crisis_transformation_control"],
        target_type="natal_planet",
        target_key="SUN",
    )
    ledger = FactorLedger(factors=[factor])
    assessments, _, _ = service.compute(ledger)

    decisions = assessments["decisions"]
    assert decisions.factor_count == 1


def test_trap_10_zero_denominator_no_division_by_zero(service):
    """Trap 10: support=0 and tension=0 -> balance=0.0 and ratio=None without zero division exception."""
    ledger = FactorLedger(factors=[])
    assessments, breakdown, day_status = service.compute(ledger)

    assert breakdown.support_score == 0.0
    assert breakdown.tension_score == 0.0
    assert breakdown.ratio is None
    assert day_status == "steady"

    for pkey, ass in assessments.items():
        assert ass.balance == 0.0
        assert ass.verdict == "neutral"


def test_trap_11_boundary_0_75_good_threshold(service):
    """Trap 11: support=0.74 -> neutral_low_evidence; support=0.75 -> good."""
    # Factor giving support ~ 0.74
    f_low = DayValenceFactor(
        factor_id="act:low", semantic_key="act:low", source="activation",
        technique="transit", technique_family="transit", polarity="supportive",
        strength=0.74 / 1.20, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="SUN"
    )
    ass_low, _, _ = service.compute(FactorLedger(factors=[f_low]))
    assert ass_low["relationships"].verdict == "neutral"
    assert ass_low["relationships"].verdict_rule == "neutral_low_evidence"

    # Factor giving support >= 0.75
    f_high = DayValenceFactor(
        factor_id="act:high", semantic_key="act:high", source="activation",
        technique="transit", technique_family="transit", polarity="supportive",
        strength=0.80 / 1.20, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="SUN"
    )
    ass_high, _, _ = service.compute(FactorLedger(factors=[f_high]))
    assert ass_high["relationships"].verdict == "good"
    assert ass_high["relationships"].verdict_rule == "good_support_1_3x"


def test_trap_12_boundary_1_30_ratio_threshold(service):
    """Trap 12: support > tension * 1.30 threshold boundary test."""
    f_supp = DayValenceFactor(
        factor_id="act:supp", semantic_key="act:supp", source="activation",
        technique="transit", technique_family="transit", polarity="supportive",
        strength=1.00, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="SUN"  # support = 1.20
    )
    # tension = 1.00 -> ratio = 1.20 / 1.00 = 1.20 <= 1.30 -> neutral_balanced
    f_tens = DayValenceFactor(
        factor_id="act:tens", semantic_key="act:tens", source="activation",
        technique="profection", technique_family="profection", polarity="tense",
        strength=1.00, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="MOON"  # tension = 1.00
    )

    ass, _, _ = service.compute(FactorLedger(factors=[f_supp, f_tens]))
    assert ass["relationships"].verdict == "neutral"
    assert ass["relationships"].verdict_rule == "neutral_balanced"


def test_trap_13_boundary_1_50_avoid_threshold(service):
    """Trap 13: tension >= 1.50 threshold for avoid verdict."""
    f_tens = DayValenceFactor(
        factor_id="act:tens", semantic_key="act:tens", source="activation",
        technique="transit", technique_family="transit", polarity="tense",
        strength=1.50 / 1.20, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="SUN"  # tension = 1.50
    )
    ass, _, _ = service.compute(FactorLedger(factors=[f_tens]))
    assert ass["relationships"].verdict == "avoid"
    assert ass["relationships"].verdict_rule == "avoid_tension_2x"


def test_trap_14_boundary_2_00_avoid_ratio_threshold(service):
    """Trap 14: tension >= support * 2.00 threshold for avoid vs caution."""
    # tension = 1.60, support = 0.90 -> tension (1.60) < support * 2.00 (1.80) -> caution!
    f_tens = DayValenceFactor(
        factor_id="act:tens", semantic_key="act:tens", source="activation",
        technique="transit", technique_family="transit", polarity="tense",
        strength=1.60 / 1.20, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="SUN"  # tension = 1.60
    )
    f_supp = DayValenceFactor(
        factor_id="act:supp", semantic_key="act:supp", source="activation",
        technique="profection", technique_family="profection", polarity="supportive",
        strength=0.90 / 1.00, technical_spheres=["relationships_partnership"],
        target_type="natal_planet", target_key="MOON"  # support = 0.90
    )
    ass, _, _ = service.compute(FactorLedger(factors=[f_tens, f_supp]))
    assert ass["relationships"].verdict == "caution"
    assert ass["relationships"].verdict_rule == "caution_tension_1_3x"
