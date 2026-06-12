# ############################################################################
# AI_HEADER: MODULE_LLM_PROMPTS
# ROLE: Prompt builder functions — signal descriptions, sphere descriptions,
#       semantic context, full context
# DEPENDENCIES: app.services.llm.russian
# GRACE_ANCHORS: [BUILD_SIGNAL_DESCRIPTIONS, BUILD_SPHERE_DESCRIPTIONS,
#                  BUILD_SEMANTIC_CONTEXT, BUILD_FULL_CONTEXT]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-PROMPTS
# purpose: Build structured prompt context strings for LLM generation.
# owns:
#   - apps/api/app/services/llm/prompts.py
# inputs:
#   - signals (list), sphere_scores (dict), semantic_layer (dict|Model),
#     natal (dict), top_signals (list)
# outputs:
#   - str — formatted context text
# dependencies:
#   - M-LLM-RUSSIAN (_planet, _HOUSE_RU, _ASPECT_RU, _SPHERE_RU)
# invariants:
#   - all outputs are deterministic (no randomness)
# failure_policy:
#   - returns "— нет ..." fallback text on empty input
# END_MODULE_CONTRACT: M-LLM-PROMPTS

# START_MODULE_MAP: M-LLM-PROMPTS
# public_entrypoints:
#   - _build_signal_descriptions
#   - _build_sphere_descriptions
#   - _build_semantic_context
#   - _build_full_context
# END_MODULE_MAP: M-LLM-PROMPTS

from app.services.llm.russian import _planet, _HOUSE_RU, _ASPECT_RU, _SPHERE_RU


def _build_signal_descriptions(signals: list, limit: int = 5) -> str:
    lines = []
    for s in signals[:limit]:
        p = _planet(s.planet)
        if s.type == "planet_in_house":
            h = _HOUSE_RU.get(s.house or 0, f"{s.house} дом")
            lines.append(
                f"- {p} в {h} (сила {s.strength:.2f})"
            )
        elif s.type == "aspect" and s.aspect_type and s.target_planet:
            a = _ASPECT_RU.get(s.aspect_type, s.aspect_type)
            t = _planet(s.target_planet)
            lines.append(
                f"- {p} в {a}е с {t} (орб {s.orb:.1f}°, сила {s.strength:.2f})"
            )
    return "\n".join(lines) if lines else "— нет ярко выраженных сигналов"


def _build_sphere_descriptions(sphere_scores: dict) -> str:
    lines = []
    for s, v in sorted(sphere_scores.items(), key=lambda x: -x[1]):
        name = _SPHERE_RU.get(s, s)
        level = "сильное" if v >= 3 else ("среднее" if v >= 1 else "слабое")
        lines.append(f"- {name}: {level} влияние (балл: {v})")
    return "\n".join(lines) or "— нет данных по сферам"


def _build_semantic_context(semantic_layer) -> str:
    if hasattr(semantic_layer, 'model_dump'):
        sl = semantic_layer.model_dump()
    elif isinstance(semantic_layer, dict):
        sl = semantic_layer
    else:
        return ""

    day_theme = sl.get("day_theme", "")
    sphere_themes = sl.get("sphere_themes", [])
    keywords = sl.get("top_keywords", sl.get("keywords", []))

    parts = []
    if day_theme:
        parts.append(f"Тема дня: {day_theme}")
    if sphere_themes:
        themes_text = ", ".join(
            f"{t.get('sphere', '')}: {t.get('theme', '')}"
            for t in sphere_themes[:4]
        )
        if themes_text.strip():
            parts.append(f"Темы сфер: {themes_text}")
    if keywords:
        parts.append(f"Ключевые слова: {', '.join(keywords[:6])}")
    return "\n".join(parts) if parts else ""


def _build_full_context(
    natal: dict,
    top_signals: list,
    sphere_scores: dict,
    semantic_layer,
) -> str:
    """Build rich context for LLM — natal chart, ranked signals, grouping."""
    parts = []

    parts.append("=== НАТАЛЬНАЯ КАРТА ===")
    natal_planets = natal.get("planets", [])
    for p in natal_planets:
        name = _planet(p.get("name", ""))
        sign = p.get("sign", "?")
        lon = p.get("longitude", 0)
        sign_deg = lon % 30
        parts.append(
            f"- {name}: {sign_deg:.1f}° {sign}"
        )

    parts.append("\n=== ТОП-ТРАНЗИТЫ (по силе) ===")
    for i, s in enumerate(top_signals[:5]):
        p = _planet(s.planet)
        if s.type == "planet_in_house":
            parts.append(
                f"{i+1}. [сила {s.strength:.2f}] {p} в {s.house} доме"
            )
        elif s.type == "aspect" and s.aspect_type and s.target_planet:
            a = _ASPECT_RU.get(s.aspect_type, s.aspect_type)
            t = _planet(s.target_planet)
            parts.append(
                f"{i+1}. [сила {s.strength:.2f}] {p} {a} {t} (орб {s.orb:.1f}°)"
            )

    parts.append("\n=== ГРУППИРОВКА ===")
    houses = [s for s in top_signals if s.type == "planet_in_house"]
    aspects = [s for s in top_signals if s.type == "aspect"]
    if houses:
        house_list = ", ".join(
            f"{_planet(s.planet)}({s.house} дом)" for s in houses
        )
        parts.append(f"Планеты в домах: {house_list}")
    if aspects:
        aspect_list = ", ".join(
            f"{_planet(s.planet)}-{_planet(s.target_planet or '?')} ({_ASPECT_RU.get(s.aspect_type or '', s.aspect_type or '')})"
            for s in aspects
        )
        parts.append(f"Аспекты: {aspect_list}")

    parts.append("\n=== СФЕРЫ ПО ВЛИЯНИЮ ===")
    for sphere, score in sorted(sphere_scores.items(), key=lambda x: -x[1]):
        name = _SPHERE_RU.get(sphere, sphere)
        level = "сильное" if score >= 3 else ("среднее" if score >= 1 else "слабое")
        parts.append(f"- {name}: {level} (балл {score})")

    sem = _build_semantic_context(semantic_layer)
    if sem:
        parts.append(f"\n=== СЕМАНТИКА ===\n{sem}")

    return "\n".join(parts)
