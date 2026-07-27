# ############################################################################
# AI_HEADER: MODULE_SPHERE_WHY_BUILDER
# ROLE: Pure service module building deterministic human-readable why lines for sphere evidence.
# DEPENDENCIES: app.schemas.today.ConcreteAdviceEvidence, app.services.astro_utils.strip_prefix
# GRACE_ANCHORS: [SPHERE_WHY_BUILDER]
# ############################################################################

# START_MODULE_CONTRACT: M-API-SPHERE-WHY-BUILDER
# purpose: Compute 1-2 deterministic, human-readable background why lines from sphere evidence without astrology jargon or planet names.
# owns:
#   - apps/api/app/services/sphere_why_builder.py
# inputs: evidence (list of ConcreteAdviceEvidence objects or dicts)
# outputs: list[str] (up to 2 human why lines, or [] if no valid evidence)
# dependencies: app.services.astro_utils
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: returns [] on empty or invalid evidence
# END_MODULE_CONTRACT: M-API-SPHERE-WHY-BUILDER

# START_MODULE_MAP: M-API-SPHERE-WHY-BUILDER
# public_entrypoints:
#   - build_sphere_why
# semantic_blocks:
#   - WHY_BUILDER: deterministic human why line calculation from evidence
# owned_tests:
#   - apps/api/tests/test_sphere_why_builder.py
# END_MODULE_MAP: M-API-SPHERE-WHY-BUILDER

from __future__ import annotations

from typing import Any
from app.services.astro_utils import strip_prefix

PLANET_FUNCTIONS: dict[str, dict[str, str]] = {
    # nom — именительный, acc — винительный (для «поддерживают»),
    # inst — творительный (для «сталкиваются/взаимодействуют с»)
    "Sun": {"nom": "самовыражение и цели", "acc": "самовыражение и цели", "inst": "самовыражением и целями"},
    "Moon": {"nom": "эмоции и привычки", "acc": "эмоции и привычки", "inst": "эмоциями и привычками"},
    "Mercury": {"nom": "мысли и разговоры", "acc": "мысли и разговоры", "inst": "мыслями и разговорами"},
    "Venus": {"nom": "чувства и симпатии", "acc": "чувства и симпатии", "inst": "чувствами и симпатиями"},
    "Mars": {"nom": "действия и темп", "acc": "действия и темп", "inst": "действиями и темпом"},
    "Jupiter": {"nom": "возможности и рост", "acc": "возможности и рост", "inst": "возможностями и ростом"},
    "Saturn": {"nom": "правила и сроки", "acc": "правила и сроки", "inst": "правилами и сроками"},
    "Uranus": {"nom": "перемены и свобода", "acc": "перемены и свободу", "inst": "переменами и свободой"},
    "Neptune": {"nom": "мечты и чуткость", "acc": "мечты и чуткость", "inst": "мечтами и чуткостью"},
    "Pluto": {"nom": "глубокие изменения", "acc": "глубокие изменения", "inst": "глубокими изменениями"},
}

SUPPORTIVE_ASPECTS: set[str] = {"conjunction", "sextile", "trine"}
CHALLENGING_ASPECTS: set[str] = {"square", "opposition", "quincunx", "semi_square", "sesquisquare"}


def _get_direction(aspect_type: str | None) -> tuple[str, str]:
    """Return (verb, target_case): supportive uses accusative, others instrumental."""
    if not aspect_type:
        return ("взаимодействуют с", "inst")
    asp = aspect_type.lower()
    if asp in SUPPORTIVE_ASPECTS:
        return ("поддерживают", "acc")
    if asp in CHALLENGING_ASPECTS:
        return ("сталкиваются с", "inst")
    return ("взаимодействуют с", "inst")


def _get_scale(ev_kind: str | None, technique_family: str | None, technique: str | None) -> str:
    family = (technique_family or "").lower()
    tech = (technique or "").lower()

    if family in ("firdar", "profection") or tech in ("firdar", "profection"):
        return "долгий фон"
    if family in ("return", "progression") or tech in ("return", "progression"):
        return "текущий период"
    if ev_kind == "aspect" or family == "transit" or tech.startswith("transit"):
        return "работает сегодня"
    return ""


# START_BLOCK: WHY_BUILDER
def build_sphere_why(evidence_list: list[Any]) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-API-SPHERE-WHY-BUILDER.build_sphere_why
    # purpose: Convert top sphere evidence items into 1-2 deterministic human why strings.
    # inputs: evidence_list (list of ConcreteAdviceEvidence objects or dicts)
    # returns: list[str] — 0 to 2 human-readable why lines
    # side_effects: none (pure calculation)
    # emitted_logs: none
    # error_behavior: skips invalid/unsupported evidence items gracefully
    # END_FUNCTION_CONTRACT: F-M-API-SPHERE-WHY-BUILDER.build_sphere_why
    if not evidence_list:
        return []

    lines: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()

    # Sort evidence by strength/weight descending
    def get_strength(ev: Any) -> float:
        if isinstance(ev, dict):
            return float(ev.get("strength") or ev.get("weight") or 0.0)
        return float(getattr(ev, "strength", None) or getattr(ev, "weight", None) or 0.0)

    sorted_evidence = sorted(evidence_list, key=get_strength, reverse=True)

    for ev in sorted_evidence:
        if len(lines) >= 2:
            break

        # Extract fields whether dict or Pydantic model
        if isinstance(ev, dict):
            planet = ev.get("planet")
            target_planet = ev.get("target_planet")
            aspect_type = ev.get("aspect_type")
            kind = ev.get("kind")
            technique_family = ev.get("technique_family")
            technique = ev.get("technique")
        else:
            planet = getattr(ev, "planet", None)
            target_planet = getattr(ev, "target_planet", None)
            aspect_type = getattr(ev, "aspect_type", None)
            kind = getattr(ev, "kind", None)
            technique_family = getattr(ev, "technique_family", None)
            technique = getattr(ev, "technique", None)

        if not planet or not target_planet:
            continue

        source_clean = strip_prefix(str(planet)).strip().capitalize()
        target_clean = strip_prefix(str(target_planet)).strip().capitalize()

        source_fn = PLANET_FUNCTIONS.get(source_clean)
        target_fn = PLANET_FUNCTIONS.get(target_clean)

        if not source_fn or not target_fn:
            continue

        pair_key = (source_clean, target_clean)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        direction, target_case = _get_direction(aspect_type)
        scale = _get_scale(kind, technique_family, technique)

        # Capitalize first letter of source function (nominative)
        source_cap = source_fn["nom"][0].upper() + source_fn["nom"][1:]
        target_form = target_fn[target_case]

        if scale:
            line = f"{source_cap} {direction} {target_form} — {scale}"
        else:
            line = f"{source_cap} {direction} {target_form}"

        lines.append(line)

    return lines
# END_BLOCK: WHY_BUILDER
