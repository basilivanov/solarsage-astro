# ############################################################################
# AI_HEADER: MODULE_TODAY_IMPORTANT_SERVICE
# ROLE: Deterministic "Today Important" — daily-impact astrological alerts.
# DEPENDENCIES: stdlib only
# GRACE_ANCHORS: [BUILD_ITEMS, EVENT_CHECKS]
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-SERVICE.important_service
# purpose: Extract and prioritize key daily transit events for the user.
# owns:
#   - apps/api/app/services/today_important_service.py
# inputs:
#   - target_date: Date, timezone: str, natal: dict, transits: dict, signals: list[AstroSignal]
# outputs:
#   - list[TodayImportantEvent]
# invariants:
#   - maximum 3 events returned.
#   - eclipse events take precedence over regular new/full moons.
# END_MODULE_CONTRACT: M-DAY-SERVICE.important_service

# START_MODULE_MAP: M-DAY-SERVICE.important_service
# public_entrypoints:
#   - TodayImportantService.build_items
# END_MODULE_MAP: M-DAY-SERVICE.important_service

from __future__ import annotations

from datetime import date as Date, datetime, timedelta, timezone
from typing import Any

from app.schemas.normalization import AstroSignal
from app.schemas.today import TodayImportantEvent

_PLANET_NAMES_RU: dict[str, str] = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
}

_ASPECT_RU_NOMINATIVE = {
    "conjunction": "соединение",
    "opposition": "оппозиция",
    "trine": "трин",
    "square": "квадрат",
    "sextile": "секстиль",
}


class TodayImportantService:
    def build_items(
        self,
        target_date: Date,
        timezone: str,
        natal: dict,
        transits: dict,
        signals: list[AstroSignal],
        scoring_result: dict = None,
        semantic_layer=None,
    ) -> list[TodayImportantEvent]:
        # START_FUNCTION_CONTRACT: M-DAY-SERVICE.important_service.build_items
        # purpose: Scan transit parameters and build the prioritized whitelisted list of events.
        # inputs: target_date (Date), timezone (str), natal (dict), transits (dict), signals (list[AstroSignal])
        # returns: list[TodayImportantEvent]
        # side_effects: none
        # emitted_logs: none
        # error_behavior: propagates database/key errors
        # END_FUNCTION_CONTRACT: M-DAY-SERVICE.important_service.build_items
        
        items: list[TodayImportantEvent] = []

        # 1. Eclipse and lunation checks
        has_eclipse = self._check_eclipses(items, transits, target_date)
        self._check_lunation(items, transits, has_eclipse)

        # 2. Moon Void of Course
        self._check_moon_voc(items, transits, signals, timezone)

        # 3. Mercury retro / station
        self._check_mercury(items, transits, timezone)

        # 4. Moon Quarter
        self._check_moon_quarter(items, transits, timezone)

        # 5. Sun Ingress
        self._check_sun_ingress(items, transits, timezone)

        # 6. Fast Planet Aspects
        self._check_fast_planet_aspects(items, signals, timezone)

        # Sort by priority, then limit to max 3
        items.sort(key=lambda x: x.priority, reverse=True)
        return items[:3]

    def _check_eclipses(self, items: list[TodayImportantEvent], transits: dict, target_date: Date) -> bool:
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        moon = self._find_planet(transit_planets, "Moon")
        north_node = self._find_planet(transit_planets, ["NORTH_NODE_TRUE", "NORTH_NODE"])
        if not sun or not moon or not north_node:
            return False

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        node_lon = north_node.get("longitude", 0)

        # Sun near node (eclipse season ±3 days)
        sun_node_dist = min(
            abs(sun_lon - node_lon) % 360,
            abs(sun_lon - (node_lon + 180)) % 360,
        )
        if sun_node_dist >= 18:
            return False

        diff = abs(moon_lon - sun_lon) % 360
        diff = min(diff, 360 - diff)

        is_new = diff <= 3 * 12
        is_full = abs(diff - 180) <= 3 * 12

        if not is_new and not is_full:
            return False

        # Moon near Node (actual eclipse window)
        moon_node_dist = min(
            abs(moon_lon - node_lon) % 360,
            abs(moon_lon - (node_lon + 180)) % 360,
        )
        if moon_node_dist >= 18:
            return False

        exact = diff < 4 or abs(diff - 180) < 4

        if is_new:
            title = "Солнечное затмение сегодня" if exact else "Солнечное затмение"
            items.append(TodayImportantEvent(
                id="solar_eclipse",
                kind="solar_eclipse",
                tone="caution",
                title=title,
                summary="Сильная точка разворота. Лучше не принимать резких решений на эмоциях.",
                priority=100,
                timezone="UTC",
            ))
            return True
        elif is_full:
            title = "Лунное затмение сегодня" if exact else "Лунное затмение"
            items.append(TodayImportantEvent(
                id="lunar_eclipse",
                kind="lunar_eclipse",
                tone="caution",
                title=title,
                summary="Сильная точка разворота. Лучше не принимать резких решений на эмоциях.",
                priority=100,
                timezone="UTC",
            ))
            return True

        return False

    def _check_lunation(self, items: list[TodayImportantEvent], transits: dict, has_eclipse: bool):
        if has_eclipse:
            return
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        moon = self._find_planet(transit_planets, "Moon")
        if not sun or not moon:
            return

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        diff = abs(moon_lon - sun_lon) % 360
        diff = min(diff, 360 - diff)

        is_new = diff <= 3 * 12
        is_full = abs(diff - 180) <= 3 * 12

        if not is_new and not is_full:
            return

        exact = diff < 4 or abs(diff - 180) < 4

        if is_new:
            if exact:
                title = "Новолуние сегодня"
            elif moon_lon < sun_lon or (sun_lon < 30 and moon_lon > 330):
                title = "Новолуние на подходе"
            else:
                title = "Новолуние было 2 дня назад"
            items.append(TodayImportantEvent(
                id="new_moon",
                kind="new_moon",
                tone="neutral_shift",
                title=title,
                summary="День перезагрузки и нового цикла. Лучше не форсировать, а настроить направление.",
                priority=90 - int(diff / 4),
                timezone="UTC",
            ))
        elif is_full:
            if exact:
                title = "Полнолуние сегодня"
            elif 168 < diff < 180:
                title = "Полнолуние на подходе"
            else:
                title = "Полнолуние было 2 дня назад"
            items.append(TodayImportantEvent(
                id="full_moon",
                kind="full_moon",
                tone="neutral_shift",
                title=title,
                summary="Пик эмоций и ясности. Хорошо завершать, видеть результат, не перегревать конфликты.",
                priority=90 - int(abs(diff - 180) / 4),
                timezone="UTC",
            ))

    def _check_moon_voc(self, items: list[TodayImportantEvent], transits: dict, signals: list[AstroSignal], tz: str):
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
            
            from zoneinfo import ZoneInfo
            try:
                user_tz = ZoneInfo(tz)
            except Exception:
                user_tz = ZoneInfo("UTC")
            now = datetime.now(user_tz)
            
            starts_at_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            ends_at_dt = now + timedelta(hours=hours_to_next)
            
            local_time_label = f"до {ends_at_dt.strftime('%H:%M')}"
            
            items.append(TodayImportantEvent(
                id="moon_voc",
                kind="void_moon",
                tone="caution",
                title="Луна без курса",
                summary="Лучше не запускать новое и не принимать решения на спешке. Подходит для завершения, рутины и отдыха.",
                starts_at=starts_at_dt.isoformat(),
                ends_at=ends_at_dt.isoformat(),
                local_time_label=local_time_label,
                timezone=tz,
                priority=85,
            ))

    def _check_mercury(self, items: list[TodayImportantEvent], transits: dict, tz: str):
        transit_planets = transits.get("planets", [])
        mercury = self._find_planet(transit_planets, "Mercury")
        if not mercury:
            return

        speed = mercury.get("speed", 1.0)
        is_retro = speed < 0.0
        abs_speed = abs(speed)
        is_station = abs_speed < 0.05

        if is_station:
            items.append(TodayImportantEvent(
                id="mercury_station",
                kind="mercury_station",
                tone="caution",
                title="Меркурий разворачивается",
                summary="Самая нестабильная точка периода: больше путаницы, задержек и пересмотров.",
                priority=80,
                timezone=tz,
            ))
        elif is_retro:
            items.append(TodayImportantEvent(
                id="mercury_retrograde",
                kind="mercury_retrograde",
                tone="caution",
                title="Меркурий ретроградный",
                summary="Проверяй договорённости, документы, технику и сообщения. Лучше перепроверить детали.",
                priority=75,
                timezone=tz,
            ))

    def _check_moon_quarter(self, items: list[TodayImportantEvent], transits: dict, tz: str):
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        moon = self._find_planet(transit_planets, "Moon")
        if not sun or not moon:
            return

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        diff = (moon_lon - sun_lon) % 360

        is_first = abs(diff - 90) <= 12
        is_last = abs(diff - 270) <= 12

        if is_first:
            items.append(TodayImportantEvent(
                id="first_quarter",
                kind="moon_quarter",
                tone="neutral_shift",
                title="Первая четверть Луны",
                summary="День действия и проверки намерений. Может быть напряжение между желанием и реальностью.",
                priority=50,
                timezone=tz,
            ))
        elif is_last:
            items.append(TodayImportantEvent(
                id="last_quarter",
                kind="moon_quarter",
                tone="neutral_shift",
                title="Последняя четверть Луны",
                summary="День корректировки и освобождения от лишнего. Лучше завершать, чем начинать.",
                priority=50,
                timezone=tz,
            ))

    def _check_sun_ingress(self, items: list[TodayImportantEvent], transits: dict, tz: str):
        transit_planets = transits.get("planets", [])
        sun = self._find_planet(transit_planets, "Sun")
        if not sun:
            return

        sun_lon = sun.get("longitude", 0)
        if (sun_lon % 30) < 1.0:
            sign_idx = int(sun_lon / 30)
            sign_ru = {
                0: "Овен", 1: "Телец", 2: "Близнецы", 3: "Рак",
                4: "Лев", 5: "Дева", 6: "Весы", 7: "Скорпион",
                8: "Стрелец", 9: "Козерог", 10: "Водолей", 11: "Рыбы"
            }.get(sign_idx, "новый знак")

            items.append(TodayImportantEvent(
                id="sun_ingress",
                kind="sun_ingress",
                tone="neutral_shift",
                title=f"Солнце входит в {sign_ru}",
                summary="Меняется общий фокус месяца. День подходит, чтобы заметить новую тему и перестроить планы.",
                priority=60,
                timezone=tz,
            ))

    def _check_fast_planet_aspects(self, items: list[TodayImportantEvent], signals: list[AstroSignal], tz: str):
        caution_whitelist = [
            ({"Mercury", "Neptune"}, "square"),
            ({"Venus", "Saturn"}, "square"),
            ({"Mars", "Saturn"}, "square"),
            ({"Sun", "Mars"}, "square"),
            ({"Mercury", "Uranus"}, "opposition"),
            ({"Venus", "Pluto"}, "opposition"),
            ({"Mars", "Pluto"}, "square"),
        ]
        
        supportive_whitelist = [
            ({"Sun", "Jupiter"}, "trine"),
            ({"Sun", "Jupiter"}, "sextile"),
            ({"Mercury", "Jupiter"}, "trine"),
            ({"Mercury", "Jupiter"}, "sextile"),
            ({"Venus", "Jupiter"}, "trine"),
            ({"Venus", "Jupiter"}, "sextile"),
            ({"Mars", "Jupiter"}, "trine"),
            ({"Mars", "Jupiter"}, "sextile"),
            ({"Venus", "Sun"}, "trine"),
            ({"Venus", "Sun"}, "sextile"),
            ({"Venus", "Sun"}, "conjunction"),
        ]

        for sig in signals:
            if sig.type != "aspect":
                continue
            if not sig.aspect_type or not sig.target_planet:
                continue

            p1_clean = _normalize_name(sig.planet)
            p2_clean = _normalize_name(sig.target_planet)
            pair = {p1_clean, p2_clean}

            # Check caution whitelist
            is_caution = False
            for w_pair, w_asp in caution_whitelist:
                if pair == w_pair and sig.aspect_type == w_asp:
                    is_caution = True
                    break

            if is_caution:
                p1_ru = _PLANET_NAMES_RU.get(p1_clean, p1_clean)
                p2_ru = _PLANET_NAMES_RU.get(p2_clean, p2_clean)
                asp_ru = _ASPECT_RU_NOMINATIVE.get(sig.aspect_type, sig.aspect_type)
                items.append(TodayImportantEvent(
                    id=f"aspect_{p1_clean.lower()}_{p2_clean.lower()}",
                    kind="fast_planet_aspect",
                    tone="caution",
                    title=f"{p1_ru} {asp_ru} {p2_ru}",
                    summary="Осторожнее с резкими решениями, конфликтами и обещаниями. Лучше перепроверить детали.",
                    priority=70,
                    timezone=tz,
                ))
                continue

            # Check supportive whitelist
            is_supportive = False
            for w_pair, w_asp in supportive_whitelist:
                if pair == w_pair and sig.aspect_type == w_asp:
                    is_supportive = True
                    break

            if is_supportive:
                p1_ru = _PLANET_NAMES_RU.get(p1_clean, p1_clean)
                p2_ru = _PLANET_NAMES_RU.get(p2_clean, p2_clean)
                asp_ru = _ASPECT_RU_NOMINATIVE.get(sig.aspect_type, sig.aspect_type)
                items.append(TodayImportantEvent(
                    id=f"aspect_{p1_clean.lower()}_{p2_clean.lower()}",
                    kind="fast_planet_aspect",
                    tone="supportive",
                    title=f"{p1_ru} {asp_ru} {p2_ru}",
                    summary="Хорошее окно для переговоров, поддержки, знакомств, денег или продвижения дел.",
                    priority=65,
                    timezone=tz,
                ))

    @staticmethod
    def _find_planet(planets: list[dict], name: str | list[str]) -> dict | None:
        names = name if isinstance(name, list) else [name]
        for p in planets:
            if p.get("name") in names:
                return p
        return None


def _normalize_name(name: str) -> str:
    for prefix in ("Transit_", "Natal_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name
