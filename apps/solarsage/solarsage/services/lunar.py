# ############################################################################
# AI_HEADER: MODULE_SERVICES_LUNAR
# ROLE: Lunar window calculations via pyswisseph
# DEPENDENCIES: swisseph, local ephemeris
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Service for computing daily lunar details, VOC intervals, phase, and ingress.
# owns:
#   - apps/solarsage/solarsage/services/lunar.py
# inputs: date range
# outputs: list of LunarDayInfo
# dependencies: swisseph
# side_effects: calculation using ephemeris
# emitted_logs: n/a (pure)
# failure_policy: raises ValueError/RuntimeError
# END_MODULE_CONTRACT

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time, timedelta
import swisseph as swe

from ..schemas.lunar import LunarDayInfo, VocInterval

MOON_SIGNS = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

MOON_SIGNS_RU = {
    "aries": "Овен", "taurus": "Телец", "gemini": "Близнецы", "cancer": "Рак",
    "leo": "Лев", "virgo": "Дева", "libra": "Весы", "scorpio": "Скорпион",
    "sagittarius": "Стрелец", "capricorn": "Козерог", "aquarius": "Водолей", "pisces": "Рыбы"
}

# Major aspect angles and their orb thresholds (in degrees) for Moon VOC check:
# conj: 0° (12°), opp: 180° (12°), trine: 120° (10°), square: 90° (10°), sextile: 60° (8°)
ASPECT_ORBS = [
    (0.0, 12.0),
    (180.0, 12.0),
    (120.0, 10.0),
    (90.0, 10.0),
    (60.0, 8.0),
]

TARGET_PLANETS = [
    swe.SUN, swe.MERCURY, swe.VENUS, swe.MARS,
    swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO
]


def _datetime_to_jd(dt_utc: datetime) -> float:
    return swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )


def _jd_to_iso(jd: float) -> str:
    year, month, day, hour_float = swe.revjul(jd)
    hours = int(hour_float)
    rem_min = (hour_float - hours) * 60.0
    minutes = int(rem_min)
    seconds = int(round((rem_min - minutes) * 60.0))
    if seconds >= 60:
        seconds = 0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        hours += 1
    dt = datetime(year, month, day, hours % 24, minutes, seconds, tzinfo=UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_moon_voc_at_jd(jd: float) -> bool:
    """
    Check if Moon is Void of Course (VOC) at a specific Julian Day:
    True if Moon will make NO applying major aspect to Sun..Pluto before exiting its current sign.
    """
    res_m = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
    moon_lon = res_m[0][0]
    moon_speed = res_m[0][3]

    current_sign_index = int(moon_lon // 30)
    next_sign_boundary = (current_sign_index + 1) * 30.0

    # Distance to next sign boundary (degrees)
    dist_to_boundary = next_sign_boundary - moon_lon
    if dist_to_boundary <= 0:
        return False

    # Check each target planet
    for planet in TARGET_PLANETS:
        res_p = swe.calc_ut(jd, planet, swe.FLG_SWIEPH | swe.FLG_SPEED)
        p_lon = res_p[0][0]
        p_speed = res_p[0][3]

        rel_speed = moon_speed - p_speed
        if rel_speed <= 0:
            continue  # Moon is not applying to planet

        for aspect_angle, orb in ASPECT_ORBS:
            # We check target Moon positions where aspect occurs: (p_lon ± aspect_angle) % 360
            for sign_dir in (-1, 1):
                target_m_lon = (p_lon + sign_dir * aspect_angle) % 360
                # Move target_m_lon into current sign frame if needed
                # Distance from current moon_lon to target_m_lon (forward)
                forward_dist = (target_m_lon - moon_lon) % 360

                # Is it within the orb right now or applying before boundary?
                # 1) Current orb diff:
                angle_diff = abs((moon_lon - p_lon) % 360 - aspect_angle)
                angle_diff = min(angle_diff, 360 - angle_diff)

                if angle_diff <= orb and forward_dist < 180:
                    # Currently in orb — check if applying
                    # If forward_dist <= orb or applying towards exact aspect:
                    if forward_dist <= dist_to_boundary:
                        return False

                # 2) Future exact aspect before boundary:
                if 0 < forward_dist <= dist_to_boundary:
                    return False

    return True


class LunarService:
    def __init__(self) -> None:
        pass

    def compute_window(self, from_date: date, to_date: date) -> list[LunarDayInfo]:
        if (to_date - from_date).days > 62:
            raise ValueError("Maximum date range is 62 days")

        results: list[LunarDayInfo] = []
        curr_date = from_date

        while curr_date <= to_date:
            info = self.compute_day(curr_date)
            results.append(info)
            curr_date += timedelta(days=1)

        return results

    def compute_day(self, target_date: date) -> LunarDayInfo:
        # Noon UTC
        noon_dt = datetime.combine(target_date, time(12, 0, 0), tzinfo=UTC)
        jd_noon = _datetime_to_jd(noon_dt)

        res_moon = swe.calc_ut(jd_noon, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
        res_sun = swe.calc_ut(jd_noon, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
        res_merc = swe.calc_ut(jd_noon, swe.MERCURY, swe.FLG_SWIEPH | swe.FLG_SPEED)

        moon_lon_noon = res_moon[0][0]
        sun_lon_noon = res_sun[0][0]
        merc_speed_noon = res_merc[0][3]

        phase_angle = (moon_lon_noon - sun_lon_noon) % 360.0
        waxing = phase_angle < 180.0
        illumination = (1.0 - math.cos(math.radians(phase_angle))) / 2.0

        sign_idx = int(moon_lon_noon // 30)
        moon_sign = MOON_SIGNS[sign_idx]
        moon_sign_ru = MOON_SIGNS_RU[moon_sign]
        mercury_retro = merc_speed_noon < 0.0

        # Sign ingress check in this 24h day [00:00, 24:00)
        start_day_dt = datetime.combine(target_date, time(0, 0, 0), tzinfo=UTC)
        end_day_dt = datetime.combine(target_date, time(23, 59, 59), tzinfo=UTC)
        jd_start = _datetime_to_jd(start_day_dt)
        jd_end = _datetime_to_jd(end_day_dt)

        sign_ingress_iso: str | None = None
        try:
            # Next boundary multiple of 30°
            res_start = swe.calc_ut(jd_start, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SPEED)
            curr_deg = res_start[0][0]
            target_deg = ((int(curr_deg // 30) + 1) * 30) % 360
            cross_jd = swe.mooncross_ut(target_deg, jd_start)
            if jd_start <= cross_jd <= jd_end:
                sign_ingress_iso = _jd_to_iso(cross_jd)
        except Exception:
            pass

        # VOC Step-Scan: 288 steps (5-minute intervals)
        voc_steps: list[tuple[datetime, bool]] = []
        is_voc_noon = False

        for i in range(288):
            step_dt = start_day_dt + timedelta(minutes=5 * i)
            jd_step = _datetime_to_jd(step_dt)
            is_voc = _is_moon_voc_at_jd(jd_step)
            voc_steps.append((step_dt, is_voc))
            if i == 144:  # 12:00 UTC
                is_voc_noon = is_voc

        # Build voc_intervals
        voc_intervals: list[VocInterval] = []
        in_voc = False
        start_voc_dt: datetime | None = None

        for step_dt, is_voc in voc_steps:
            if is_voc and not in_voc:
                in_voc = True
                start_voc_dt = step_dt
            elif not is_voc and in_voc:
                in_voc = False
                end_voc_dt = step_dt
                if start_voc_dt is not None:
                    voc_intervals.append(
                        VocInterval(
                            start=start_voc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            end=end_voc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        )
                    )
                start_voc_dt = None

        if in_voc and start_voc_dt is not None:
            voc_intervals.append(
                VocInterval(
                    start=start_voc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    end=end_day_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            )

        voc_count = sum(1 for _, is_voc in voc_steps if is_voc)
        voc_fraction = round(voc_count / 288.0, 2)

        return LunarDayInfo(
            date=target_date.isoformat(),
            moon_sign=moon_sign,  # type: ignore
            moon_sign_ru=moon_sign_ru,
            moon_lon_noon=round(moon_lon_noon, 2),
            phase_angle=round(phase_angle, 2),
            waxing=waxing,
            illumination=round(illumination, 2),
            is_voc_noon=is_voc_noon,
            voc_intervals=voc_intervals,
            voc_fraction=voc_fraction,
            sign_ingress=sign_ingress_iso,
            mercury_retro=mercury_retro,
        )
