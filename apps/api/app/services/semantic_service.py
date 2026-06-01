# AI_HEADER
# module: M-SEMANTIC-SERVICE
# wave: W-4.3
# purpose: Semantic layer service — computes 9 WhyThisHappens section contexts

from app.schemas.semantic import SemanticLayer, SphereTheme

# ── Transliterations ──────────────────────────────────────────────

_PLANET_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна",
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн",
    "Uranus": "Уран", "Neptune": "Нептун", "Pluto": "Плутон",
}
_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединении", "opposition": "оппозиции",
    "trine": "трине", "square": "квадратуре", "sextile": "секстиле",
}
_SPHERE_RU: dict[str, str] = {
    "personal": "личная жизнь", "relationships": "отношения",
    "career": "карьера", "finance": "финансы",
    "health": "здоровье", "creativity": "творчество",
    "spirituality": "духовное развитие",
}

def _p(s: str) -> str: return _PLANET_RU.get(s, s)
def _a(s: str) -> str: return _ASPECT_RU.get(s, s)

# Theme mappings
DAY_THEMES = {
    "supportive": "День возможностей",
    "steady": "Спокойный день",
    "tense": "День вызовов",
}

SPHERE_THEMES = {
    "career": {"high": ("Активный рост", ["продвижение", "успех", "признание"]), "medium": ("Стабильность", ["работа", "задачи", "рутина"]), "low": ("Затишье", ["отдых", "планирование"])},
    "relationships": {"high": ("Гармония", ["близость", "понимание", "любовь"]), "medium": ("Ровные отношения", ["общение", "поддержка"]), "low": ("Дистанция", ["одиночество", "размышления"])},
    "health": {"high": ("Энергия", ["бодрость", "активность", "сила"]), "medium": ("Норма", ["здоровье", "баланс"]), "low": ("Усталость", ["отдых", "восстановление"])},
    "creativity": {"high": ("Вдохновение", ["творчество", "идеи", "самовыражение"]), "medium": ("Потенциал", ["хобби", "интересы"]), "low": ("Пауза", ["рефлексия", "накопление"])},
}


class SemanticService:

    def __init__(self):
        pass

    def build_semantic_layer(
        self,
        day_status: str,
        sphere_scores: dict[str, float],
    ) -> SemanticLayer:
        day_theme = DAY_THEMES.get(day_status, "Обычный день")
        sphere_themes = []
        all_keywords = []
        for sphere, score in sphere_scores.items():
            if sphere not in SPHERE_THEMES:
                continue
            level = "high" if score >= 3 else ("medium" if score >= 1 else "low")
            theme, keywords = SPHERE_THEMES[sphere][level]
            sphere_themes.append(SphereTheme(sphere=sphere, score=score / 5.0, theme=theme, keywords=keywords))
            all_keywords.extend(keywords)
        top_keywords = list(dict.fromkeys(all_keywords))[:5]
        return SemanticLayer(
            day_status=day_status, day_theme=day_theme,
            sphere_themes=sphere_themes, top_keywords=top_keywords,
        )

    def build_why_contexts(
        self,
        day_status: str,
        sphere_scores: dict,
        top_signals: list,
        natal: dict,
        transits: dict,
        semantic_layer: SemanticLayer,
    ) -> list[dict]:
        """Compute pre-filled context for each of 9 WhyThisHappens sections.
        LLM only writes narrative text — no numbers, no planet names.
        Returns list of dicts: {layer, title, context, blocks_kind}"""
        
        natal_planets = natal.get("planets", []) if natal else []
        transit_planets = transits.get("planets", []) if transits else []

        # Helpers
        def natal_planet(name: str) -> dict | None:
            for p in natal_planets:
                if p.get("name") == name:
                    return p
            return None

        def top_of_type(kind: str):
            for s in top_signals:
                if s.type == kind:
                    return s
            return None

        def signal_lines(signals, kind: str | None = None) -> list[str]:
            lines = []
            for s in signals:
                if kind and s.type != kind:
                    continue
                p = _p(s.planet)
                if s.type == "planet_in_house":
                    lines.append(f"- {p} в {s.house} доме (сила {s.strength:.2f})")
                elif s.type == "aspect" and s.aspect_type and s.target_planet:
                    a = _a(s.aspect_type)
                    t = _p(s.target_planet)
                    lines.append(f"- {p} в {a} с {t} (орб {s.orb:.1f}°, сила {s.strength:.2f})")
            return lines

        aspects = [s for s in top_signals if s.type == "aspect"]
        houses = [s for s in top_signals if s.type == "planet_in_house"]
        top_aspect = aspects[0] if aspects else None
        top_house = houses[0] if houses else None

        # Build 9 contexts
        contexts = []

        # 01 main_theme
        main_parts = [f"Статус дня: {DAY_THEMES.get(day_status, 'Обычный день')}."]
        if top_aspect:
            main_parts.append(f"Доминирующий аспект: {_p(top_aspect.planet)} в {_a(top_aspect.aspect_type)} с {_p(top_aspect.target_planet)} (сила {top_aspect.strength:.2f}).")
        if top_house:
            main_parts.append(f"Ведущий транзит: {_p(top_house.planet)} в {top_house.house} доме.")
        if houses:
            house_nums = sorted(set(s.house for s in houses if s.house))
            if len(house_nums) >= 2:
                main_parts.append(f"Ось домов: {house_nums[0]}-{house_nums[-1]}.")
        contexts.append({"layer": "main_theme", "title": "Главная тема дня", "context": " ".join(main_parts), "blocks_kind": "paragraph"})

        # 02 daily_layer
        daily_parts = []
        moon_transit = next((t for t in transit_planets if t.get("name") == "Moon"), None)
        if moon_transit:
            daily_parts.append(f"Луна: {moon_transit.get('sign', '?')} ({moon_transit.get('longitude', 0) % 30:.1f}°).")
        contexts.append({"layer": "daily_layer", "title": "Быстрый слой дня", "context": " ".join(daily_parts) or "Данные по быстрым транзитам.", "blocks_kind": "paragraph"})

        # 03 personal_activation
        pers_parts = []
        for s in aspects[:3]:
            np = natal_planet(s.target_planet or "")
            if np:
                pers_parts.append(f"Транзитный {_p(s.planet)} активирует натальный {_p(s.target_planet or '')} ({np.get('sign','?')} дом {s.house or '?'}): {_a(s.aspect_type or '')}, орб {s.orb:.1f}°.")
        if not pers_parts:
            for s in houses[:2]:
                pers_parts.append(f"Транзитный {_p(s.planet)} ({s.house} дом) акцентирует тему этого дома в натальной карте.")
        contexts.append({"layer": "personal_activation", "title": "Почему это задевает именно тебя", "context": " ".join(pers_parts) or "Нет ярко выраженных личных активаций.", "blocks_kind": "paragraph"})

        # 04 period_background
        contexts.append({"layer": "period_background", "title": "Фон периода", "context": f"Солярный акцент: дома {', '.join(str(s.house) for s in houses[:3] if s.house)}. Тема периода: {semantic_layer.day_theme}.", "blocks_kind": "paragraph"})

        # 05 amplifiers
        amp_lines = signal_lines(top_signals, "aspect")
        amp_text = "\n".join(amp_lines[:3]) if amp_lines else "Нет выраженных усилителей."
        contexts.append({"layer": "amplifiers", "title": "Что усиливает этот день", "context": amp_text, "blocks_kind": "paragraph"})

        # 06 softeners — гармоничные аспекты
        harmony_signals = [s for s in aspects if s.aspect_type in ("trine", "sextile")]
        soft_lines = []
        for s in harmony_signals[:3]:
            soft_lines.append(f"- {_p(s.planet)} в {_a(s.aspect_type)} с {_p(s.target_planet or '')} (орб {s.orb:.1f}°)")
        soft_text = "\n".join(soft_lines) if soft_lines else "Нет выраженных смягчающих аспектов."
        contexts.append({"layer": "softeners", "title": "Что смягчает этот день", "context": soft_text, "blocks_kind": "paragraph"})

        # 07 manifestation_zones
        zone_items = []
        for s in houses[:5]:
            zone_items.append(f"{s.house} дом — {_p(s.planet)} (сила {s.strength:.2f})")
        contexts.append({"layer": "manifestation_zones", "title": "Через какие сферы это проявляется", "context": "\n".join(zone_items) or "Через основные сферы жизни.", "blocks_kind": "bullets"})

        # 08 astrological_meaning
        meaning_text = f"Статус дня: {DAY_THEMES.get(day_status, '')}. "
        if top_aspect:
            meaning_text += f"Ключевой аспект: {_p(top_aspect.planet)}-{_p(top_aspect.target_planet or '')} ({_a(top_aspect.aspect_type)}). "
        meaning_text += "Это день пересборки — уточнения, а не прорыва." if day_status != "supportive" else "Это день поддержки — можно двигаться вперёд."
        contexts.append({"layer": "astrological_meaning", "title": "Астрологический смысл дня", "context": meaning_text, "blocks_kind": "paragraph"})

        # 09 practical_meaning
        practical_items = []
        if day_status == "supportive":
            practical_items = ["Действуй — сегодня энергии планет поддерживают начинания.", "Общайся с близкими — аспекты благоприятствуют отношениям.", "Заверши отложенные задачи — день даёт импульс."]
        elif day_status == "tense":
            practical_items = ["Отложи важные решения — день с высоким напряжением.", "Сфокусируйся на рутине, избегай конфликтов.", "Дай себе паузу перед реакцией — эмоции могут зашкаливать."]
        else:
            practical_items = ["Занимайся плановой работой — нейтральный день.", "Не форсируй — день сам всё расставит.", "Анализируй, планируй, но не запускай нового."]
        contexts.append({"layer": "practical_meaning", "title": "Что это значит практически", "context": "\n".join(f"- {item}" for item in practical_items), "blocks_kind": "bullets"})

        return contexts
