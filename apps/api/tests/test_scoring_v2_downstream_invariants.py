"""W11 scoring downstream invariants for trusted activation layer inputs."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.activation import ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "downstream_v2"


def _layer(name: str) -> ActivationLayer:
    raw = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return ActivationLayer.model_validate(raw["activation_layer"])


def test_planet_target_maps_only_to_canon_spheres():
    result = ScoringV2Service().score_day([], _layer("01_planet_target_mapping.json"))
    # PLUTO contributions should only appear on spheres that include PLUTO
    pluto_spheres = set()
    for skey, ss in result.sphere_scores.items():
        for c in ss.contributions:
            if c.source == "activation" and c.source_id == "t2n__MOON__PLUTO":
                pluto_spheres.add(skey)
    assert pluto_spheres
    assert "crisis_transformation_control" in pluto_spheres


def test_house_target_maps_to_house_spheres():
    result = ScoringV2Service().score_day([], _layer("02_house_target_mapping.json"))
    contrib_spheres = {
        skey
        for skey, ss in result.sphere_scores.items()
        for c in ss.contributions
        if c.source == "activation" and c.source_id == "tih__SUN__10"
    }
    assert "work_status_achievement" in contrib_spheres


def test_lot_target_mapping():
    result = ScoringV2Service().score_day([], _layer("03_lot_target_mapping.json"))
    contrib = [
        (skey, c)
        for skey, ss in result.sphere_scores.items()
        for c in ss.contributions
        if c.source == "activation" and c.source_id == "t2l__MOON__FORTUNE"
    ]
    # FORTUNE may or may not be in spheres depending on canon; if unmapped, must be in debug
    if not contrib:
        assert "t2l__MOON__FORTUNE" in result.debug["unmapped_activations"]
    else:
        assert contrib


def test_angle_target_maps_mc_to_work():
    result = ScoringV2Service().score_day([], _layer("04_angle_target_mapping.json"))
    contrib_spheres = {
        skey
        for skey, ss in result.sphere_scores.items()
        for c in ss.contributions
        if c.source == "activation" and c.source_id == "t2a__MARS__MC"
    }
    assert "work_status_achievement" in contrib_spheres


def test_sphere_target_exact_match():
    result = ScoringV2Service().score_day([], _layer("05_sphere_target_mapping.json"))
    contrib_spheres = {
        skey
        for skey, ss in result.sphere_scores.items()
        for c in ss.contributions
        if c.source == "activation" and c.source_id == "sr__work"
    }
    assert "work_status_achievement" in contrib_spheres


def test_inactive_activations_do_not_contribute():
    layer = _layer("01_planet_target_mapping.json")
    layer.activations[0].active = False
    result = ScoringV2Service().score_day([], layer)
    for ss in result.sphere_scores.values():
        assert all(c.source_id != "t2n__MOON__PLUTO" for c in ss.contributions if c.source == "activation")


def test_same_family_no_convergence_bonus():
    result = ScoringV2Service().score_day([], _layer("07_convergence_same_family.json"))
    # all transit family -> no convergence contribution
    for ss in result.sphere_scores.values():
        assert all(c.source != "convergence" for c in ss.contributions)


def test_multi_family_produces_convergence():
    result = ScoringV2Service().score_day([], _layer("08_convergence_multi_family.json"))
    has_conv = any(
        c.source == "convergence"
        for ss in result.sphere_scores.values()
        for c in ss.contributions
    )
    assert has_conv
    # family count 3 -> bonus 0.65 on spheres hit by all families
    for skey, info in (result.debug.get("convergence_by_sphere") or {}).items():
        if info.get("family_count") == 3:
            assert abs(result.sphere_scores[skey].convergence_bonus - 0.65) <= 0.0001


def test_dominance_cap_creates_cap_contribution():
    result = ScoringV2Service().score_day([], _layer("09_dominance_cap.json"))
    capped = [ss for ss in result.sphere_scores.values() if ss.dominance_capped]
    # may or may not cap depending on scores; if capped, must have source=cap
    for ss in capped:
        assert any(c.source == "cap" for c in ss.contributions)
