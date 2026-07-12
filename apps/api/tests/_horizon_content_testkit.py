# ############################################################################
# AI_HEADER: HORIZON_CONTENT_TESTKIT — deterministic synthetic B2B1 fact and tone inputs.
# ROLE: Builds selected stories, finite natal contexts, verdict maps, and fact packs without user or runtime dependencies.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CONTENT-TESTKIT
# purpose: Provide reusable synthetic builders for B2B1 content canon, fact-pack, and tone tests.
# owns:
#   - apps/api/tests/_horizon_content_testkit.py
# inputs: Stable story ids and explicit synthetic natal/verdict overrides.
# outputs: Typed selection, scoring, natal, verdict, and fact-pack test inputs.
# dependencies: B2A testkit/services, natal/scoring schemas, B2B fact service.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No database, network, clock, profile, real user, or production fixture data is used.
#   - Builders preserve deterministic selection and input ordering.
# failure_policy: raises Pydantic/service validation errors for invalid synthetic inputs.
# END_MODULE_CONTRACT: M-HORIZON-CONTENT-TESTKIT

# START_MODULE_MAP: M-HORIZON-CONTENT-TESTKIT
# public_entrypoints:
#   - build_selected_story
#   - build_natal_context
#   - build_structure_natal
#   - build_communication_natal
#   - build_relationship_natal
#   - build_sphere_verdicts
#   - build_fact_pack
# semantic_blocks:
#   - HORIZON_CONTENT_SYNTHETIC_BUILDERS: selected B2A stories and finite natal/verdict inputs.
# owned_tests:
#   - apps/api/tests/test_personal_fact_pack_service.py
#   - apps/api/tests/test_horizon_tone_service.py
# END_MODULE_MAP: M-HORIZON-CONTENT-TESTKIT

# START_BLOCK: HORIZON_CONTENT_SYNTHETIC_BUILDERS
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

import yaml

from app.schemas.activation import ActivationLayer
from app.schemas.horizon_selection import SelectedHorizonTriple
from app.schemas.natal import NatalChartAspect, NatalChartPlanet, NatalContextData
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.today_horizons import TodayV2ProductSphereKey
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.personal_fact_pack_service import PersonalFactPackService
from app.services.canon_service import CANON_DIR

from ._horizon_selection_testkit import build_layer, build_scoring, build_story


def build_selected_story(theme: str) -> tuple[SelectedHorizonTriple, ActivationLayer, ScoringV2Result]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_selected_story
    # purpose: Build one accepted B2A golden selection plus its exact activation/scoring inputs.
    # inputs: theme - stable synthetic B2A golden story id.
    # returns: selected triple, activation layer, and scoring result.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises AssertionError if the golden no longer selects a triple.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_selected_story
    activations, mapping, _, _ = build_story(theme)
    layer = build_layer(activations)
    scoring = build_scoring(activations, mapping)
    result = HorizonSelectionService().select(activation_layer=layer, scoring_result=scoring)
    assert result.selection is not None
    return result.selection, layer, scoring


def build_natal_context(
    *,
    planets: list[NatalChartPlanet] | None = None,
    aspects: list[NatalChartAspect] | None = None,
) -> NatalContextData:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_natal_context
    # purpose: Build a synthetic finite natal context containing only explicit chart planets/aspects.
    # inputs: planets/aspects - optional typed synthetic chart values.
    # returns: NatalContextData without profile or real-user data.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises Pydantic ValidationError for invalid synthetic models.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_natal_context
    return NatalContextData(
        house_system="WHOLE_SIGN",
        planets=planets or [],
        aspects=aspects or [],
    )


def _planet(name: str, sign: str, house: int) -> NatalChartPlanet:
    return NatalChartPlanet(
        name=name,
        sign=sign,
        degree=0.0,
        house=house,
        retrograde=False,
        longitude=0.0,
    )


def _aspect(planet_a: str, planet_b: str, aspect_type: str, orb: float) -> NatalChartAspect:
    return NatalChartAspect(
        planet_a=planet_a,
        planet_b=planet_b,
        aspect_type=aspect_type,
        orb=orb,
    )


def build_structure_natal() -> NatalContextData:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_structure_natal
    # purpose: Build the reviewed structure golden natal configuration.
    # inputs: none.
    # returns: Natal context with Saturn/Aquarius/house-10 and Saturn-Pluto square inputs.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_structure_natal
    return build_natal_context(
        planets=[_planet("SATURN", "AQUARIUS", 10), _planet("PLUTO", "SCORPIO", 8)],
        aspects=[_aspect("SATURN", "PLUTO", "SQUARE", 1.0)],
    )


def build_communication_natal() -> NatalContextData:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_communication_natal
    # purpose: Build the reviewed communication golden natal configuration.
    # inputs: none.
    # returns: Natal context with Mercury-Saturn trine input.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_communication_natal
    return build_natal_context(
        planets=[_planet("MERCURY", "GEMINI", 3), _planet("SATURN", "ARIES", 2)],
        aspects=[_aspect("MERCURY", "SATURN", "TRINE", 1.5)],
    )


def build_relationship_natal() -> NatalContextData:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_relationship_natal
    # purpose: Build the reviewed relationship golden natal configuration.
    # inputs: none.
    # returns: Natal context with Mercury-Venus sextile and Venus-Saturn opposition inputs.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_relationship_natal
    return build_natal_context(
        planets=[_planet("MERCURY", "GEMINI", 3), _planet("VENUS", "LEO", 5), _planet("SATURN", "AQUARIUS", 11)],
        aspects=[_aspect("MERCURY", "VENUS", "SEXTILE", 1.0), _aspect("VENUS", "SATURN", "OPPOSITION", 2.0)],
    )


def build_sphere_verdicts(
    **overrides: HorizonSphereVerdict,
) -> dict[TodayV2ProductSphereKey, HorizonSphereVerdict]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_sphere_verdicts
    # purpose: Build a small explicit product-sphere verdict map for tone tests.
    # inputs: overrides - sphere key to verdict replacements.
    # returns: deterministic verdict mapping.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_sphere_verdicts
    verdicts: dict[TodayV2ProductSphereKey, HorizonSphereVerdict] = {
        "work": "good",
        "decisions": "neutral",
        "money": "caution",
    }
    verdicts.update(overrides)
    return verdicts


def build_fact_pack(theme: str, natal_context: NatalContextData):
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_fact_pack
    # purpose: Build a complete deterministic B2B1 fact pack for one synthetic selected story.
    # inputs: theme - stable golden id; natal_context - typed synthetic chart context.
    # returns: PersonalFactPack.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: propagates fact-pack integrity validation failures.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.build_fact_pack
    selection, layer, scoring = build_selected_story(theme)
    return PersonalFactPackService().build(
        selection=selection,
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal_context,
    )


def copy_content_canon_dir(tmp_path: Path) -> Path:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.copy_content_canon_dir
    # purpose: Copy the three B2B1 content canons for one isolated YAML mutation test.
    # inputs: tmp_path - pytest temporary root.
    # returns: directory containing independent mutable canon files.
    # side_effects: temporary filesystem writes only.
    # emitted_logs: none.
    # error_behavior: propagates filesystem failures.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.copy_content_canon_dir
    target = tmp_path / "canon"
    target.mkdir(parents=True)
    for name in ("horizon_language.ru.v1.yml", "horizon_actions.ru.v1.yml", "personal_patterns.ru.v1.yml"):
        shutil.copy2(CANON_DIR / name, target / name)
    return target


def read_content_canon_yaml(directory: Path, name: str) -> dict[str, object]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.read_content_canon_yaml
    # purpose: Return one mutable parsed temporary canon mapping.
    # inputs: directory - copied canon directory; name - canon file name.
    # returns: deep mutable YAML mapping.
    # side_effects: temporary filesystem read only.
    # emitted_logs: none.
    # error_behavior: propagates parser failures.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.read_content_canon_yaml
    return deepcopy(yaml.safe_load((directory / name).read_text(encoding="utf-8")))


def write_content_canon_yaml(directory: Path, name: str, data: dict[str, object]) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.write_content_canon_yaml
    # purpose: Persist exactly one temporary YAML mutation with stable key order.
    # inputs: directory - copied canon directory; name - canon file name; data - mutation mapping.
    # returns: none.
    # side_effects: temporary filesystem write only.
    # emitted_logs: none.
    # error_behavior: propagates filesystem failures.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-TESTKIT.write_content_canon_yaml
    (directory / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# END_BLOCK: HORIZON_CONTENT_SYNTHETIC_BUILDERS
