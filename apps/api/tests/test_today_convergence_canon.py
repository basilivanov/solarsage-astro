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
    map_factor_to_theme_keys,
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
    shutil.copy(CANON_DIR / "today_convergence_themes.v1.yml", target / "today_convergence_themes.v1.yml")
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
    assert canon.theme_schema_version == "today_convergence_themes.v1"
    assert canon.theme_status == "frozen_w1"
    assert canon.theme_formula_version == "today-convergence-2"
    assert canon.theme_canonical_order == (
        "communication_learning_documents",
        "structure_boundaries_control",
        "relationships_values_closeness",
        "resources_security",
        "energy_body_pacing",
        "home_belonging",
        "inner_clarity_recovery",
        "direction_growth_meaning",
        "creativity_visibility",
        "change_innovation",
    )
    assert canon.tone_policy.status == "frozen_w1"
    assert canon.tone_policy.version == "tone-candidate-0.1"
    assert canon.tone_policy.layers == ("unit_polarity", "group_polarity", "day_tone")
    assert canon.tone_policy.unit_polarities == ("supportive", "tense", "mixed", "steady")
    assert canon.tone_policy.neutral_maps_to == "steady"
    assert dict(canon.tone_policy.role_weights) == {
        "anchor_today": 1.0,
        "supporting_context": 0.5,
        "background": 0.0,
        "mixed_split": 0.5,
    }
    assert canon.tone_policy.independence == "distinct_driver"
    assert canon.tone_policy.min_side_weight == 0.25
    assert canon.tone_policy.mixed_margin == 0.25
    assert canon.tone_policy.fresh_predicate == (
        "temporal_role == anchor_today",
        "exact_at local_date == target_date",
    )
    assert canon.tone_policy.ongoing_roles_are_context == ("supporting", "background")
    assert canon.tone_policy.fast_sources_detail_only == frozenset({"MOON", "MERCURY", "VENUS"})
    assert canon.tone_policy.high_confidence_strength == 0.75
    assert canon.tone_policy.min_independent_tense_units == 2
    assert canon.tone_policy.min_independent_supportive_units == 2
    assert canon.tone_policy.mixed_requires_fresh_support_and_tense is True
    assert canon.tone_policy.audit_fields == (
        "unit_polarity_counts",
        "group_polarity_counts",
        "day_tone",
        "tone_scores",
        "tone_trigger_keys",
        "legacy_any_selected_tense",
    )
    with pytest.raises(TypeError):
        canon.tone_policy.role_weights["anchor_today"] = 0.0  # type: ignore[index]


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
        (lambda data, aspect: data["tone_policy"].update(status="draft"), "tone_policy_status"),
        (lambda data, aspect: data["tone_policy"].update(version="other"), "tone_policy_version"),
        (lambda data, aspect: data["tone_policy"].update(layers=["unit_polarity"]), "tone_policy_layers"),
        (lambda data, aspect: data["tone_policy"].update(unit_polarity=["supportive"]), "tone_policy_unit_polarity"),
        (lambda data, aspect: data["tone_policy"].update(neutral_maps_to="tense"), "tone_policy_neutral_maps_to"),
        (lambda data, aspect: data["tone_policy"]["weights"].update(anchor_today=0.5), "tone_policy_role_weights"),
        (lambda data, aspect: data["tone_policy"]["group_balance"].update(independence="raw_units"), "tone_policy_group_balance"),
        (lambda data, aspect: data["tone_policy"]["group_balance"].update(mixed_margin=0.5), "tone_policy_group_balance"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(fresh_predicate=["date prefix"]), "tone_policy_fresh_predicate"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(ongoing_roles_are_context=["supporting"]), "tone_policy_ongoing_roles"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(fast_sources_detail_only=["MOON"]), "tone_policy_fast_sources"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(high_confidence_strength="0.75"), "tone_policy_high_confidence_strength"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(min_independent_tense_units=1), "tone_policy_tense_threshold"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(min_independent_supportive_units=1), "tone_policy_supportive_threshold"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(mixed_requires_fresh_support_and_tense=False), "tone_policy_mixed_requirement"),
        (lambda data, aspect: data["tone_policy"]["day_tone"].update(values=["supportive", "tense"]), "tone_policy_day_tones"),
        (lambda data, aspect: data["tone_policy"].update(audit_fields=["day_tone"]), "tone_policy_audit_fields"),
        (lambda data, aspect: data["tone_policy"].update(extra_key=True), "tone_policy_keys"),
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


def test_theme_registry_matches_horizon_reference_without_runtime_import() -> None:
    canon = load_today_convergence_canon()
    registry = yaml.safe_load((CANON_DIR / "today_convergence_themes.v1.yml").read_text(encoding="utf-8"))
    reference = yaml.safe_load((CANON_DIR / "horizon_selection.v1.yml").read_text(encoding="utf-8"))

    assert registry["technical_sphere_themes"] == reference["technical_sphere_themes"]
    assert registry["target_planet_themes"] == reference["target_planet_themes"]
    assert {key: list(value) for key, value in canon.technical_sphere_themes.items()} == reference["technical_sphere_themes"]
    assert {key: list(value) for key, value in canon.target_planet_themes.items()} == reference["target_planet_themes"]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda theme: theme.update(schema_version="other"), "theme_schema_version"),
        (lambda theme: theme.update(canonical_order=["communication_learning_documents"]), "theme_reference"),
        (lambda theme: theme["technical_sphere_themes"].update(unknown_theme=["not_in_order"]), "theme_reference"),
        (lambda theme: theme["technical_sphere_themes"].update(work_status_achievement=["not_in_order"]), "theme_reference"),
        (lambda theme: theme["target_planet_themes"].update(Transit_MOON=["energy_body_pacing"]), "theme_target_keys"),
        (lambda theme: theme["target_planet_themes"].update(MOON=["energy_body_pacing", "energy_body_pacing"]), "theme_target_keys"),
    ],
)
def test_malformed_theme_registry_copy_fails_closed(tmp_path: Path, mutation, reason: str) -> None:
    target = copied_canons(tmp_path)
    registry_path = target / "today_convergence_themes.v1.yml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    mutation(registry)
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")

    with pytest.raises(TodayConvergenceCanonError, match=reason):
        load_today_convergence_canon(target)


def test_missing_theme_registry_fails_closed(tmp_path: Path) -> None:
    target = copied_canons(tmp_path)
    (target / "today_convergence_themes.v1.yml").unlink()
    with pytest.raises(TodayConvergenceCanonError, match="theme_missing"):
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
    assert map_factor_to_theme_keys(canon, technical_spheres=["thinking_speech_learning"]) == (
        "communication_learning_documents",
    )
    assert map_factor_to_theme_keys(
        canon,
        technical_spheres=["relationships_partnership", "money_security_resources"],
        source_key="Transit_VENUS",
        target_key="Natal_MOON",
    ) == (
        "relationships_values_closeness",
        "resources_security",
        "energy_body_pacing",
    )
    assert map_factor_to_theme_keys(canon, technical_spheres=["unknown_factor"]) == ()
    assert map_factor_to_theme_keys(canon, source_key="UNKNOWN", target_key="UNKNOWN") == ()


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
