# ############################################################################
# AI_HEADER: MODULE_TEST_SCORING_V2_DOWNSTREAM_INVARIANTS
# ROLE: W11 exact mapping/amount/convergence/cap invariants for trusted activations
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SCORING-V2-DOWNSTREAM-INVARIANTS
# purpose: Exact canon mapping and scoring invariants for synthetic activation fixtures.
# owns:
#   - apps/api/tests/test_scoring_v2_downstream_invariants.py
# inputs: fixtures/downstream_v2/*
# outputs: pytest assertions
# dependencies: ScoringV2Service, audit_downstream_v2 helpers
# side_effects: none
# emitted_logs: none
# invariants: exact sphere sets and amounts from fixture expected contracts
# failure_policy: pytest fail
# END_MODULE_CONTRACT: M-TEST-SCORING-V2-DOWNSTREAM-INVARIANTS

# START_MODULE_MAP: M-TEST-SCORING-V2-DOWNSTREAM-INVARIANTS
# public_entrypoints: test_* functions
# END_MODULE_MAP: M-TEST-SCORING-V2-DOWNSTREAM-INVARIANTS

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas.activation import ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service
from scripts import audit_downstream_v2 as audit


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "downstream_v2"


def _load(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _layer(name: str) -> ActivationLayer:
    return ActivationLayer.model_validate(_load(name)["activation_layer"])


def _assert_exact_mapping_and_amounts(name: str):
    data = _load(name)
    expected = data["expected"]
    layer = ActivationLayer.model_validate(data["activation_layer"])
    result = ScoringV2Service().score_day([], layer)
    spheres, scoring_v2, activation_rules, _ = audit.load_canons()

    # exact mapped spheres
    for act in layer.activations:
        if act.active is False:
            continue
        maps = audit.map_activation_to_spheres_for_audit(audit.activation_as_dict(act), spheres, scoring_v2)
        got = sorted(m["sphere"] for m in maps)
        assert got == sorted(expected["mapped_spheres"].get(act.id, [])), act.id

    # exact contribution amounts present
    actual = {(c.source_id, skey): c.amount for skey, ss in result.sphere_scores.items() for c in ss.contributions if c.source == "activation"}
    for c in expected["contributions"]:
        key = (c["activation_id"], c["sphere"])
        assert key in actual
        assert abs(float(actual[key]) - float(c["amount"])) <= 0.0001


def test_planet_exact_mapping_and_amounts():
    _assert_exact_mapping_and_amounts("01_planet_target_mapping.json")


def test_house_exact_mapping_and_amounts():
    _assert_exact_mapping_and_amounts("02_house_target_mapping.json")


def test_lot_exact_mapping_and_amounts():
    _assert_exact_mapping_and_amounts("03_lot_target_mapping.json")


def test_angle_exact_mapping_and_amounts():
    _assert_exact_mapping_and_amounts("04_angle_target_mapping.json")


def test_sphere_exact_mapping_and_amounts():
    _assert_exact_mapping_and_amounts("05_sphere_target_mapping.json")


def test_inactive_skip():
    layer = _layer("01_planet_target_mapping.json")
    layer.activations[0].active = False
    result = ScoringV2Service().score_day([], layer)
    for ss in result.sphere_scores.values():
        assert all(not (c.source == "activation" and c.source_id == "t2n__MOON__PLUTO") for c in ss.contributions)


def test_same_family_dedup_no_convergence():
    data = _load("07_convergence_same_family.json")
    result = ScoringV2Service().score_day([], ActivationLayer.model_validate(data["activation_layer"]))
    for skey, exp in data["expected"]["convergence"].items():
        if exp["family_count"] == 1:
            assert result.sphere_scores[skey].convergence_bonus == 0.0
    assert all(c.source != "convergence" for ss in result.sphere_scores.values() for c in ss.contributions)


def test_multi_family_convergence_exact():
    data = _load("08_convergence_multi_family.json")
    result = ScoringV2Service().score_day([], ActivationLayer.model_validate(data["activation_layer"]))
    found = False
    for skey, exp in data["expected"]["convergence"].items():
        if exp["family_count"] >= 3:
            found = True
            assert abs(result.sphere_scores[skey].convergence_bonus - exp["bonus"]) <= 0.0001
            dbg = result.debug["convergence_by_sphere"][skey]
            assert set(dbg["families"]) == set(exp["families"])
    assert found


def test_dominance_cap_exact_trace():
    data = _load("09_dominance_cap.json")
    result = ScoringV2Service().score_day([], ActivationLayer.model_validate(data["activation_layer"]))
    exp_cap = data["expected"]["dominance_cap"]
    assert exp_cap, "fixture must deterministically cap"
    for skey, exp in exp_cap.items():
        ss = result.sphere_scores[skey]
        assert ss.dominance_capped is True
        assert abs(ss.raw_score - exp["raw_score"]) <= 0.0001
        assert abs(ss.final_score - exp["final_score"]) <= 0.0001
        cap = next(c for c in ss.contributions if c.source == "cap")
        assert cap.source_id == exp["cap_source_id"]
        assert abs(float(cap.amount) - exp["cap_amount"]) <= 0.0001


def test_status_supportive_and_tense_fixtures():
    for name in ("10_status_supportive_by_activation.json", "11_status_tense_by_activation.json"):
        data = _load(name)
        result = ScoringV2Service().score_day([], ActivationLayer.model_validate(data["activation_layer"]))
        assert result.day_status == data["expected"]["day_status"]
        for k, v in data["expected"]["status_breakdown"].items():
            if k == "rule":
                assert result.status_breakdown[k] == v
            elif v is None:
                assert result.status_breakdown[k] is None
            else:
                assert abs(float(result.status_breakdown[k]) - float(v)) <= 0.0001
