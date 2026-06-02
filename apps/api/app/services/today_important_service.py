# AI_HEADER
# module: M-TODAY-IMPORTANT-SERVICE
# wave: W-PHASE-3
# purpose: Deterministic "Today Important" — only real daily-impact events.
#          Whitelist: eclipse_window, new_moon_window, full_moon_window, moon_void,
#          mercury_retrograde, mercury_station, exact_daily_aspect, active_house.
#          No outer planet retrogrades/stations, no ingresses, no daily_note fallback.

from __future__ import annotations

from datetime import date as Date, datetime, timedelta
from typing import Any

from app.schemas.normalization import AstroSignal
from app.schemas.today import ImportantTodayItem, ImportantTodayDetails

# ── Priority map ────────────────────────────────────────────────────

_PRIORITY: dict[str, int] = {
    "eclipse_window": 100,
    "new_moon_window": 90,
    "full_moon_window": 90,
    "moon_void": 85,
    "mercury_station": 80,
    "mercury_retrograde": 75,
    "exact_daily_aspect": 70,
    "active_house": 50,
}

_LUNATION_WINDOW_DAYS = 3
_STATION_WINDOW_DAYS = 1
_ECLIPSE_WINDOW_DAYS = 3

# ── Fallback details ─────────────────────────────────────────────────

_DETAILS_FALLBACK = {
    "eclipse_window": ImportantTodayDetails(
        meaning="Затмение сжимает во времени события, которые в обычный период растянулись бы на месяцы.",
        why_important="Решения, принятые сейчас, могут иметь длинный хвост — на полгода и больше.",
        personal_context="Смотри, в каком доме происходит затмение: эта сфера будет главной точкой перемен в ближайшие месяцы.",
    ),
    "new_moon_window": ImportantTodayDetails(
        meaning="Новолуние начинает новый лунный цикл и задаёт тему ближайших недель.",
        why_important="Это хороший момент для намерений и перезапуска, но не всегда для резкого внешнего старта.",
        personal_context="Смотри, через какой дом проходит новолуние: там начинается новая внутренняя сборка.",
    ),
    "full_moon_window": ImportantTodayDetails(
        meaning="Полнолуние подсвечивает накопленные темы и делает эмоции заметнее.",
        why_important="То, что раньше было фоном, может выйти наружу и потребовать реакции.",
        personal_context="Дом полнолуния показывает сферу, где проще увидеть результат, напряжение или необходимость завершения.",
    ),
    "moon_void": ImportantTodayDetails(
        meaning="Луна уже прошла последний значимый аспект в знаке и находится в паузе до перехода в следующий знак.",
        why_important="В такие окна лучше завершать начатое, чем запускать новое: договорённости могут позже пересобраться.",
        personal_context="У тебя это связано с активным домом дня, поэтому лучше перепроверять короткие решения и не форсировать запуск.",
    ),
    "mercury_retrograde": ImportantTodayDetails(
        meaning="Меркурий движется ретроградно, поэтому темы общения, документов, решений и маршрутов чаще требуют пересмотра.",
        why_important="Сейчас лучше закладывать время на второй круг: уточнение, перепроверку, повторный разговор.",
        personal_context="Если день затрагивает рабочие или партнёрские дома, это особенно заметно в договорённостях, сроках и формулировках.",
    ),
    "mercury_station": ImportantTodayDetails(
        meaning="Меркурий замедляется перед разворотом — информация, планы и разговоры требуют паузы.",
        why_important="Вблизи разворота Меркурия связь может сбоить, а решения — требовать пересмотра позже.",
        personal_context="Если Меркурий затрагивает твои рабочие или бытовые дома, дай себе больше времени на уточнения.",
    ),
    "exact_daily_aspect": ImportantTodayDetails(
        meaning="Точный аспект сегодня означает, что взаимодействие планет достигает пика именно в этот день.",
        why_important="В момент точного аспекта энергия сфокусирована: событие или решение может иметь более заметный результат.",
        personal_context="Этот аспект связан с твоими натальными точками, поэтому эффект будет личным, а не общим.",
    ),
    "active_house": ImportantTodayDetails(
        meaning="Этот дом показывает главную сцену дня — сферу, через которую сильнее всего проявляются текущие транзиты.",
        why_important="Даже небольшие события в этой зоне могут ощущаться заметнее обычного.",
        personal_context="Сегодня главные сигналы собираются вокруг этой сферы, поэтому лучше дать ей внимание и не распыляться.",
    ),
}

# ── Planet name helpers ──────────────────────────────────────────────

_PLANET_NAMES_RU: dict[str, str] = {
    "Sun": "Солнце", "Moon": "Луна",
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран",
    "Neptune": "Нептун", "Pluto": "Плутон",
}

_ASPECT_RU: dict[str, str] = {
    "conjunction": "соединении",
    "opposition": "оппозиции",
    "trine": "трине",
    "square": "квадратуре",
    "sextile": "секстиле",
}

_ASPECT_RU_NOMINATIVE = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "трин",
    "square": "квадрат",
    "sextile": "секстиль",
}

_HOUSE_MEANINGS_RU: dict[int, str] = {
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

_HARD_ASPECTS = {"conjunction", "opposition", "square"}
_FAST_PLANETS = {"Moon", "Sun", "Mercury", "Venus", "Mars"}
_OUTER_PLANETS = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}


class TodayImportantService:
    """Collect only daily-impact items for the 'Today Important' block.
    Whitelist-only: no outer planet retrogrades, no ingresses, no daily_note fallbacks."""

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

        has_eclipse = self._check_eclipse_window(items, transits, target_date)
        self._check_lunation_window(items, transits, target_date, has_eclipse)
        self._check_moon_voc(items, transits, signals)
        has_station = self._check_mercury_station(items, transits)
        if not has_station:
            self._check_mercury_retrograde(items, transits)
        self._check_exact_daily_aspect(items, signals, scoring_result)
        self._check_active_house(items, transits, signals, scoring_result)

        for it in items:
            if it.details is None:
                it.details = _DETAILS_FALLBACK.get(it.type)

        items.sort(key=lambda x: x.priority, reverse=True)
        return items[:3]

    # ── Eclipse window ───────────────────────────────────────────────

    def _check_eclipse_window(self, items: list[ImportantTodayItem], transits: dict, target_date: Date) -> bool:
        """Detect eclipse and return True if one was added."""
        transit_planets = transits.get("planets", [])
        moon = self._find_planet(transit_planets, "Moon")
        north_node = self._find_planet(transit_planets, ["NORTH_NODE_TRUE", "NORTH_NODE"])
        if not moon or not north_node:
            return False

        moon_lon = moon.get("longitude", 0)
        node_lon = north_node.get("longitude", 0)
        dist_to_north = abs(moon_lon - node_lon) % 360
        dist_to_south = abs(moon_lon - (node_lon + 180)) % 360
        min_dist = min(dist_to_north, dist_to_south)

        if min_dist >= 18:
            return False

        sun = self._find_planet(transit_planets, "Sun")
        if not sun:
            return False

        sun_lon = sun.get("longitude", 0)
        sun_node_dist = min(
            abs(sun_lon - node_lon) % 360,
            abs(sun_lon - node_lon - 180) % 360,
        )
        if sun_node_dist >= 18:
            return False

        # Determine if exact eclipse day (Moon at node) or window day
        exact = min_dist < 4 and sun_node_dist < 4
        title = "Затмение сегодня" if exact else "Затменный фон"

        items.append(ImportantTodayItem(
            id="eclipse",
            type="eclipse_window",
            title=title,
            subtitle="Не форсируй резкие решения — события могут иметь длинный хвост",
            severity="high_attention",
            priority=_PRIORITY["eclipse_window"],
            source="live_calculation",
        ))
        return True

    # ── Lunation window (new/full moon ±3 days) ──────────────────────

    def _check_lunation_window(self, items: list[ImportantTodayItem], transits: dict, target_date: Date, has_eclipse: bool):
        """Detect new/full moon window. Eclipse suppresses lunation items."""
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        moon = self._find_planet(transit_planets, "Moon")
        if not sun or not moon:
            return

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        diff = abs(moon_lon - sun_lon) % 360
        diff = min(diff, 360 - diff)

        is_new = diff <= _LUNATION_WINDOW_DAYS * 12  # Moon moves ~12°/day
        is_full = abs(diff - 180) <= _LUNATION_WINDOW_DAYS * 12

        if not is_new and not is_full:
            return
        if has_eclipse and (is_new and diff < 18 or is_full and abs(diff - 180) < 18):
            return  # Eclipse covers this lunation

        event_type = "new_moon_window" if is_new else "full_moon_window"
        exact = diff < 4 or abs(diff - 180) < 4

        if is_new:
            if exact:
                title = "Новолуние сегодня"
                subtitle = "День перезапуска, но старт лучше делать мягко"
                prio = 90
            elif moon_lon < sun_lon or (sun_lon < 30 and moon_lon > 330):
                title = "Новолуние на подходе"
                subtitle = "Новая тема собирается — не требуй быстрых результатов"
                prio = 82
            else:
                title = "Новолуние ещё ощущается"
                subtitle = "Новая тема собирается — не требуй быстрых результатов"
                prio = 82
        else:
            if exact:
                title = "Полнолуние сегодня"
                subtitle = "Эмоции и важные темы проявляются ярче"
                prio = 90
            elif 168 < diff < 180:
                title = "Полнолуние на подходе"
                subtitle = "Эмоциональный фон нарастает — важные темы выходят наружу"
                prio = 82
            else:
                title = "Полнолуние ещё ощущается"
                subtitle = "Эмоции и важные темы проявляются ярче"
                prio = 82

        items.append(ImportantTodayItem(
            id=event_type,
            type=event_type,
            title=title,
            subtitle=subtitle,
            severity="info",
            priority=prio,
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
                subtitle="Лучше завершать начатое, чем запускать новое",
                severity="soft_warning",
                planet="Moon",
                ends_at=end_time.isoformat(),
                priority=_PRIORITY["moon_void"],
                source="live_calculation",
            ))

    # ── Mercury retrograde (only Mercury, no other planets) ─────────

    def _check_mercury_retrograde(self, items: list[ImportantTodayItem], transits: dict):
        transit_planets = transits.get("planets", [])
        mercury = self._find_planet(transit_planets, "Mercury")
        if not mercury:
            return

        speed = mercury.get("speed", 0)
        if speed >= 0:
            return

        title = "Меркурий ретрограден"
        days_remaining: int | None = None
        abs_speed = abs(speed)
        if abs_speed > 0:
            days_remaining = max(1, int(10 / abs_speed))
            title = f"Меркурий ретрограден · ещё {days_remaining} дней"

        items.append(ImportantTodayItem(
            id="retro_mercury",
            type="mercury_retrograde",
            title=title,
            subtitle="Решения и разговоры требуют второго круга",
            severity="warning",
            planet="Меркурий",
            days_remaining=days_remaining,
            priority=_PRIORITY["mercury_retrograde"],
            source="live_calculation",
        ))

    # ── Mercury station (only Mercury) ──────────────────────────────

    def _check_mercury_station(self, items: list[ImportantTodayItem], transits: dict) -> bool:
        """Returns True if station was added (to suppress retrograde)."""
        transit_planets = transits.get("planets", [])
        mercury = self._find_planet(transit_planets, "Mercury")
        if not mercury:
            return False

        speed = abs(mercury.get("speed", 1))
        if speed >= 0.05:  # Not near station
            return False

        items.append(ImportantTodayItem(
            id="station_mercury",
            type="mercury_station",
            title="Меркурий разворачивается",
            subtitle="Информация, планы и разговоры требуют паузы",
            severity="warning",
            planet="Меркурий",
            priority=_PRIORITY["mercury_station"],
            source="live_calculation",
        ))
        return True

    # ── Exact daily aspect ──────────────────────────────────────────

    def _check_exact_daily_aspect(self, items: list[ImportantTodayItem], signals: list[AstroSignal], scoring_result: dict):
        """Show a hard daily aspect if it's exact_today/peak_today/new_today and not background."""
        candidates = []

        for s in signals:
            if s.type != "aspect":
                continue
            if not s.aspect_type or not s.target_planet:
                continue

            # Must have a strong delta — not background
            if s.delta_kind in ("background", None, "weaker_than_yesterday"):
                continue
            # Must be a hard aspect (conjunction, square, opposition)
            if s.aspect_type not in _HARD_ASPECTS:
                continue
            # Prefer fast planets
            planet_name = _normalize_name(s.planet or "")
            target_name = _normalize_name(s.target_planet or "")
            is_fast = (
                planet_name in _FAST_PLANETS or
                target_name in _FAST_PLANETS
            )
            if not is_fast:
                continue

            candidates.append(s)

        if not candidates:
            return

        # Pick the strongest daily salience
        best = max(candidates, key=lambda s: s.daily_salience or s.strength)
        # Normalize planet names
        pn = _normalize_name(best.planet or "")
        tn = _normalize_name(best.target_planet or "")
        p1 = _PLANET_NAMES_RU.get(pn, pn)
        p2 = _PLANET_NAMES_RU.get(tn, tn)
        asp_ru = _ASPECT_RU.get(best.aspect_type or "", best.aspect_type or "")

        if best.aspect_type == "square":
            sub = "Энергия требует собранности — не форсируй конфликт"
        elif best.aspect_type == "opposition":
            sub = "Напряжение между темами — ищи баланс, а не крайность"
        else:
            sub = "Фокус на стыковке этих двух тем"

        items.append(ImportantTodayItem(
            id="exact_daily_aspect",
            type="exact_daily_aspect",
            title=f"{p1} в {asp_ru} с {p2}",
            subtitle=sub,
            severity="soft_warning",
            planet=p1,
            priority=_PRIORITY["exact_daily_aspect"],
            source="live_calculation",
        ))

    # ── Active House ────────────────────────────────────────────────

    def _check_active_house(self, items: list[ImportantTodayItem], transits: dict, signals: list[AstroSignal], scoring_result: dict):
        main_house: int | None = None

        top_signals = scoring_result.get("top_signals", [])
        for s in top_signals[:1]:
            if getattr(s, "house", None):
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
                house_list = [s.house for s in houses if s.house]
                if house_list:
                    main_house = max(set(house_list), key=house_list.count)

        if not main_house:
            return

        meaning = _HOUSE_MEANINGS_RU.get(main_house, f"Акцент на {main_house} доме")
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
        names = name if isinstance(name, list) else [name]
        for p in planets:
            if p.get("name") in names:
                return p
        return None


def _normalize_name(name: str) -> str:
    """Strip Transit_/Natal_ prefix for lookup."""
    for prefix in ("Transit_", "Natal_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name
