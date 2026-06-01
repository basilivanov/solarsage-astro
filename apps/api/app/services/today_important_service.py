# AI_HEADER
# module: M-TODAY-IMPORTANT-SERVICE
# wave: W-PHASE-2
# purpose: Deterministic "Today Important" items — VOC, retrograde, moon phase, eclipse, active house,
#          station, ingress. Returns ImportantTodayItem with built-in fallback details.

from __future__ import annotations

from datetime import date as Date, datetime, timedelta
from typing import Any

from app.schemas.normalization import AstroSignal
from app.schemas.today import ImportantTodayItem, ImportantTodayDetails, ImportantTodayType, ImportantTodaySeverity, ImportantTodaySource

# ── Priority map (higher = shown first) ──────────────────────────────

_PRIORITY: dict[str, int] = {
    "eclipse": 100,
    "new_moon": 90,
    "full_moon": 90,
    "moon_void": 85,
    "retrograde": 60,          # overwritten to 80 for Mercury below
    "station": 70,
    "active_house": 50,
    "ingress": 40,
    "daily_note": 30,
}

_PLANET_NAMES_RU = {
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран",
    "Neptune": "Нептун", "Pluto": "Плутон",
}

_RU_SIGN_NAMES = [
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы",
]

# ── Fallback details ─────────────────────────────────────────────────

_DETAILS_FALLBACK = {
    "moon_void": ImportantTodayDetails(
        meaning="Луна уже прошла последний значимый аспект в знаке и находится в паузе до перехода в следующий знак.",
        why_important="В такие окна лучше завершать начатое, чем запускать новое: договорённости могут позже пересобраться.",
        personal_context="У тебя это связано с активным домом дня, поэтому лучше перепроверять короткие решения и не форсировать запуск.",
    ),
    "retrograde": ImportantTodayDetails(
        meaning="Меркурий движется ретроградно, поэтому темы общения, документов, решений и маршрутов чаще требуют пересмотра.",
        why_important="Сейчас лучше закладывать время на второй круг: уточнение, перепроверку, повторный разговор.",
        personal_context="Если день затрагивает рабочие или партнёрские дома, это особенно заметно в договорённостях, сроках и формулировках.",
    ),
    "active_house": ImportantTodayDetails(
        meaning="Этот дом показывает главную сцену дня — сферу, через которую сильнее всего проявляются текущие транзиты.",
        why_important="Даже небольшие события в этой зоне могут ощущаться заметнее обычного.",
        personal_context="Сегодня главные сигналы собираются вокруг этой сферы, поэтому лучше дать ей внимание и не распыляться.",
    ),
    "new_moon": ImportantTodayDetails(
        meaning="Новолуние начинает новый лунный цикл и задаёт тему ближайших недель.",
        why_important="Это хороший момент для намерений и перезапуска, но не всегда для резкого внешнего старта.",
        personal_context="Смотри, через какой дом проходит новолуние: там начинается новая внутренняя сборка.",
    ),
    "full_moon": ImportantTodayDetails(
        meaning="Полнолуние подсвечивает накопленные темы и делает эмоции заметнее.",
        why_important="То, что раньше было фоном, может выйти наружу и потребовать реакции.",
        personal_context="Дом полнолуния показывает сферу, где проще увидеть результат, напряжение или необходимость завершения.",
    ),
    "eclipse": ImportantTodayDetails(
        meaning="Затмение сжимает во времени события, которые в обычный период растянулись бы на месяцы.",
        why_important="Решения, принятые сейчас, могут иметь длинный хвост — на полгода и больше.",
        personal_context="Смотри, в каком доме происходит затмение: эта сфера будет главной точкой перемен в ближайшие месяцы.",
    ),
    "station": ImportantTodayDetails(
        meaning="Планета замедляется перед разворотом — её тема становится заметнее и требует паузы.",
        why_important="Вблизи разворота планета действует сильнее обычного, но её проявления могут быть противоречивыми.",
        personal_context="Если эта планета затрагивает твои личные дома или натальные точки, стоит дать себе больше времени на осознание.",
    ),
    "ingress": ImportantTodayDetails(
        meaning="Планета входит в новый знак, меняя стиль своего проявления и акценты.",
        why_important="Переход в новый знак переключает фокус планеты на другие сферы жизни.",
        personal_context="Смотри, в каком доме у тебя находится этот знак — там поменяется фон на ближайшие недели.",
    ),
}

HOUSE_MEANINGS_RU = {
    1: "Тело и самочувствие требуют внимания",
    2: "Финансы и ресурсы в фокусе",
    3: "Общение и поездки активны",
    4: "Дом и семья на первом плане",
    5: "Творчество и радость важны сегодня",
    6: "Работа и здоровье требуют порядка",
    7: "Партнёрство и договорённости в приоритете",
    8: "Глубинные процессы и общие ресурсы",
    9: "Обучение и расширение горизонтов",
    10: "Рабочие темы и ответственность ощущаются сильнее",
    11: "Друзья и планы на будущее",
    12: "Уединение и восстановление",
}

RETROGRADE_DESCRIPTIONS = {
    "Меркурий": "Решения и разговоры требуют второго круга",
    "Венера": "Любовь и финансы требуют пересмотра",
    "Марс": "Энергия и действия требуют пересмотра",
    "Юпитер": "Планы расширения стоит перепроверить",
    "Сатурн": "Структуры и обязательства требуют ревизии",
    "Уран": "Перемены идут медленнее, но глубже",
    "Нептун": "Интуиция сильнее логики",
    "Плутон": "Трансформации требуют паузы и осознания",
}


class TodayImportantService:
    """Collect deterministic items for the 'Today Important' block.
    LLM does NOT select events — it only fills details."""

    def build_items(
        self,
        target_date: Date,
        timezone: str,
        natal: dict,
        transits: dict,
        signals: list[AstroSignal],
        scoring_result: dict,
        semantic_layer=None,
    ) -> list[ImportantTodayItem]:
        items: list[ImportantTodayItem] = []

        self._check_eclipse(items, transits)
        self._check_moon_phase(items, transits)
        self._check_moon_voc(items, transits, signals)
        self._check_retrogrades(items, transits)
        self._check_stations(items, transits)
        self._check_ingresses(items, transits)
        self._check_active_house(items, transits, signals, scoring_result)

        # Attach fallback details to every item (LLM may override later)
        for it in items:
            if it.details is None:
                it.details = _DETAILS_FALLBACK.get(it.type)

        # Sort by priority descending, take top 3
        items.sort(key=lambda x: x.priority, reverse=True)
        return items[:3]

    # ── Eclipse ─────────────────────────────────────────────────────

    def _check_eclipse(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        moon = self._find_planet(transit_planets, "Moon")
        north_node = self._find_planet(transit_planets, ["NORTH_NODE_TRUE", "NORTH_NODE"])
        if not moon or not north_node:
            return

        moon_lon = moon.get("longitude", 0)
        node_lon = north_node.get("longitude", 0)
        dist_to_north = abs(moon_lon - node_lon) % 360
        dist_to_south = abs(moon_lon - (node_lon + 180)) % 360
        min_dist = min(dist_to_north, dist_to_south)

        if min_dist < 18:
            sun = self._find_planet(transit_planets, "Sun")
            if sun:
                sun_lon = sun.get("longitude", 0)
                sun_node_dist = min(
                    abs(sun_lon - node_lon) % 360,
                    abs(sun_lon - node_lon - 180) % 360,
                )
                if sun_node_dist < 18:
                    items.append(ImportantTodayItem(
                        id="eclipse",
                        type="eclipse",
                        title="Затменный фон",
                        subtitle="Не форсируй резкие решения — события могут иметь длинный хвост",
                        severity="high_attention",
                        priority=_PRIORITY["eclipse"],
                        source="live_calculation",
                    ))

    # ── Moon phase ───────────────────────────────────────────────────

    def _check_moon_phase(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        moon = self._find_planet(transit_planets, "Moon")
        if not sun or not moon:
            return

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        diff = abs(moon_lon - sun_lon) % 360

        if diff < 12 or diff > 348:
            items.append(ImportantTodayItem(
                id="new_moon",
                type="new_moon",
                title="Новолуние сегодня",
                subtitle="День перезапуска, но лучше не форсировать старт",
                severity="info",
                priority=_PRIORITY["new_moon"],
                source="live_calculation",
            ))
        elif 168 < diff < 192:
            items.append(ImportantTodayItem(
                id="full_moon",
                type="full_moon",
                title="Полнолуние сегодня",
                subtitle="Эмоции и важные темы проявляются ярче",
                severity="info",
                priority=_PRIORITY["full_moon"],
                source="live_calculation",
            ))

    # ── Moon Void of Course ─────────────────────────────────────────

    def _check_moon_voc(self, items: list[ImportantTodayItem], transits: dict, signals: list[AstroSignal]):
        transit_planets = transits.get("planets", [])
        moon = self._find_planet(transit_planets, "Moon")
        if not moon:
            return

        moon_lon = moon.get("longitude", 0)
        moon_sign_idx = int(moon_lon / 30)
        next_sign_start = (moon_sign_idx + 1) * 30

        moon_aspects = [
            s for s in signals
            if s.type == "aspect" and s.planet and "Moon" in s.planet
        ]

        if not moon_aspects:
            moon_speed = abs(moon.get("speed", 13))
            degrees_to_next = next_sign_start - moon_lon
            if degrees_to_next < 0:
                degrees_to_next += 360
            hours_to_next = degrees_to_next / moon_speed
            end_time = datetime.now().replace(tzinfo=None) + timedelta(hours=hours_to_next)

            items.append(ImportantTodayItem(
                id="moon_voc",
                type="moon_void",
                title=f"Луна без курса до {end_time.strftime('%H:%M')}",
                subtitle="Новые старты дают смазанный отклик",
                severity="soft_warning",
                planet="Moon",
                ends_at=end_time.isoformat(),
                priority=_PRIORITY["moon_void"],
                source="live_calculation",
            ))

    # ── Retrogrades ─────────────────────────────────────────────────

    def _check_retrogrades(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        retro_planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

        for name in retro_planets:
            planet = self._find_planet(transit_planets, name)
            if not planet:
                continue
            speed = planet.get("speed", 0)
            if speed >= 0:
                continue

            ru_name = _PLANET_NAMES_RU.get(name, name)
            subtitle = RETROGRADE_DESCRIPTIONS.get(ru_name, "Требует пересмотра")
            priority = 80 if name == "Mercury" else _PRIORITY["retrograde"]
            title = f"{ru_name} ретрограден"
            days_remaining: int | None = None

            abs_speed = abs(speed)
            if abs_speed > 0:
                days_remaining = max(1, int(15 / (abs_speed * 10)))
                title = f"{ru_name} ретрограден · ещё {days_remaining} дней"

            detail = _DETAILS_FALLBACK.get("retrograde")
            if detail and name == "Mercury":
                pass  # Use default retrograde detail
            elif detail and name != "Mercury":
                detail = ImportantTodayDetails(
                    meaning=f"{ru_name} ретрограден: тема планеты требует пересмотра, а не прямых решений.",
                    why_important="Во время ретроградности планеты её сфера замедляется, и старые вопросы возвращаются на доработку.",
                    personal_context="Если эта планета активна в твоих домах дня, дай себе право на паузу и перепроверку.",
                )

            items.append(ImportantTodayItem(
                id=f"retro_{name.lower()}",
                type="retrograde",
                title=title,
                subtitle=subtitle,
                severity="warning" if name == "Mercury" else "soft_warning",
                planet=ru_name,
                days_remaining=days_remaining,
                priority=priority,
                source="live_calculation",
                details=detail,
            ))

    # ── Planet Stations ─────────────────────────────────────────────

    def _check_stations(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        for p in transit_planets:
            name = p.get("name", "")
            if name in ("Sun", "Moon"):
                continue
            speed = abs(p.get("speed", 1))
            if speed < 0.02:
                ru_name = _PLANET_NAMES_RU.get(name, name)
                items.append(ImportantTodayItem(
                    id=f"station_{name.lower()}",
                    type="station",
                    title=f"{ru_name} разворачивается",
                    subtitle="Тема планеты становится заметнее и требует паузы",
                    severity="soft_warning",
                    planet=ru_name,
                    priority=_PRIORITY["station"],
                    source="live_calculation",
                ))

    # ── Ingresses ───────────────────────────────────────────────────

    def _check_ingresses(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        for p in transit_planets:
            name = p.get("name", "")
            if name in ("Sun", "Moon"):
                continue
            lon = p.get("longitude", 0)
            deg_in_sign = lon % 30
            speed = p.get("speed", 0)
            if deg_in_sign < 2 and speed > 0:
                sign_idx = int(lon / 30) % 12
                ru_name = _PLANET_NAMES_RU.get(name, name)
                items.append(ImportantTodayItem(
                    id=f"ingress_{name.lower()}",
                    type="ingress",
                    title=f"{ru_name} входит в {_RU_SIGN_NAMES[sign_idx]}",
                    subtitle="Меняется стиль проявления темы дня",
                    severity="info",
                    planet=ru_name,
                    sign=_RU_SIGN_NAMES[sign_idx],
                    priority=_PRIORITY["ingress"],
                    source="live_calculation",
                ))
                break  # Only show one ingress max

    # ── Active House ────────────────────────────────────────────────

    def _check_active_house(self, items: list[ImportantTodayItem], transits: dict, signals: list[AstroSignal], scoring_result: dict):
        main_house: int | None = None

        top_signals = scoring_result.get("top_signals", [])
        for s in top_signals[:1]:
            if s.house:
                main_house = s.house
                break

        if not main_house:
            transit_planets = transits.get("planets", [])
            moon = self._find_planet(transit_planets, "Moon")
            if moon:
                main_house = int(moon.get("longitude", 0) / 30) + 1

        if not main_house:
            houses = [s for s in signals if s.type == "planet_in_house" and s.house]
            if houses:
                main_house = max(set(s.house for s in houses if s.house), key=lambda h: sum(1 for s in houses if s.house == h))

        if not main_house:
            return

        meaning = HOUSE_MEANINGS_RU.get(main_house, f"Акцент на {main_house} доме")
        items.append(ImportantTodayItem(
            id="active_house",
            type="active_house",
            title=f"Активен {main_house} дом",
            subtitle=meaning,
            severity="info",
            house=main_house,
            priority=_PRIORITY["active_house"],
            source="live_calculation",
        ))

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _find_planet(planets: list[dict], name: str | list[str]) -> dict | None:
        """Find transit planet by name(s)."""
        names = name if isinstance(name, list) else [name]
        for p in planets:
            if p.get("name") in names:
                return p
        return None
