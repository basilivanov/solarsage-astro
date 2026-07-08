# ############################################################################
# AI_HEADER: MODULE_LUNAR_FACTS_SERVICE
# ROLE: Backend-owned lunar facts helper for calendar/day consumers.
# ############################################################################

# START_MODULE_CONTRACT: M-LUNAR-FACTS-SERVICE
# purpose: Compute stable lunar read-model facts on the backend so frontend
#   calendar UI can render lunar presentation without astrological calculations.
# owns:
#   - apps/api/app/services/lunar_facts_service.py
# inputs:
#   - target_date: datetime.date
# outputs:
#   - CalendarLunarFields with phase key/index/labels, illumination, moon sign,
#     lunar day, and void-of-course boolean.
# dependencies:
#   - math, datetime, app.schemas.calendar
# side_effects: none
# emitted_logs: none
# invariants:
#   - phase_index is always 0..7.
#   - illumination is a 0..100 percentage.
#   - lunar_day is always 1..30.
#   - void_of_course false means computed-not-void; null is reserved for unknown.
# failure_policy:
#   - deterministic pure calculation; unexpected errors should propagate to caller.
# non_goals:
#   - Swiss Ephemeris precision. This service is versioned and can be replaced
#     by SolarSage longitude-backed facts without changing frontend semantics.
# END_MODULE_CONTRACT: M-LUNAR-FACTS-SERVICE

# START_MODULE_MAP: M-LUNAR-FACTS-SERVICE
# public_entrypoints:
#   - LunarFactsService.facts_for_date
# semantic_blocks:
#   - LUNAR_APPROXIMATION: documented backend-side approximation
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py
# END_MODULE_MAP: M-LUNAR-FACTS-SERVICE

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date as Date, datetime
from math import cos, floor, pi

from app.schemas.calendar import CalendarLunarFields


LUNAR_FACTS_VERSION = "mean-synodic-v1"
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)
SYNODIC_MONTH_DAYS = 29.530588853

PHASES: tuple[tuple[str, str, str], ...] = (
    ("new_moon", "новолуние", "Новолуние"),
    ("waxing_crescent", "раст. серп", "Растущий серп"),
    ("first_quarter", "перв. четв.", "Первая четверть"),
    ("waxing_gibbous", "раст. Луна", "Растущая Луна"),
    ("full_moon", "полнолуние", "Полнолуние"),
    ("waning_gibbous", "убыв. Луна", "Убывающая Луна"),
    ("last_quarter", "посл. четв.", "Последняя четверть"),
    ("waning_crescent", "убыв. серп", "Убывающий серп"),
)

MOON_SIGNS: tuple[tuple[str, str], ...] = (
    ("Aries", "Овен"),
    ("Taurus", "Телец"),
    ("Gemini", "Близнецы"),
    ("Cancer", "Рак"),
    ("Leo", "Лев"),
    ("Virgo", "Дева"),
    ("Libra", "Весы"),
    ("Scorpio", "Скорпион"),
    ("Sagittarius", "Стрелец"),
    ("Capricorn", "Козерог"),
    ("Aquarius", "Водолей"),
    ("Pisces", "Рыбы"),
)


@dataclass(frozen=True)
class LunarPosition:
    age_days: float
    cycle_fraction: float
    illumination: int
    phase_index: int
    sign_index: int
    moon_longitude_in_sign: float


# START_BLOCK: LUNAR_APPROXIMATION
class LunarFactsService:
    """Backend-owned lunar facts service.

    The current implementation uses a documented mean-synodic-month
    approximation at noon UTC for each civil date. It is intentionally located
    in the API layer, not the frontend, so a future SolarSage/Swiss-Ephemeris
    replacement can keep the same wire contract.
    """

    def facts_for_date(self, target_date: Date) -> CalendarLunarFields:
        # START_FUNCTION_CONTRACT: F-M-LUNAR-FACTS-SERVICE.facts_for_date
        # purpose: Build CalendarLunarFields for one calendar date.
        # inputs: target_date — civil date to evaluate at 12:00 UTC.
        # returns: CalendarLunarFields — populated lunar contract fields.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises only for unexpected arithmetic/runtime errors.
        # END_FUNCTION_CONTRACT: F-M-LUNAR-FACTS-SERVICE.facts_for_date
        position = self._position_for_date(target_date)
        phase_key, phase_label, _phase_long_label = PHASES[position.phase_index]
        moon_sign, moon_sign_label = MOON_SIGNS[position.sign_index]

        return CalendarLunarFields(
            phase=phase_key,
            phase_index=position.phase_index,
            phase_label=phase_label,
            illumination=float(position.illumination),
            moon_sign=moon_sign,
            moon_sign_label=moon_sign_label,
            lunar_day=min(30, floor(position.age_days) + 1),
            void_of_course=position.moon_longitude_in_sign >= 28.0,
        )

    def _position_for_date(self, target_date: Date) -> LunarPosition:
        sample = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            12,
            0,
            tzinfo=UTC,
        )
        age_days = ((sample - NEW_MOON_EPOCH).total_seconds() / 86400.0) % SYNODIC_MONTH_DAYS
        cycle_fraction = age_days / SYNODIC_MONTH_DAYS
        illumination = round(((1 - cos(2 * pi * cycle_fraction)) / 2) * 100)
        phase_index = self._phase_index(cycle_fraction, illumination)
        sign_index = int(((age_days / SYNODIC_MONTH_DAYS) * 12 + 3) % 12)
        moon_longitude_in_sign = ((age_days / SYNODIC_MONTH_DAYS) * 360) % 30

        return LunarPosition(
            age_days=age_days,
            cycle_fraction=cycle_fraction,
            illumination=illumination,
            phase_index=phase_index,
            sign_index=sign_index,
            moon_longitude_in_sign=moon_longitude_in_sign,
        )

    @staticmethod
    def _phase_index(cycle_fraction: float, illumination: int) -> int:
        if illumination < 2:
            return 0 if cycle_fraction < 0.5 else 4
        if illumination >= 98:
            return 4
        if 48 <= illumination <= 52:
            return 2 if cycle_fraction < 0.5 else 6
        if cycle_fraction < 0.25:
            return 1
        if cycle_fraction < 0.5:
            return 3
        if cycle_fraction < 0.75:
            return 5
        return 7
# END_BLOCK: LUNAR_APPROXIMATION
