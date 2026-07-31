# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_CANON — strict frozen W1 canon tests.
# ROLE: Proves production canon loading and fail-closed pure policy helpers.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-CANON
# purpose: Validate the frozen Today Convergence and aspect canon without importing reference analysis code.
# owns:
#   - apps/api/tests/test_today_convergence_canon.py
# inputs: repository canon YAML and malformed temporary copies.
# outputs: pytest assertions for loader, mapping, thresholds, and eligibility policy.
# dependencies: app.services.today_convergence_canon, PyYAML.
# side_effects: reads canon and writes only pytest temporary directories.
# emitted_logs: none.
# invariants: frozen values come from YAML; unknown normative values fail closed.
# failure_policy: pytest failure on canon drift or fallback behavior.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-CANON

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-CANON
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - CANON_LOADER_TESTS: strict source and malformed-copy validation.
#   - POLICY_HELPERS: mapping, thresholds, source, rare, and hero policy.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-CANON

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from app.services.today_convergence_canon import (
    TodayConvergenceCanonError,
    event_class_significance,
    hero_confirmation_policy,
    is_fast_source,
    is_rare_source,
    load_today_convergence_canon,
    map_factor_to_product_spheres,
    source_max_orb,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = REPO_ROOT / "grace" / "canon"


def copied_canons(tmp_path: Path) -> Path:
    target = tmp_path / "canon"
    target.mkdir()
    shutil.copy(CANON_DIR / "today_convergence.v1.yml", target / "today_convergence.v1.yml")
    shutil.copy(CANON_DIR / "aspect_rules.v1.yml", target / "aspect_rules.v1.yml")
    return target


def test_repository_canon_loads_strictly_from_both_yaml_sources() -> None:
    canon = load_today_convergence_canon()

    assert canon.schema_version == "today_convergence.v1"
    assert canon.status == "frozen_w1"
    assert canon.formula_version == "today-convergence-2"
    assert canon.canonical_spheres == (
        "work", "money", "documents", "relationships", "sport", "communication",
        "health", "decisions", "travel", "creativity", "study", "shopping",
    )
    assert canon.aspect_weight_min == 0.55
    assert canon.orb_ratio_max == 0.5
    assert source_max_orb(canon, "Jupiter") == 7.0
    assert canon.rare_transit_sources == frozenset({"JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"})


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda data, aspect: data["status"].__class__ and data.update(status="draft"), "status"),
        (lambda data, aspect: data.update(formula_version="other"), "formula_version"),
        (lambda data, aspect: data["sphere_projection"].update(canonical_order=["work", "work"]), "canonical_order"),
        (lambda data, aspect: data["sphere_projection"]["planet_to_product"].update(UNKNOWN=["not_a_sphere"]), "sphere"),
        (lambda data, aspect: aspect.update(orb_profile_default={}), "orb_profile"),
        (lambda data, aspect: aspect["orb_profile_default"].update(JUPITER=0), "orb_value"),
        (lambda data, aspect: data["significance"].update(aspect_weight_min=1.1), "aspect_weight_min"),
        (lambda data, aspect: data["significance"].update(orb_ratio_max=1.1), "orb_ratio_max"),
        (lambda data, aspect: aspect["aspect_weights"].update(SEXTILE=1.1), "aspect_weight"),
        (lambda data, aspect: aspect["aspect_threshold"].update(major=1.1), "aspect_threshold"),
        (lambda data, aspect: data["canonical_event"].update(identity="other"), "canonical_event_identity"),
        (lambda data, aspect: data["canonical_event"].update(producer_precedence=["day_signal", "activation"]), "canonical_event_precedence"),
        (lambda data, aspect: data["canonical_event"].update(strip_prefixes=["Transit_"]), "canonical_event_prefixes"),
        (lambda data, aspect: data["canonical_event"].update(daydelta_contract="names"), "canonical_event_daydelta"),
        (lambda data, aspect: data["background"].update(in_groups=True), "background_in_groups"),
        (lambda data, aspect: data["grouping"].update(rule="transitive_star"), "grouping_rule"),
        (lambda data, aspect: data["grouping"].update(link=["shared_target_key"]), "grouping_link"),
        (lambda data, aspect: data["sphere_projection"].update(rule="factor_to_spheres"), "sphere_projection_rule"),
        (lambda data, aspect: data["sphere_projection"].update(primary="first"), "sphere_projection_primary"),
        (lambda data, aspect: data["sphere_projection"].update(secondary_max=2), "sphere_projection_secondary"),
        (lambda data, aspect: data["sphere_projection"].update(fail_unmapped=False), "sphere_projection_unmapped"),
        (lambda data, aspect: data["independence"]["driver_key"].update(transit="technique_family"), "driver_transit"),
        (lambda data, aspect: data["independence"]["driver_key"].update(timelord="source_planet"), "driver_timelord"),
        (lambda data, aspect: aspect["orb_profile_default"].pop("JUPITER"), "rare_transit_sources"),
        (lambda data, aspect: data["eligibility"]["fast"].update(rare_anchor=True), "fast_policy_truth_table"),
        (lambda data, aspect: data["eligibility"]["slow"].update(hero_confirmation=False), "slow_policy_truth_table"),
    ],
)
def test_malformed_canon_copy_fails_closed(tmp_path: Path, mutation, reason: str) -> None:
    target = copied_canons(tmp_path)
    today_path = target / "today_convergence.v1.yml"
    aspect_path = target / "aspect_rules.v1.yml"
    today = yaml.safe_load(today_path.read_text(encoding="utf-8"))
    aspect = yaml.safe_load(aspect_path.read_text(encoding="utf-8"))
    mutation(today, aspect)
    today_path.write_text(yaml.safe_dump(today), encoding="utf-8")
    aspect_path.write_text(yaml.safe_dump(aspect), encoding="utf-8")

    with pytest.raises(TodayConvergenceCanonError, match=reason):
        load_today_convergence_canon(target)


def test_missing_normative_file_fails_closed(tmp_path: Path) -> None:
    target = copied_canons(tmp_path)
    (target / "aspect_rules.v1.yml").unlink()
    with pytest.raises(TodayConvergenceCanonError, match="aspect_rules"):
        load_today_convergence_canon(target)


def test_mapping_and_threshold_helpers_are_canon_driven_and_fail_closed() -> None:
    canon = load_today_convergence_canon()

    assert map_factor_to_product_spheres(canon, technical_spheres=["thinking_speech_learning"]) == (
        "documents", "communication", "study"
    )
    assert map_factor_to_product_spheres(canon, source_key="Transit_Jupiter") == ("work", "money")
    assert map_factor_to_product_spheres(canon, source_key="UNKNOWN_FACTOR") == ()
    assert "work" not in map_factor_to_product_spheres(canon, technical_spheres=["unknown_factor"])
    assert event_class_significance(canon, "timelord_period_change") is True
    assert event_class_significance(canon, "house_ingress") is False
    assert event_class_significance(canon, "unknown_class") is None
    assert source_max_orb(canon, "CERES") is None


def test_structural_lunar_event_gap_is_explicitly_fail_closed() -> None:
    canon = load_today_convergence_canon()

    # It is listed in rare_anchor_eligible, but absent from significance.event_class.
    assert event_class_significance(canon, "structural_lunar_event") is None
    assert is_rare_source(canon, "MOON", event_class="structural_lunar_event") is False


def test_fast_rare_and_hero_policies_follow_frozen_truth_table() -> None:
    canon = load_today_convergence_canon()

    assert is_fast_source(canon, "MOON") is True
    assert is_fast_source(canon, "JUPITER") is False
    assert is_rare_source(canon, "JUPITER", technique_family="transit", aspect_type="SEXTILE") is True
    assert is_rare_source(canon, "MOON", technique_family="transit", aspect_type="SEXTILE") is False
    assert hero_confirmation_policy(canon, "MOON", technique_family="transit") is False
    assert hero_confirmation_policy(canon, "JUPITER", technique_family="transit") is True
    assert hero_confirmation_policy(canon, None, technique_family="firdar") is True
    assert hero_confirmation_policy(canon, "MARS", technique_family="transit") is True
