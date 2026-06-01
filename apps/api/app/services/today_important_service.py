# AI_HEADER
# module: M-TODAY-IMPORTANT-SERVICE
# purpose: Calculate "Today Important" items — VOC, retrograde, moon phase, eclipse, active house

from datetime import date as Date, datetime, timedelta
from typing import Any

from app.schemas.normalization import AstroSignal


PLANET_NAMES_RU = {
    "Mercury": "Меркурий", "Venus": "Венера", "Mars": "Марс",
    "Jupiter": "Юпитер", "Saturn": "Сатурн", "Uranus": "Уран",
    "Neptune": "Нептун", "Pluto": "Плутон",
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
    """Calculate 'Today Important' items from live astro data."""

    def __init__(
        self,
        transits: dict,
        natal: dict,
        signals: list[AstroSignal],
        scoring_result: dict,
        user_tz: str,
    ):
        self.transits = transits
        self.natal = natal
        self.signals = signals
        self.scoring = scoring_result
        self.user_tz = user_tz
        self.items: list[dict] = []

    def compute(self) -> list[dict]:
        self._check_eclipse()
        self._check_moon_phase()
        self._check_moon_voc()
        self._check_retrogrades()
        self._check_stations()
        self._check_ingresses()
        self._check_active_house()

        # Sort by priority (lower = higher)
        self.items.sort(key=lambda x: x["priority"])
        return self.items[:3]

    # ── Moon Void of Course ──────────────────────────────────────

    def _check_moon_voc(self):
        """Check if Moon is void of course today."""
        transit_planets = self.transits.get("planets", [])
        moon = next((p for p in transit_planets if p.get("name") == "Moon"), None)
        if not moon:
            return

        moon_lon = moon.get("longitude", 0)
        moon_sign_idx = int(moon_lon / 30)
        next_sign_start = (moon_sign_idx + 1) * 30

        # Check for major aspects to other planets before next sign
        moon_aspects = [
            s for s in self.signals
            if s.type == "aspect" and s.planet and "Moon" in s.planet
        ]
        
        last_aspect_lon = 0
        for s in moon_aspects:
            if s.orb and s.strength:
                last_aspect_lon = max(last_aspect_lon, moon_lon)

        # VOC: Moon won't make any more major aspects in current sign
        # Simplified check: if no moon aspects → likely VOC
        if not moon_aspects:
            moon_speed = abs(moon.get("speed", 13))
            degrees_to_next = next_sign_start - moon_lon
            if degrees_to_next < 0:
                degrees_to_next += 360
            hours_to_next = degrees_to_next / moon_speed
            end_time = datetime.now().replace(tzinfo=None) + timedelta(hours=hours_to_next)
            
            self.items.append({
                "id": "moon_voc",
                "type": "moon_void",
                "title": f"Луна без курса до {end_time.strftime('%H:%M')}",
                "subtitle": "Новые старты дают смазанный отклик",
                "severity": "soft_warning",
                "planet": "Moon",
                "ends_at": end_time.isoformat(),
                "priority": 3,
                "source": "live_calculation",
            })

    # ── Retrogrades ──────────────────────────────────────────────

    def _check_retrogrades(self):
        """Check for retrograde planets (especially Mercury)."""
        transit_planets = self.transits.get("planets", [])
        retro_planets = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

        for name in retro_planets:
            planet = next((p for p in transit_planets if p.get("name") == name), None)
            if planet and (planet.get("speed", 0) < 0):
                ru_name = PLANET_NAMES_RU.get(name, name)
                subtitle = RETROGRADE_DESCRIPTIONS.get(ru_name, "Требует пересмотра")
                
                item: dict[str, Any] = {
                    "id": f"retro_{name.lower()}",
                    "type": "retrograde",
                    "title": f"{ru_name} ретрограден",
                    "subtitle": subtitle,
                    "severity": "warning" if name == "Mercury" else "soft_warning",
                    "planet": ru_name,
                    "days_remaining": None,
                    "priority": 4 if name == "Mercury" else 7,
                    "source": "live_calculation",
                }

                # Estimate days remaining
                abs_speed = abs(planet.get("speed", 0.03))
                if abs_speed > 0:
                    # Rough estimate: retrograde periods vary
                    item["days_remaining"] = max(1, int(15 / (abs_speed * 10)))
                    item["title"] = f"{ru_name} ретрограден · ещё {item['days_remaining']} дней"

                if name == "Mercury":
                    item["priority"] = 4
                
                self.items.append(item)

    # ── New Moon / Full Moon ─────────────────────────────────────

    def _check_moon_phase(self):
        """Check for new moon or full moon."""
        transit_planets = self.transits.get("planets", [])
        sun = next((p for p in transit_planets if p.get("name") == "Sun"), None)
        moon = next((p for p in transit_planets if p.get("name") == "Moon"), None)
        if not sun or not moon:
            return

        sun_lon = sun.get("longitude", 0)
        moon_lon = moon.get("longitude", 0)
        diff = abs(moon_lon - sun_lon) % 360

        # New moon: 0° ± 12° (≈1 day)
        if diff < 12 or diff > 348:
            self.items.append({
                "id": "new_moon",
                "type": "new_moon",
                "title": "Новолуние сегодня",
                "subtitle": "День перезапуска, но лучше не форсировать старт",
                "severity": "info",
                "priority": 2,
                "source": "live_calculation",
            })
        # Full moon: 180° ± 12°
        elif 168 < diff < 192:
            self.items.append({
                "id": "full_moon",
                "type": "full_moon",
                "title": "Полнолуние сегодня",
                "subtitle": "Эмоции и важные темы проявляются ярче",
                "severity": "info",
                "priority": 2,
                "source": "live_calculation",
            })

    # ── Eclipse ──────────────────────────────────────────────────

    def _check_eclipse(self):
        """Check for eclipse conditions (moon near nodes)."""
        transit_planets = self.transits.get("planets", [])
        moon = next((p for p in transit_planets if p.get("name") == "Moon"), None)
        north_node = next((p for p in transit_planets if p.get("name") in ("NORTH_NODE_TRUE", "NORTH_NODE")), None)
        
        if not moon or not north_node:
            return

        moon_lon = moon.get("longitude", 0)
        node_lon = north_node.get("longitude", 0)
        dist_to_north = abs(moon_lon - node_lon) % 360
        dist_to_south = abs(moon_lon - (node_lon + 180)) % 360
        min_dist = min(dist_to_north, dist_to_south)

        if min_dist < 18:
            sun = next((p for p in transit_planets if p.get("name") == "Sun"), None)
            sun_lon = sun.get("longitude", 0) if sun else 0
            sun_node_dist = min(abs(sun_lon - node_lon) % 360, abs(sun_lon - node_lon - 180) % 360)
            
            if sun_node_dist < 18:
                self.items.append({
                    "id": "eclipse",
                    "type": "eclipse",
                    "title": "Затменный фон",
                    "subtitle": "Не форсируй резкие решения — события могут иметь длинный хвост",
                    "severity": "high_attention",
                    "priority": 1,
                    "source": "live_calculation",
                })

    # ── Active House ─────────────────────────────────────────────

    def _check_active_house(self):
        """Find the most active house of the day."""
        main_house = None

        # 1. From main signal
        top_signals = self.scoring.get("top_signals", [])
        for s in top_signals[:1]:
            if s.house:
                main_house = s.house
                break

        # 2. Fallback: house of transit Moon
        if not main_house:
            transit_planets = self.transits.get("planets", [])
            moon = next((p for p in transit_planets if p.get("name") == "Moon"), None)
            if moon:
                main_house = int(moon.get("longitude", 0) / 30) + 1

        if not main_house:
            return

        meaning = HOUSE_MEANINGS_RU.get(main_house, f"Акцент на {main_house} доме")
        self.items.append({
            "id": "active_house",
            "type": "active_house",
            "title": f"Активен {main_house} дом",
            "subtitle": meaning,
            "severity": "info",
            "house": main_house,
            "priority": 6,
            "source": "live_calculation",
        })

    # ── Planet Stations ──────────────────────────────────────────

    def _check_stations(self):
        """Check for planetary stations (near-zero speed)."""
        transit_planets = self.transits.get("planets", [])
        for p in transit_planets:
            name = p.get("name", "")
            if name in ("Sun", "Moon"):
                continue
            speed = abs(p.get("speed", 1))
            if speed < 0.02:  # near stationary
                ru_name = PLANET_NAMES_RU.get(name, name)
                self.items.append({
                    "id": f"station_{name.lower()}",
                    "type": "station",
                    "title": f"{ru_name} разворачивается",
                    "subtitle": "Тема планеты становится заметнее и требует паузы",
                    "severity": "soft_warning",
                    "planet": ru_name,
                    "priority": 5,
                    "source": "live_calculation",
                })

    # ── Ingresses ────────────────────────────────────────────────

    def _check_ingresses(self):
        """Check for planet ingresses (near sign boundary)."""
        transit_planets = self.transits.get("planets", [])
        signs = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
                 "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]

        for p in transit_planets:
            name = p.get("name", "")
            if name in ("Sun", "Moon"):
                continue
            lon = p.get("longitude", 0)
            deg_in_sign = lon % 30
            speed = p.get("speed", 0)
            
            # Just entered (within 2° of sign start with positive speed)
            if deg_in_sign < 2 and speed > 0:
                sign_idx = int(lon / 30) % 12
                ru_name = PLANET_NAMES_RU.get(name, name)
                self.items.append({
                    "id": f"ingress_{name.lower()}",
                    "type": "ingress",
                    "title": f"{ru_name} входит в {signs[sign_idx]}",
                    "subtitle": "Меняется стиль проявления темы дня",
                    "severity": "info",
                    "planet": ru_name,
                    "sign": signs[sign_idx],
                    "priority": 8,
                    "source": "live_calculation",
                })
                break  # Only show one ingress max
