# ############################################################################
# AI_HEADER: MODULE_FOCUS_TITLE_BUILDER
# ROLE: Pure service module building human-first event titles and clean technical titles without LLM.
# DEPENDENCIES: app.services.astro_utils
# ############################################################################

# START_MODULE_CONTRACT: M-FOCUS-TITLE-BUILDER
# purpose: Build deterministic human titles ("Марс напротив твоего Нептуна") and technical titles without raw prefixes or machine keys (§2 of C2 TZ).
# owns:
#   - apps/api/app/services/focus_title_builder.py
# inputs: factor (TodayFactor | dict | Any)
# outputs: build_event_title -> tuple[str, str | None]
# dependencies: app.services.astro_utils
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: returns clean human title or falls back to planet/factor label
# END_MODULE_CONTRACT: M-FOCUS-TITLE-BUILDER

# START_MODULE_MAP: M-FOCUS-TITLE-BUILDER
# public_entrypoints:
#   - build_event_title
#   - check_public_title_eligibility
# semantic_blocks:
#   - TITLE_BUILDER: Russian declension, aspect phrasing, house/angle/lot formatting
#   - TITLE_ELIGIBILITY: deterministic check for public title eligibility
# owned_tests:
#   - tests/test_today_focus_title_builder.py
# END_MODULE_MAP: M-FOCUS-TITLE-BUILDER

from __future__ import annotations

from typing import Any
from app.services.astro_utils import strip_prefix

PLANET_NOMINATIVE_RU: dict[str, str] = {
    "SUN": "Солнце",
    "MOON": "Луна",
    "MERCURY": "Меркурий",
    "VENUS": "Венера",
    "MARS": "Марс",
    "JUPITER": "Юпитер",
    "SATURN": "Сатурн",
    "URANUS": "Уран",
    "NEPTUNE": "Нептун",
    "PLUTO": "Плутон",
}

PLANET_INSTRUMENTAL_RU: dict[str, str] = {
    "SUN": "Солнцем",
    "MOON": "Луной",
    "MERCURY": "Меркурием",
    "VENUS": "Венерой",
    "MARS": "Марсом",
    "JUPITER": "Юпитером",
    "SATURN": "Сатурном",
    "URANUS": "Ураном",
    "NEPTUNE": "Нептуном",
    "PLUTO": "Плутоном",
}

PLANET_GENITIVE_RU: dict[str, str] = {
    "SUN": "Солнца",
    "MOON": "Луны",
    "MERCURY": "Меркурия",
    "VENUS": "Венеры",
    "MARS": "Марса",
    "JUPITER": "Юпитера",
    "SATURN": "Сатурна",
    "URANUS": "Урана",
    "NEPTUNE": "Нептуна",
    "PLUTO": "Плутона",
}

ASPECT_LABELS_RU: dict[str, str] = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "тригон",
    "square": "квадратура",
    "sextile": "секстиль",
    "quincunx": "квиконс",
    "semi_square": "полуквадрат",
    "sesquisquare": "полутораквадрат",
    "sesqui_quadrate": "полутораквадрат",
    "semi_sextile": "полусекстиль",
}

ANGLE_LABELS_RU: dict[str, str] = {
    "ASC": "Асцендента",
    "MC": "Меридиана (MC)",
    "IC": "Надира (IC)",
    "DESC": "Десцендента",
    "DSC": "Десцендента",
}

LOT_LABELS_RU: dict[str, str] = {
    "FORTUNE": "Фортуны",
    "SPIRIT": "Духа",
    "EROS": "Эроса",
    "SCIENCE": "Знания",
    "MARRIAGE": "Брака",
}

HOUSE_ORDINAL_RU: dict[int, str] = {
    1: "1-м", 2: "2-м", 3: "3-м", 4: "4-м", 5: "5-м", 6: "6-м",
    7: "7-м", 8: "8-м", 9: "9-м", 10: "10-м", 11: "11-м", 12: "12-м",
}


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# START_BLOCK: TITLE_BUILDER
def build_event_title(factor: Any) -> tuple[str, str | None]:
    # START_FUNCTION_CONTRACT: F-M-FOCUS-TITLE-BUILDER.build_event_title
    # purpose: Build deterministic human_title and technical_title for an event without jargon or machine preambles (§2 of C2 TZ).
    # inputs: factor (TodayFactor | dict | Any)
    # returns: (human_title, technical_title)
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns clean fallback title on unknown formats
    # END_FUNCTION_CONTRACT: F-M-FOCUS-TITLE-BUILDER.build_event_title
    factor_id = str(_get_field(factor, "factor_id") or "")
    src_raw = _get_field(factor, "source_key") or ""
    tgt_raw = _get_field(factor, "target_key") or ""
    target_type = str(_get_field(factor, "target_type") or "").lower()
    tech_family = str(_get_field(factor, "technique_family") or "").lower()
    technique = str(_get_field(factor, "technique") or "").lower()

    src_clean = strip_prefix(str(src_raw)).upper()
    tgt_clean = strip_prefix(str(tgt_raw)).upper()

    src_nom = PLANET_NOMINATIVE_RU.get(src_clean, src_clean or "Планета")
    tgt_nom = PLANET_NOMINATIVE_RU.get(tgt_clean, tgt_clean)
    # Lot targets without a human label degrade to «жребий» forms, never machine keys
    if target_type == "lot" and tgt_clean not in PLANET_NOMINATIVE_RU:
        lot_nom = LOT_LABELS_RU.get(tgt_clean)
        tgt_nom = lot_nom or "жребий"
        tgt_inst = lot_nom or "жребием"
        tgt_gen = lot_nom or "жребия"
    else:
        tgt_inst = PLANET_INSTRUMENTAL_RU.get(tgt_clean, tgt_clean)
        tgt_gen = PLANET_GENITIVE_RU.get(tgt_clean, tgt_clean)

    # 1. Slow layers (firdar / profection / return)
    if tech_family == "firdar" or technique == "firdar":
        human = f"Фирдар: {src_nom} — тема периода"
        return human, f"Фирдар {src_nom}"
    if tech_family == "profection" or technique == "profection":
        human = f"Профекция: {src_nom} в фокусе"
        return human, f"Профекция {src_nom}"
    if tech_family in ("solar_return", "lunar_return") or technique in ("solar_return", "lunar_return", "return"):
        label = "Соляр" if "solar" in tech_family or "solar" in technique else "Лунар"
        period_word = "года" if label == "Соляр" else "месяца"
        # Angular-planet return factors carry no real source planet (the ledger
        # may even capture "Lunar"/"Solar" from the evidence sentence): the
        # meaningful planet is the TARGET, optionally refined by the house.
        if src_clean not in PLANET_NOMINATIVE_RU and tgt_clean in PLANET_NOMINATIVE_RU:
            house = _get_field(factor, "house")
            house_suffix = f" ({house} дом)" if isinstance(house, int) else ""
            human = f"{label}: {tgt_nom} — тема {period_word}"
            return human, f"{label}: {tgt_nom} на углу{house_suffix}"
        human = f"{label}: {src_nom} — тема {period_word}"
        return human, f"{label} {src_nom}"

    # 2. Aspect factors
    parts = factor_id.split(":")
    if (len(parts) >= 5 and parts[1] == "aspect") or _get_field(factor, "aspect_type"):
        asp_raw = str(_get_field(factor, "aspect_type") or (parts[3] if len(parts) >= 5 else "")).lower()
        asp_ru = ASPECT_LABELS_RU.get(asp_raw, asp_raw)

        if asp_raw in ("opposition", "square", "quincunx", "semi_square", "sesquisquare", "sesqui_quadrate"):
            if asp_raw == "opposition":
                human = f"{src_nom} напротив твоего {tgt_gen}"
            else:
                human = f"{src_nom} в напряжении с твоим {tgt_inst}"
        elif asp_raw in ("trine", "sextile", "semi_sextile"):
            human = f"{src_nom} в гармонии с твоим {tgt_inst}"
        elif asp_raw == "conjunction":
            human = f"{src_nom} сошлась с твоим {tgt_inst}"
        else:
            human = f"{src_nom} {asp_ru} {tgt_nom}"

        tech = f"{src_nom} {asp_ru} {tgt_nom}"
        return human, tech

    # 3. Angle / Lot / House factors
    if target_type == "angle" or tgt_clean in ANGLE_LABELS_RU:
        angle_ru = ANGLE_LABELS_RU.get(tgt_clean, tgt_clean)
        human = f"{src_nom} у твоего {angle_ru}"
        return human, f"{src_nom} на {tgt_clean}"

    if target_type == "lot" or tgt_clean in LOT_LABELS_RU:
        lot_ru = LOT_LABELS_RU.get(tgt_clean)
        if lot_ru:
            human = f"{src_nom} у Жребия {lot_ru}"
            return human, f"{src_nom} у Жребия {lot_ru}"
        # Lot without a human label: never leak the machine key to users
        return f"{src_nom} у твоего жребия", f"{src_nom} у жребия"

    if target_type == "house" or (len(parts) >= 4 and parts[1] == "house"):
        # House number: the dedicated field, else the target key itself (house factors
        # key their target as the house number), else the semantic id segment.
        house_num_raw = _get_field(factor, "house") or (tgt_raw if target_type == "house" else "") or (parts[3] if len(parts) >= 4 else "")
        try:
            h_int = int(house_num_raw)
            h_ord = HOUSE_ORDINAL_RU.get(h_int, f"{h_int}-м")
        except (TypeError, ValueError):
            h_ord = f"{house_num_raw}"

        human = f"{src_nom} в твоём {h_ord} доме"
        return human, f"{src_nom} в {house_num_raw} доме"

    # Default clean fallback
    human = f"{src_nom} {tgt_nom}".strip() or factor_id
    return human, human
# END_BLOCK: TITLE_BUILDER


# START_BLOCK: TITLE_ELIGIBILITY
def check_public_title_eligibility(human_title: str | None) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-FOCUS-TITLE-BUILDER.check_public_title_eligibility
    # purpose: Check deterministic eligibility of human title for public event selection (amendment §3.1 п.5).
    # inputs: human_title (str | None)
    # returns: reason_code (str) if ineligible, or None if eligible
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns reason code on missing or invalid title
    # END_FUNCTION_CONTRACT: F-M-FOCUS-TITLE-BUILDER.check_public_title_eligibility
    if not human_title or not human_title.strip():
        return "empty_title"

    if any(prefix in human_title for prefix in ("Transit_", "Natal_", "transit_", "natal_")):
        return "machine_key"

    import re
    if re.search(r"\b[A-Z][A-Z0-9_]{2,}\b", human_title):
        return "machine_key"

    return None
# END_BLOCK: TITLE_ELIGIBILITY
