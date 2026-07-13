# ############################################################################
# AI_HEADER: HORIZON_GUIDANCE_FORMATTER — pure deterministic Russian display formatting.
# ROLE: Formats timing, entity labels, and manifestation splits for the B2B2 guidance service.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-GUIDANCE-FORMATTER
# purpose: Provide pure/stateless formatting helpers consumed only by
#          HorizonGuidanceService and HorizonGuidanceBuilders. Loads the cached
#          language canon for templates but never mutates process state.
# owns:
#   - apps/api/app/services/horizon_guidance_formatter.py
# inputs: Raw B2A timing strings, entity keys, product-sphere bodies, canon
#         language bundle.
# outputs: Formatted Russian display strings, typed HorizonTimingPresentation,
#          and manifestation split results.
# dependencies: datetime/zoneinfo/re stdlib, B2B content canon service, B2B1 schemas.
# side_effects: reads cached content canon only.
# emitted_logs: none.
# invariants:
#   - No settings, locale process mutation, or wall clock.
#   - Every public method is deterministic given the same inputs and same loaded canon.
# failure_policy: raises HorizonGuidanceError.
# END_MODULE_CONTRACT: M-HORIZON-GUIDANCE-FORMATTER

# START_MODULE_MAP: M-HORIZON-GUIDANCE-FORMATTER
# public_entrypoints:
#   - format_timing
#   - planet_label
#   - angle_label
#   - lot_label
#   - target_label
#   - source_label
#   - entity_display
#   - split_manifestation
# semantic_blocks:
#   - FORMATTER_TABLES: static planet/angle/lot/month display maps.
#   - FORMATTER_SERVICE: timing, entity label, and manifestation formatting.
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_formatter.py
# END_MODULE_MAP: M-HORIZON-GUIDANCE-FORMATTER

# START_BLOCK: FORMATTER_TABLES
from __future__ import annotations

import datetime as _dt
import re
from functools import cached_property
from zoneinfo import ZoneInfo

from app.schemas.horizon_content_canon import HorizonContentCanonBundle
from app.schemas.horizon_guidance import (
    HorizonGuidanceError,
    HorizonTimingPresentation,
)
from app.schemas.horizon_selection import HorizonTimingAssessment
from app.schemas.today_horizons import (
    TodayV2HorizonId,
    TodayV2HorizonTiming,
)
from app.services.horizon_content_canon_service import load_horizon_content_canons

_PREFIX_RE = re.compile(r"^(?:Transit_|Natal_)+", re.IGNORECASE)
_RFC3339_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?"
    r"(Z|[+-]\d{2}:\d{2})$"
)

PLANET_LABELS: dict[str, str] = {
    "SUN": "Солнце",
    "MOON": "Луна",
    "MERCURY": "Меркурий",
    "VENUS": "Венера",
    "MARS": "Марс",
    "JUPITER": "Юпитер",
    "SATURN": "Сатурн",
    "URANUS": "Уран",
    "NEPTUNE": "Нептун",
    "PLUTO": "Плутон",
    "CHIRON": "Хирон",
    "NORTH_NODE": "Северный узел",
    "SOUTH_NODE": "Южный узел",
}

ANGLE_LABELS: dict[str, str] = {
    "ASC": "Асцендент",
    "DSC": "Десцендент",
    "MC": "Меридиан MC",
    "IC": "Надир IC",
}

LOT_LABELS: dict[str, str] = {
    "FORTUNE": "Жребий Фортуны",
    "SPIRIT": "Жребий Духа",
    "EROS": "Жребий Эроса",
    "MARRIAGE": "Жребий Брака",
    "NECESSITY": "Жребий Необходимости",
    "VICTORY": "Жребий Победы",
    "NEMESIS": "Жребий Немезиды",
}

_MONTH_GENITIVE: dict[int, str] = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

_SUFFIX_MAP: dict[str, str] = {
    "Europe/Moscow": "по Москве",
    "UTC": "UTC",
}


# END_BLOCK: FORMATTER_TABLES


# START_BLOCK: FORMATTER_SERVICE
class HorizonGuidanceFormatter:
    """Pure stateless formatter for timing, entity labels, and manifestation splits.

    Loads the cached language canon once per instance for template access.
    """

    def __init__(self) -> None:
        self._bundle: HorizonContentCanonBundle | None = None

    @cached_property
    def bundle(self) -> HorizonContentCanonBundle:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.bundle
        # purpose: Lazy-load content canons once per formatter instance.
        # inputs: self.
        # returns: HorizonContentCanonBundle.
        # side_effects: reads canons from disk on first access.
        # emitted_logs: none.
        # error_behavior: propagates file/parse errors from canon loader.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.bundle
        if self._bundle is None:
            self._bundle = load_horizon_content_canons()
        return self._bundle

    # -- Timing formatting --

    def format_timing(
        self,
        *,
        horizon: TodayV2HorizonId,
        timing: HorizonTimingAssessment,
    ) -> HorizonTimingPresentation:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.format_timing
        # purpose: Build typed HorizonTimingPresentation from raw anchor timing.
        #          Validates timezone/date/instant before formatting.
        # inputs: horizon - horizon id; timing - raw B2A timing assessment.
        # returns: HorizonTimingPresentation with all labels.
        # side_effects: reads cached canon.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError with structural code and
        #   path; never includes raw input value in error string.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.format_timing
        tz = self._ensure_timezone(timing.timezone)
        canon = self.bundle.language
        templates = canon.timing_templates
        state = timing.timing_state or "background"
        state_label = canon.timing_state_labels.get(state, "")
        if not state_label:
            raise HorizonGuidanceError("invalid_timing_value", "timing.state")

        tz_suffix = self._format_timezone_suffix(timing.timezone)

        precision = timing.precision or "date"
        active_from = timing.active_from or ""
        active_until = timing.active_until or ""

        if precision == "date":
            from_disp = self._validate_date_label(active_from)
            until_disp = self._validate_date_label(active_until)
            range_label = templates.get("range", "{active_from} — {active_until}")
            range_label = range_label.replace("{active_from}", from_disp)
            range_label = range_label.replace("{active_until}", until_disp)
            peak_label = self._build_peak_label(
                timing.exact_at, precision, tz, templates, tz_suffix
            )
            valid_until_label = self._build_valid_until(
                horizon, templates, until_disp
            )
        elif precision == "instant":
            from_disp = self._validate_instant_label(active_from, tz)
            until_disp = self._validate_instant_label(active_until, tz)
            range_label = templates.get("range", "{active_from} — {active_until}")
            range_label = range_label.replace("{active_from}", from_disp)
            range_label = range_label.replace("{active_until}", until_disp)
            if tz_suffix:
                range_label = f"{range_label} {tz_suffix}"
            peak_label = self._build_peak_label(
                timing.exact_at, precision, tz, templates, tz_suffix
            )
            valid_until_label = self._build_valid_until(
                horizon, templates, until_disp
            )
        else:
            raise HorizonGuidanceError(
                "invalid_timing_value", "timing.precision"
            )

        active_from_label = from_disp
        active_until_label = until_disp
        exact_at_label: str | None = None
        if timing.exact_at:
            if precision == "date":
                exact_at_label = self._validate_date_label(timing.exact_at)
            else:
                exact_at_label = self._validate_instant_label(timing.exact_at, tz)

        _peak_label_val: str | None = peak_label
        public_timing = TodayV2HorizonTiming(
            active_from=active_from,
            exact_at=timing.exact_at,
            active_until=active_until,
            precision=precision,  # type: ignore
            state=state,  # type: ignore
            range_label=range_label,
            peak_label=_peak_label_val,
            state_label=state_label,
            timezone=timing.timezone,
        )

        return HorizonTimingPresentation(
            public_timing=public_timing,
            active_from_label=active_from_label,
            active_until_label=active_until_label,
            exact_at_label=exact_at_label,
            valid_until_label=valid_until_label,
            timezone_suffix=tz_suffix,
        )

    def _ensure_timezone(self, timezone: str) -> ZoneInfo:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._ensure_timezone
        # purpose: Validate and return ZoneInfo for a given IANA timezone string.
        # inputs: timezone - IANA timezone string.
        # returns: ZoneInfo instance.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=invalid_timezone;
        #   never exposes raw ZoneInfo exception or body.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._ensure_timezone
        try:
            return ZoneInfo(timezone)
        except (KeyError, TypeError, OSError):
            raise HorizonGuidanceError(
                "invalid_timezone", "anchor.timing.timezone"
            )

    def _validate_date_label(self, value: str) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._validate_date_label
        # purpose: Validate an ISO date string via date.fromisoformat and
        #          format as Russian genitive.
        # inputs: value - YYYY-MM-DD string.
        # returns: Russian genitive date label.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=invalid_timing_value;
        #   never exposes raw value.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._validate_date_label
        try:
            d = _dt.date.fromisoformat(value)
        except (ValueError, TypeError):
            raise HorizonGuidanceError(
                "invalid_timing_value", "anchor.timing"
            )
        genitive = _MONTH_GENITIVE.get(d.month)
        if not genitive:
            raise HorizonGuidanceError("invalid_timing_value", "anchor.timing")
        return f"{d.day} {genitive} {d.year}"

    def _validate_instant_label(self, value: str, tz: ZoneInfo) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._validate_instant_label
        # purpose: Validate an RFC 3339 instant string and format as local
        #          Russian display.
        # inputs: value - RFC 3339 string; tz - validated ZoneInfo.
        # returns: Local date/time Russian display without timezone suffix.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=invalid_timing_value;
        #   never exposes raw value.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER._validate_instant_label
        m = _RFC3339_RE.match(value)
        if not m:
            raise HorizonGuidanceError(
                "invalid_timing_value", "anchor.timing"
            )
        try:
            dt = _dt.datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6)),
                tzinfo=_dt.timezone.utc,
            )
            if m.group(7) != "Z":
                offset_str = m.group(7)
                sign = 1 if offset_str[0] == "+" else -1
                hours = int(offset_str[1:3])
                minutes = int(offset_str[4:6])
                offset = _dt.timedelta(
                    hours=sign * hours, minutes=sign * minutes
                )
                dt = dt.replace(tzinfo=_dt.timezone(offset))
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                raise HorizonGuidanceError(
                    "invalid_timing_value", "anchor.timing"
                )
        except (ValueError, OverflowError):
            raise HorizonGuidanceError(
                "invalid_timing_value", "anchor.timing"
            )
        local_dt = dt.astimezone(tz)
        genitive = _MONTH_GENITIVE.get(local_dt.month, "")
        return (
            f"{local_dt.day} {genitive} {local_dt.year}, "
            f"{local_dt.hour:02d}:{local_dt.minute:02d}"
        )

    def _build_peak_label(
        self,
        exact_at: str | None,
        precision: str,
        tz: ZoneInfo,
        templates: dict[str, str],
        tz_suffix: str,
    ) -> str | None:
        if exact_at is None:
            return None
        if precision == "date":
            display = self._validate_date_label(exact_at)
            return display
        display = self._validate_instant_label(exact_at, tz)
        template = templates.get("peak", "{exact_at}")
        result = template.replace("{exact_at}", display)
        if tz_suffix:
            result = f"{result} {tz_suffix}"
        return result

    def _build_valid_until(
        self,
        horizon: TodayV2HorizonId,
        templates: dict[str, str],
        until_display: str,
    ) -> str:
        key = {
            "long": "long_valid_until",
            "medium": "valid_until",
            "fast": "fast_eases",
        }[horizon]
        template = templates.get(key, "")
        if not template:
            raise HorizonGuidanceError(
                "invalid_timing_value", "timing.valid_until_template"
            )
        result = template.replace("{active_until}", until_display)
        if "{active_until}" in result:
            raise HorizonGuidanceError(
                "invalid_timing_value", "timing.valid_until_template"
            )
        return result

    def _format_timezone_suffix(self, timezone: str) -> str:
        if timezone in _SUFFIX_MAP:
            return _SUFFIX_MAP[timezone]
        return f"({timezone})"

    # -- Entity labels --

    def planet_label(self, key: str) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.planet_label
        # purpose: Look up Russian planet label.
        # inputs: key - uppercase planet code (SUN, MOON, …).
        # returns: Russian string, or "" for unknown.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: returns "" for unknown keys; caller decides.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.planet_label
        return PLANET_LABELS.get(key, "")

    def angle_label(self, key: str) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.angle_label
        # purpose: Look up Russian angle label.
        # inputs: key - uppercase angle code (ASC, DSC, MC, IC).
        # returns: Russian string, or "" for unknown.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: returns "" for unknown keys; caller decides.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.angle_label
        return ANGLE_LABELS.get(key, "")

    def lot_label(self, key: str) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.lot_label
        # purpose: Look up Russian lot label.
        # inputs: key - uppercase lot code (FORTUNE, SPIRIT, …).
        # returns: Russian string, or "" for unknown.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: returns "" for unknown keys; caller decides.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.lot_label
        return LOT_LABELS.get(key, "")

    def target_label(
        self, target_type: str, target_key: str
    ) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.target_label
        # purpose: Format a human-safe target label for technique explanations.
        # inputs: target_type - planet|angle|lot|house|sphere;
        #         target_key - raw machine key.
        # returns: Russian display string.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=unknown_entity_label
        #   for unknown planet/angle or unreachable sphere. House rejects
        #   values outside 1..12. Unknown lot returns safe generic. Missing
        #   transit source raises unsupported_entity_label.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.target_label
        if target_type == "planet":
            label = self.planet_label(target_key)
            if not label:
                raise HorizonGuidanceError(
                    "unsupported_entity_label", "planet"
                )
            return f"ваш натальный {label}"
        elif target_type == "angle":
            label = self.angle_label(target_key)
            if not label:
                raise HorizonGuidanceError(
                    "unsupported_entity_label", "angle"
                )
            return f"опорную точку {label}"
        elif target_type == "lot":
            label = self.lot_label(target_key)
            if label:
                return label
            return "расчётную точку карты"
        elif target_type == "house":
            try:
                hnum = int(target_key)
            except (ValueError, TypeError):
                raise HorizonGuidanceError(
                    "unsupported_entity_label", "house"
                )
            if hnum < 1 or hnum > 12:
                raise HorizonGuidanceError(
                    "unsupported_entity_label", "house"
                )
            return f"область карты №{hnum}"
        elif target_type == "sphere":
            canon = self.bundle.language
            sphere_label = canon.product_spheres.get(target_key, None)
            if sphere_label is None:
                raise HorizonGuidanceError(
                    "unsupported_entity_label", "sphere"
                )
            return f"сферу «{sphere_label.label}»"
        raise HorizonGuidanceError(
            "unknown_entity_label", "target_type"
        )

    def source_label(self, source_planet: str | None) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.source_label
        # purpose: Format a transit source planet label.
        # inputs: source_planet - raw planet key or None.
        # returns: Russian planet label when found.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=
        #   unsupported_entity_label on null/missing source; never defaults
        #   to generic "планета".
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.source_label
        if source_planet is None:
            raise HorizonGuidanceError(
                "unsupported_entity_label", "source_planet"
            )
        planet = _strip_prefix(source_planet)
        label = self.planet_label(planet)
        if not label:
            raise HorizonGuidanceError(
                "unsupported_entity_label",
                "source_planet",
            )
        return label

    def entity_display(self, key: str) -> str:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.entity_display
        # purpose: Display a planet/angle/lot key without Transit_/Natal_ prefix.
        # inputs: key - raw machine entity key.
        # returns: Russian label or raises on unknown.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError unsupported_entity_label.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.entity_display
        cleaned = _strip_prefix(key)
        label = PLANET_LABELS.get(cleaned)
        if label:
            return label
        label = ANGLE_LABELS.get(cleaned)
        if label:
            return label
        label = LOT_LABELS.get(cleaned)
        if label:
            return label
        raise HorizonGuidanceError(
            "unsupported_entity_label", "entity"
        )

    # -- Manifestation split --

    def split_manifestation(
        self,
        body: str,
        required_prefixes: tuple[str, ...],
    ) -> tuple[str, str]:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.split_manifestation
        # purpose: Split a conditional manifestation body into condition and body parts.
        # inputs: body - full conditional sentence starting with a required
        #         prefix; required_prefixes - loaded canon prefixes.
        # returns: (condition, body) tuple.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises HorizonGuidanceError code=
        #   invalid_manifestation_copy on missing comma, blank parts, or
        #   missing prefix.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-FORMATTER.split_manifestation
        comma_idx = body.find(",")
        if comma_idx == -1:
            raise HorizonGuidanceError(
                "invalid_manifestation_copy", "manifestation.body"
            )
        condition = body[:comma_idx].strip()
        tail = body[comma_idx + 1:].strip()
        if not condition or not tail:
            raise HorizonGuidanceError(
                "invalid_manifestation_copy", "manifestation.body"
            )
        if not any(condition.startswith(prefix) for prefix in required_prefixes):
            raise HorizonGuidanceError(
                "invalid_manifestation_copy",
                "manifestation.condition",
            )
        body_part = tail[0].upper() + tail[1:] if tail else tail
        return condition, body_part


# END_BLOCK: FORMATTER_SERVICE


def _strip_prefix(key: str) -> str:
    return _PREFIX_RE.sub("", key)


__all__ = ["HorizonGuidanceFormatter"]
