# ############################################################################
# AI_HEADER: MODULE_HORIZON_TIMING_SERVICE — pure timing classifier for B2A anchor eligibility.
# ROLE: Parse activation timing evidence against request target clock and return typed machine assessments.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-TIMING-SERVICE
# purpose: Classify one ActivationEvidence timing payload into deterministic timing state, eligibility, and warnings.
# owns:
#   - apps/api/app/services/horizon_timing_service.py
# inputs: ActivationEvidence plus request target_date/target_time/target_tz strings.
# outputs: HorizonTimingAssessment with no human/debug payloads.
# dependencies: datetime/re/zoneinfo stdlib, app.schemas.activation, app.schemas.horizon_selection, app.services.horizon_canon_service.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - no server clock/date/timezone calls.
#   - wire timing strings are preserved verbatim in the assessment.
#   - invalid evidence data returns an ineligible assessment instead of raising.
# failure_policy: invalid canon raises; invalid evidence or target clock returns typed ineligible assessment.
# END_MODULE_CONTRACT: M-HORIZON-TIMING-SERVICE

# START_MODULE_MAP: M-HORIZON-TIMING-SERVICE
# public_entrypoints:
#   - HorizonTimingService.classify
# semantic_blocks:
#   - HORIZON_TIMING_HELPERS: pure parsing and normalization helpers.
#   - HORIZON_TIMING_SERVICE: timing classification and horizon eligibility logic.
# owned_tests:
#   - apps/api/tests/test_horizon_timing_service.py
# END_MODULE_MAP: M-HORIZON-TIMING-SERVICE

# START_BLOCK: HORIZON_TIMING_HELPERS
from __future__ import annotations

from datetime import UTC, date as Date, datetime, time as Time
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schemas.activation import ActivationEvidence
from app.schemas.horizon_selection import HorizonTimingAssessment
from app.services.horizon_canon_service import load_horizon_selection_canon

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INSTANT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
TARGET_TIME_RE = re.compile(r"^\d{2}:\d{2}(?::\d{2})?$")
PREFIX_RE = re.compile(r"^(?:TRANSIT_|NATAL_)+")


def _normalize_planet(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = PREFIX_RE.sub("", value.strip().upper())
    return normalized or None


def _safe_assessment(
    evidence: ActivationEvidence,
    *,
    timezone: str,
    target_local: str,
    target_utc: str,
    relative_position: str,
    warning_codes: list[str],
    timing_state: str | None = None,
    timing_completeness: float = 0.0,
    precision: str | None = None,
    duration_seconds: float | None = None,
    duration_days: float | None = None,
    eligible_horizons: list[str] | None = None,
    preferred_horizons: list[str] | None = None,
    is_anchor_eligible: bool = False,
) -> HorizonTimingAssessment:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE._safe_assessment
    # purpose: Build deterministic ineligible/eligible timing results without leaking raw parse errors.
    # inputs: evidence and machine timing fields.
    # returns: HorizonTimingAssessment.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE._safe_assessment
    return HorizonTimingAssessment(
        activation_id=evidence.id,
        precision=precision,
        active_from=evidence.active_from,
        exact_at=evidence.exact_at,
        active_until=evidence.active_until,
        timezone=timezone,
        target_local=target_local,
        target_utc=target_utc,
        duration_seconds=duration_seconds,
        duration_days=duration_days,
        relative_position=relative_position,
        timing_state=timing_state,
        timing_completeness=timing_completeness,
        eligible_horizons=list(eligible_horizons or []),
        preferred_horizons=list(preferred_horizons or []),
        warning_codes=list(dict.fromkeys(warning_codes)),
        is_anchor_eligible=is_anchor_eligible,
    )


def _parse_target_clock(*, target_date: str, target_time: str, target_tz: str) -> tuple[datetime, datetime]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE._parse_target_clock
    # purpose: Parse request target clock into local and UTC datetimes.
    # inputs: target_date, target_time, target_tz.
    # returns: (target_local_dt, target_utc_dt).
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError on malformed date/time/tz.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE._parse_target_clock
    if not DATE_RE.fullmatch(target_date):
        raise ValueError("target_date")
    if not TARGET_TIME_RE.fullmatch(target_time):
        raise ValueError("target_time")
    zone = ZoneInfo(target_tz)
    parsed_date = Date.fromisoformat(target_date)
    hh, mm, *rest = [int(part) for part in target_time.split(":")]
    ss = rest[0] if rest else 0
    target_local = datetime.combine(parsed_date, Time(hh, mm, ss), tzinfo=zone)
    return target_local, target_local.astimezone(UTC)


def _detect_precision(evidence: ActivationEvidence) -> str | None:
    values = [value for value in (evidence.active_from, evidence.exact_at, evidence.active_until) if value is not None]
    if not values:
        return None
    date_flags = [bool(DATE_RE.fullmatch(value)) for value in values]
    instant_flags = [bool(INSTANT_RE.fullmatch(value)) for value in values]
    if all(date_flags):
        return "date"
    if all(instant_flags):
        return "instant"
    if any(date_flags) and any(instant_flags):
        return "mixed"
    if any(not is_date and not is_instant for is_date, is_instant in zip(date_flags, instant_flags, strict=False)):
        return "invalid"
    return "mixed"


def _speed_group(canon: object, source_planet: str | None) -> str | None:
    planet = _normalize_planet(source_planet)
    if planet is None:
        return None
    for group_name in ("fast", "medium", "slow"):
        if planet in getattr(canon.planet_speed_groups, group_name):
            return group_name
    return None


def _duration_matches(duration_days: float, *, minimum: float, maximum: float | None) -> bool:
    return duration_days >= minimum and (maximum is None or duration_days <= maximum)
# END_BLOCK: HORIZON_TIMING_HELPERS


# START_BLOCK: HORIZON_TIMING_SERVICE
class HorizonTimingService:
    def classify(
        self,
        evidence: ActivationEvidence,
        *,
        target_date: str,
        target_time: str,
        target_tz: str,
    ) -> HorizonTimingAssessment:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE.HorizonTimingService.classify
        # purpose: Classify activation timing into public-compatible state, horizon eligibility, and typed warnings.
        # inputs: evidence and request target clock strings.
        # returns: HorizonTimingAssessment.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: invalid canon raises; ordinary timing problems return ineligible assessment.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-TIMING-SERVICE.HorizonTimingService.classify
        canon = load_horizon_selection_canon()
        try:
            target_local, target_utc = _parse_target_clock(target_date=target_date, target_time=target_time, target_tz=target_tz)
        except (ValueError, ZoneInfoNotFoundError):
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=f"{target_date}T{target_time}",
                target_utc="invalid",
                relative_position="inside",
                warning_codes=["invalid_target_clock"],
            )

        target_local_str = target_local.isoformat()
        target_utc_str = target_utc.isoformat()
        precision = _detect_precision(evidence)
        if precision is None:
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                warning_codes=["missing_timing"],
            )
        if evidence.active_from is None or evidence.active_until is None:
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                precision=None if precision == "mixed" else precision,
                warning_codes=["mixed_precision" if precision == "mixed" else "partial_timing"],
            )
        if precision == "invalid":
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                warning_codes=["invalid_timing"],
            )
        if precision == "mixed":
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                warning_codes=["mixed_precision"],
            )

        rule = canon.technique_rules.get(evidence.technique)
        if rule is None:
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                precision=precision,
                warning_codes=["unknown_technique"],
            )

        try:
            if precision == "date":
                start = Date.fromisoformat(evidence.active_from)
                end = Date.fromisoformat(evidence.active_until)
                exact = Date.fromisoformat(evidence.exact_at) if evidence.exact_at is not None else None
                if exact is not None and not (start <= exact <= end):
                    raise ValueError("exact_outside")
                if start > end:
                    raise ValueError("order")
                target_value = target_local.date()
                duration_days = float((end - start).days + 1)
                duration_seconds = duration_days * 86400.0
                if target_value < start:
                    return _safe_assessment(evidence, timezone=target_tz, target_local=target_local_str, target_utc=target_utc_str, relative_position="before", precision="date", duration_seconds=duration_seconds, duration_days=duration_days, timing_state="upcoming", warning_codes=["target_before_window"])
                if target_value > end:
                    return _safe_assessment(evidence, timezone=target_tz, target_local=target_local_str, target_utc=target_utc_str, relative_position="after", precision="date", duration_seconds=duration_seconds, duration_days=duration_days, timing_state="fading", warning_codes=["target_after_window"])
                if rule.timing_mode == "period":
                    state = "background" if rule.preferred_horizon == "long" else "active"
                elif rule.timing_mode == "window" and exact is None:
                    state = "background" if rule.preferred_horizon == "long" else "active"
                elif exact is None:
                    state = "active"
                else:
                    day_delta = (target_value - exact).days
                    if abs(day_delta) <= canon.timing.date_exact_tolerance_days:
                        state = "exact"
                    elif day_delta < 0:
                        state = "building"
                    else:
                        post_seconds = max((end - exact).days * 86400.0, 0.0)
                        peaked_window_seconds = max(canon.timing.peaked_min_seconds, post_seconds * canon.timing.peaked_post_exact_fraction)
                        state = "peaked" if day_delta * 86400.0 <= peaked_window_seconds else "fading"
            else:
                start = datetime.fromisoformat(evidence.active_from.replace("Z", "+00:00")).astimezone(UTC)
                end = datetime.fromisoformat(evidence.active_until.replace("Z", "+00:00")).astimezone(UTC)
                exact = datetime.fromisoformat(evidence.exact_at.replace("Z", "+00:00")).astimezone(UTC) if evidence.exact_at is not None else None
                if exact is not None and not (start <= exact <= end):
                    raise ValueError("exact_outside")
                if start > end:
                    raise ValueError("order")
                duration_seconds = (end - start).total_seconds()
                duration_days = duration_seconds / 86400.0
                if target_utc < start:
                    return _safe_assessment(evidence, timezone=target_tz, target_local=target_local_str, target_utc=target_utc_str, relative_position="before", precision="instant", duration_seconds=duration_seconds, duration_days=duration_days, timing_state="upcoming", warning_codes=["target_before_window"])
                if target_utc > end:
                    return _safe_assessment(evidence, timezone=target_tz, target_local=target_local_str, target_utc=target_utc_str, relative_position="after", precision="instant", duration_seconds=duration_seconds, duration_days=duration_days, timing_state="fading", warning_codes=["target_after_window"])
                if rule.timing_mode == "period":
                    state = "background" if rule.preferred_horizon == "long" else "active"
                elif rule.timing_mode == "window" and exact is None:
                    state = "background" if rule.preferred_horizon == "long" else "active"
                elif exact is None:
                    state = "active"
                else:
                    delta_seconds = (target_utc - exact).total_seconds()
                    if abs(delta_seconds) <= canon.timing.instant_exact_tolerance_seconds:
                        state = "exact"
                    elif delta_seconds < 0:
                        state = "building"
                    else:
                        post_seconds = max((end - exact).total_seconds(), 0.0)
                        peaked_window_seconds = max(canon.timing.peaked_min_seconds, post_seconds * canon.timing.peaked_post_exact_fraction)
                        state = "peaked" if delta_seconds <= peaked_window_seconds else "fading"
        except (ValueError, TypeError, OverflowError):
            return _safe_assessment(
                evidence,
                timezone=target_tz,
                target_local=target_local_str,
                target_utc=target_utc_str,
                relative_position="inside",
                precision=precision,
                warning_codes=["invalid_timing"],
            )

        eligible_horizons: list[str] = []
        source_speed_warning: list[str] = []
        duration_bands = canon.duration_bands
        source_speed_group = _speed_group(canon, evidence.source_planet) if evidence.technique.startswith("transit_") else None
        for horizon in ("long", "medium", "fast"):
            if horizon not in rule.allowed_horizons:
                continue
            band = getattr(duration_bands, horizon)
            if not _duration_matches(duration_days, minimum=band.eligible_min_days, maximum=band.eligible_max_days):
                continue
            if evidence.technique.startswith("transit_"):
                if source_speed_group is None:
                    source_speed_warning = ["unknown_source_speed"]
                    continue
                if source_speed_group not in canon.transit_speed_eligibility[horizon]:
                    continue
            eligible_horizons.append(horizon)
        if rule.preferred_horizon in eligible_horizons:
            preferred_horizons = [rule.preferred_horizon]
        else:
            preferred_horizons = [
                horizon
                for horizon in eligible_horizons
                if _duration_matches(
                    duration_days,
                    minimum=getattr(duration_bands, horizon).preferred_min_days,
                    maximum=getattr(duration_bands, horizon).preferred_max_days,
                )
            ]
            if not preferred_horizons:
                preferred_horizons = list(eligible_horizons)

        timing_completeness = canon.timing.completeness_with_exact if evidence.exact_at is not None else canon.timing.completeness_without_exact
        is_anchor_eligible = bool(eligible_horizons)
        return _safe_assessment(
            evidence,
            timezone=target_tz,
            target_local=target_local_str,
            target_utc=target_utc_str,
            relative_position="inside",
            timing_state=state,
            timing_completeness=timing_completeness,
            precision=precision,
            duration_seconds=duration_seconds,
            duration_days=duration_days,
            eligible_horizons=eligible_horizons,
            preferred_horizons=preferred_horizons,
            warning_codes=source_speed_warning,
            is_anchor_eligible=is_anchor_eligible,
        )
# END_BLOCK: HORIZON_TIMING_SERVICE


__all__ = ["HorizonTimingService", "_parse_target_clock"]
