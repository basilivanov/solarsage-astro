# ############################################################################
# AI_HEADER: MODULE_LLM_RUSSIAN
# ROLE: Russian name mappings for planets, aspects, houses, spheres
# DEPENDENCIES: none (pure data)
# GRACE_ANCHORS: [PLANET_RU, ASPECT_RU, HOUSE_RU, SPHERE_RU, PLANET_FN]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-RUSSIAN
# purpose: Provide Russian translations for astrological entities.
# owns:
#   - apps/api/app/services/llm/russian.py
# inputs:
#   - planet/aspect/house/sphere names (str | int)
# outputs:
#   - Russian-localized strings
# dependencies:
#   - none (pure dict + pure function)
# invariants:
#   - dicts are frozen by convention (no mutation after import)
# failure_policy:
#   - _planet() returns the original string if not found
# END_MODULE_CONTRACT: M-LLM-RUSSIAN

_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна",
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн",
    "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединение", "opposition": "оппозиция",
    "trine": "трин", "square": "квадратура", "sextile": "секстиль",
}

_SPHERE_RU: dict[str, str] = {
    "personal": "личная жизнь", "relationships": "отношения",
    "career": "карьера", "finance": "финансы",
    "health": "здоровье", "creativity": "творчество",
    "spirituality": "духовное развитие",
}

_HOUSE_RU: dict[int, str] = {
    1: "1 дом (личность)", 2: "2 дом (финансы)", 3: "3 дом (общение)",
    4: "4 дом (семья)", 5: "5 дом (творчество)", 6: "6 дом (здоровье)",
    7: "7 дом (партнёрство)", 8: "8 дом (трансформация)", 9: "9 дом (путешествия)",
    10: "10 дом (карьера)", 11: "11 дом (друзья)", 12: "12 дом (подсознание)",
}


def _planet(s: str) -> str:
    """Translate planet name to Russian, or pass through if unknown."""
    return _PLANET_RU.get(s, s)
