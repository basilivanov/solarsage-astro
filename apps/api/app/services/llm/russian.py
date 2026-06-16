# ############################################################################
# AI_HEADER: LLM_RUSSIAN — Russian name mappings for planets, aspects, spheres, houses
# ROLE: Provides Russian-language dictionaries and translation helpers used by
#       prompt-building and horary modules in the llm/ package.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Centralize all Russian astrological name mappings.
# inputs: (none — module-level constants)
# returns: _PLANET_RU, _ASPECT_RU, _SPHERE_RU, _HOUSE_RU dicts; _planet() helper
# side_effects: none
# emitted_logs: none
# error_behavior: none
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - dict: _PLANET_RU
#   - dict: _ASPECT_RU
#   - dict: _SPHERE_RU
#   - dict: _HOUSE_RU
#   - function: _planet
# END_MODULE_MAP

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
