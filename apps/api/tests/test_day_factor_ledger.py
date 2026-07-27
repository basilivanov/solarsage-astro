# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_FACTOR_LEDGER
# ROLE: Unit and property tests for day factor ledger builder and cross-source deduplication.
# DEPENDENCIES: pytest, app.services.day_factor_ledger, app.schemas.day_valence
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-FACTOR-LEDGER
# purpose: Verify canonical factor identity, signal<->activation parity, cross-source dedup, input order invariance, and fail-closed handling.
# owns:
#   - apps/api/tests/test_day_factor_ledger.py
# inputs: test fixtures
# outputs: assertions
# dependencies: app.services.day_factor_ledger, app.schemas.normalization, app.schemas.activation
# side_effects: none
# failure_policy: fails test on factor ledger miscalculation or non-deterministic ordering
# END_MODULE_CONTRACT: M-TEST-DAY-FACTOR-LEDGER

# START_MODULE_MAP: M-TEST-DAY-FACTOR-LEDGER
# public_entrypoints:
#   - test_signal_activation_parity_transit_to_natal
#   - test_signal_activation_parity_transit_to_angle
#   - test_signal_activation_parity_transit_to_lot
#   - test_signal_activation_parity_transit_planet_in_house
#   - test_duplicate_activation_id_rejected
#   - test_input_permutation_invariance
#   - test_invalid_factor_fail_closed
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_factor_ledger.py
# END_MODULE_MAP: M-TEST-DAY-FACTOR-LEDGER

import random
import pytest
from app.schemas.activation import ActivationEvidence
from app.schemas.normalization import AstroSignal
from app.services.day_factor_ledger import build_factor_ledger


def test_signal_activation_parity_transit_to_natal():
    """Active activation wins over matching AstroSignal for transit_to_natal."""
    sig = AstroSignal(
        type="aspect",
        planet="Transit_Venus",
        target_planet="Uranus",
        aspect_type="sextile",
        strength=0.80,
    )
    act = {
        "id": "act_venus_uranus",
        "activation_id": "act_venus_uranus",
        "active": True,
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "polarity": "supportive",
        "strength": 0.90,
        "planet": "Venus",
        "target_type": "planet",
        "target_key": "URANUS",
        "aspect_type": "sextile",
        "evidence": "Transit Venus sextile natal Uranus",
    }

    ledger = build_factor_ledger(day_signals=[sig], activations=[act])

    assert len(ledger.factors) == 1
    assert ledger.duplicate_count == 1
    assert ledger.factors[0].source == "activation"
    assert ledger.factors[0].factor_id == "act:act_venus_uranus"
    assert ledger.factors[0].semantic_key == "aspect:VENUS:sextile:natal_planet:URANUS"


def test_signal_activation_parity_transit_to_angle():
    """Active activation wins over matching AstroSignal for transit_to_angle."""
    sig = AstroSignal(
        type="aspect",
        planet="Transit_Sun",
        target_planet="ASC",
        aspect_type="conjunction",
        strength=0.75,
    )
    act = {
        "id": "act_sun_asc",
        "activation_id": "act_sun_asc",
        "active": True,
        "technique": "transit_to_angle",
        "technique_family": "transit",
        "polarity": "mixed",
        "strength": 0.85,
        "planet": "Sun",
        "target_type": "angle",
        "target_key": "ASC",
        "aspect_type": "conjunction",
        "evidence": "Transit Sun conjunction natal ASC",
    }

    ledger = build_factor_ledger(day_signals=[sig], activations=[act])

    assert len(ledger.factors) == 1
    assert ledger.duplicate_count == 1
    assert ledger.factors[0].semantic_key == "aspect:SUN:conjunction:angle:ASC"


def test_signal_activation_parity_transit_to_lot():
    """Active activation wins over matching AstroSignal for transit_to_lot."""
    sig = AstroSignal(
        type="aspect",
        planet="Transit_Jupiter",
        target_planet="FORTUNE",
        aspect_type="trine",
        strength=0.70,
    )
    act = {
        "id": "act_jup_fortune",
        "activation_id": "act_jup_fortune",
        "active": True,
        "technique": "transit_to_lot",
        "technique_family": "transit",
        "polarity": "supportive",
        "strength": 0.90,
        "planet": "Jupiter",
        "target_type": "lot",
        "target_key": "FORTUNE",
        "aspect_type": "trine",
        "evidence": "Transit Jupiter trine natal FORTUNE",
    }

    ledger = build_factor_ledger(day_signals=[sig], activations=[act])

    assert len(ledger.factors) == 1
    assert ledger.duplicate_count == 1
    assert ledger.factors[0].semantic_key == "aspect:JUPITER:trine:lot:FORTUNE"


def test_signal_activation_parity_transit_planet_in_house():
    """Active activation wins over matching AstroSignal for transit_planet_in_house."""
    sig = AstroSignal(
        type="planet_in_house",
        planet="Transit_Mars",
        house=10,
        strength=0.65,
    )
    act = {
        "id": "act_mars_10",
        "activation_id": "act_mars_10",
        "active": True,
        "technique": "transit_planet_in_house",
        "technique_family": "transit",
        "polarity": "neutral",
        "strength": 0.70,
        "planet": "Mars",
        "target_type": "house",
        "target_key": "10",
        "house": 10,
        "evidence": "Transit Mars in house 10",
    }

    ledger = build_factor_ledger(day_signals=[sig], activations=[act])

    assert len(ledger.factors) == 1
    assert ledger.duplicate_count == 1
    assert ledger.factors[0].semantic_key == "house:MARS:10"


def test_duplicate_activation_id_rejected():
    """Re-occurrence of an activation_id is excluded as duplicate."""
    act1 = {
        "id": "act_dup",
        "activation_id": "act_dup",
        "active": True,
        "technique": "firdar",
        "technique_family": "firdar",
        "polarity": "supportive",
        "strength": 0.90,
        "target_type": "planet",
        "target_key": "SUN",
    }
    act2 = {
        "id": "act_dup",
        "activation_id": "act_dup",
        "active": True,
        "technique": "firdar",
        "technique_family": "firdar",
        "polarity": "supportive",
        "strength": 0.80,
        "target_type": "planet",
        "target_key": "SUN",
    }

    ledger = build_factor_ledger(activations=[act1, act2])

    assert len(ledger.factors) == 1
    assert ledger.duplicate_count == 1


def test_input_permutation_invariance():
    """Permutation of input lists yields byte-identical factor order."""
    sigs = [
        AstroSignal(type="aspect", planet="Transit_Mars", target_planet="Saturn", aspect_type="square", strength=0.80),
        AstroSignal(type="aspect", planet="Transit_Venus", target_planet="Jupiter", aspect_type="trine", strength=0.90),
        AstroSignal(type="planet_in_house", planet="Transit_Moon", house=4, strength=0.50),
    ]
    acts = [
        {"id": "firdar_1", "activation_id": "firdar_1", "active": True, "technique": "firdar", "technique_family": "firdar", "polarity": "supportive", "strength": 0.95, "target_type": "planet", "target_key": "SUN"},
        {"id": "profection_1", "activation_id": "profection_1", "active": True, "technique": "annual_profection", "technique_family": "profection", "polarity": "mixed", "strength": 0.70, "target_type": "planet", "target_key": "MOON"},
    ]

    base_ledger = build_factor_ledger(day_signals=sigs, activations=acts)

    for i in range(5):
        shuffled_sigs = list(sigs)
        shuffled_acts = list(acts)
        random.shuffle(shuffled_sigs)
        random.shuffle(shuffled_acts)

        shuffled_ledger = build_factor_ledger(day_signals=shuffled_sigs, activations=shuffled_acts)
        assert [f.factor_id for f in shuffled_ledger.factors] == [f.factor_id for f in base_ledger.factors]
        assert shuffled_ledger.duplicate_count == base_ledger.duplicate_count
        assert shuffled_ledger.invalid_count == base_ledger.invalid_count


def test_invalid_factor_fail_closed():
    """Malformed activation lacking activation_id increments invalid_count without raising."""
    bad_act = {"active": True, "technique": "firdar"}  # missing activation_id
    bad_sig = {"type": "aspect", "planet": None}       # missing planet

    ledger = build_factor_ledger(day_signals=[bad_sig], activations=[bad_act])

    assert len(ledger.factors) == 0
    assert ledger.invalid_count == 2
