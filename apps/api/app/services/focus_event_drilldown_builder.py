# ############################################################################
# AI_HEADER: MODULE_API_FOCUS_EVENT_DRILLDOWN
# ROLE: Pure service module building deterministic FocusEventDrilldown responses.
# DEPENDENCIES: datetime, zoneinfo, app.schemas.today_focus, app.services.sphere_why_builder, app.services.synastry_llm, app.services.astro_utils
# ############################################################################

# START_MODULE_CONTRACT: M-API-FOCUS-EVENT-DRILLDOWN
# purpose: Build deterministic FocusEventDrilldown objects from cached payload event and activation evidence (§87 of E1 TZ).
# owns:
#   - apps/api/app/services/focus_event_drilldown_builder.py
# inputs: event (dict), evidence (list[dict])
# outputs: build_focus_event_drilldown -> FocusEventDrilldown
# dependencies: app.schemas.today_focus, app.services.sphere_why_builder, app.services.synastry_llm, app.services.astro_utils
# side_effects: none (pure calculation)
# emitted_logs: none
# failure_policy: returns FocusEventDrilldown with graceful degradation when evidence is missing
# END_MODULE_CONTRACT: M-API-FOCUS-EVENT-DRILLDOWN

# START_MODULE_MAP: M-API-FOCUS-EVENT-DRILLDOWN
# public_entrypoints:
#   - build_focus_event_drilldown
# semantic_blocks:
#   - DRILLDOWN_BUILDER: deterministic focus event drilldown builder and number formatters
# owned_tests:
#   - tests/test_focus_event_drilldown.py
# END_MODULE_MAP: M-API-FOCUS-EVENT-DRILLDOWN

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.schemas.today_focus import (
    FocusEventDrilldown,
    FocusEventNumber,
    FocusEventPlanetSide,
)
from app.services.astro_utils import strip_prefix
from app.services.sphere_why_builder import PLANET_FUNCTIONS
from app.services.synastry_llm import ASPECT_MEANINGS, PLANET_MEANINGS

PLANET_LABELS_RU: dict[str, str] = {
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
}

ASPECT_DETAILS: dict[str, tuple[str, str]] = {
    "conjunction": ("Соединение", "☌"),
    "opposition": ("Оппозиция", "☍"),
    "trine": ("Тригон", "△"),
    "square": ("Квадрат", "□"),
    "sextile": ("Секстиль", "⚹"),
    "quincunx": ("Квиконс", "⚻"),
    "semi_square": ("Полуквадрат", "∠"),
    "sesqui_quadrate": ("Полутораквадрат", "⚼"),
    "sesquisquare": ("Полутораквадрат", "⚼"),
    "semi_sextile": ("Полусекстиль", "⚺"),
}

KIND_LABELS: dict[str, str] = {
    "exact": "точный пик",
    "peak": "точный пик",
    "starts": "начинается",
    "building": "нарастает",
    "separating": "ослабевает",
}

TECHNIQUE_LABELS: dict[str, str] = {
    "transit_to_natal": "Транзит к твоей натальной карте",
    "transit_to_lot": "Транзит к жребию",
    "lunar_return": "Лунар (карта месяца)",
    "solar_return": "Соляр (карта года)",
}


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_orb_label(orb: float | None) -> str | None:
    if orb is None or orb < 0:
        return None
    deg = int(orb)
    mins = int(round((orb - deg) * 60))
    if mins >= 60:
        deg += 1
        mins = 0
    return f"{deg}°{mins:02d}′"


def _to_utc_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def _format_local_time(dt: datetime | None, tz_name: str) -> str | None:
    if dt is None:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%H:%M")


def _format_local_datetime_short(dt: datetime | None, tz_name: str) -> str | None:
    if dt is None:
        return None
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%d.%m %H:%M")


def _extract_function_text(planet_key: str) -> str:
    key_title = planet_key.title()
    func_raw = PLANET_FUNCTIONS.get(key_title) or PLANET_MEANINGS.get(key_title)
    if isinstance(func_raw, dict):
        return str(func_raw.get("nom") or "планетарное влияние")
    if isinstance(func_raw, str):
        return func_raw
    return "планетарное влияние"


# START_BLOCK: DRILLDOWN_BUILDER
def build_focus_event_drilldown(
    event: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
) -> FocusEventDrilldown:
    # START_FUNCTION_CONTRACT: F-M-API-FOCUS-EVENT-DRILLDOWN.build_focus_event_drilldown
    # purpose: Build FocusEventDrilldown from cached event dict and matching evidence list (§87 of E1 TZ).
    # inputs: event (dict), evidence (list[dict] | None)
    # returns: FocusEventDrilldown
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns FocusEventDrilldown with None for missing fields gracefully
    # END_FUNCTION_CONTRACT: F-M-API-FOCUS-EVENT-DRILLDOWN.build_focus_event_drilldown
    evidence_list = evidence or []
    primary_ev = evidence_list[0] if evidence_list else {}

    event_id = str(_get_field(event, "id", ""))
    human_title = str(_get_field(event, "humanTitle", _get_field(event, "human_title", "")))
    technical_title = _get_field(event, "technicalTitle", _get_field(event, "technical_title"))
    kind = str(_get_field(event, "kind", "exact"))
    kind_label = KIND_LABELS.get(kind, kind)
    timezone_name = str(_get_field(event, "timezone", "UTC"))

    occurs_at_dt = _to_utc_datetime(_get_field(event, "occursAt", _get_field(event, "occurs_at")))
    local_time = _format_local_time(occurs_at_dt, timezone_name)
    meaning = _get_field(event, "meaning")

    source_act_ids = list(_get_field(event, "sourceActivationIds", _get_field(event, "source_activation_ids", [])))

    # Technique label
    tech_raw = str(_get_field(primary_ev, "technique") or _get_field(event, "technique") or "transit_to_natal")
    technique_label = TECHNIQUE_LABELS.get(tech_raw, "Астрологический цикл")

    # Source & Target sides
    src_planet_raw = (
        _get_field(primary_ev, "planet")
        or _get_field(primary_ev, "sourcePlanet")
        or _get_field(primary_ev, "source_planet")
    )
    tgt_planet_raw = (
        _get_field(primary_ev, "targetPlanet")
        or _get_field(primary_ev, "target_planet")
        or _get_field(primary_ev, "targetKey")
        or _get_field(primary_ev, "target_key")
        or _get_field(primary_ev, "lot")
    )
    target_type_raw = str(_get_field(primary_ev, "targetType") or _get_field(primary_ev, "target_type") or "").lower()

    source_side: FocusEventPlanetSide | None = None
    if src_planet_raw:
        src_clean = strip_prefix(str(src_planet_raw)).upper()
        src_label = PLANET_LABELS_RU.get(src_clean, src_clean)
        src_func = _extract_function_text(src_clean)
        source_side = FocusEventPlanetSide(
            planet_key=src_clean,
            label=src_label,
            frame_label="транзитная",
            function_text=src_func,
        )

    target_side: FocusEventPlanetSide | None = None
    if tgt_planet_raw:
        tgt_clean = strip_prefix(str(tgt_planet_raw)).upper()
        if target_type_raw == "lot" or tgt_clean in ("FORTUNE", "SPIRIT", "EROS", "SCIENCE", "MARRIAGE", "NECESSITY"):
            target_side = FocusEventPlanetSide(
                planet_key=tgt_clean,
                label="Жребий",
                frame_label="твой жребий",
                function_text="особая расчётная точка карты",
            )
        else:
            tgt_label = PLANET_LABELS_RU.get(tgt_clean, tgt_clean)
            tgt_func = _extract_function_text(tgt_clean)
            target_side = FocusEventPlanetSide(
                planet_key=tgt_clean,
                label=tgt_label,
                frame_label="твой натальный",
                function_text=tgt_func,
            )

    # Aspect label, symbol, tone, mechanics
    aspect_raw = str(_get_field(primary_ev, "aspect") or _get_field(primary_ev, "aspectType") or _get_field(primary_ev, "aspect_type") or "").lower()
    aspect_label: str | None = None
    aspect_symbol: str | None = None
    aspect_mechanics: str | None = None

    if aspect_raw in ASPECT_DETAILS:
        aspect_label, aspect_symbol = ASPECT_DETAILS[aspect_raw]
    if aspect_raw in ASPECT_MEANINGS:
        aspect_mechanics = ASPECT_MEANINGS[aspect_raw].get("explanation")

    aspect_tone: str | None = _get_field(primary_ev, "polarity") or _get_field(primary_ev, "tone")

    # Numbers
    numbers: list[FocusEventNumber] = []

    # 1. Orb
    orb_raw = _get_field(primary_ev, "orb")
    if orb_raw is not None:
        try:
            orb_val = float(orb_raw)
            orb_str = _format_orb_label(orb_val)
            if orb_str:
                numbers.append(FocusEventNumber(label="Орб", value=orb_str))
        except (TypeError, ValueError):
            pass

    # 2. Exact time
    if local_time:
        numbers.append(FocusEventNumber(label="Точное время", value=f"{local_time} · {timezone_name}"))

    # 3. Phase
    phase_raw = str(_get_field(primary_ev, "phase") or "").lower()
    if phase_raw:
        phase_map = {
            "exact": "точный",
            "applying": "сходящийся",
            "building": "сходящийся",
            "separating": "расходящийся",
            "period": "долгий период",
            "background": "долгий период",
        }
        phase_str = phase_map.get(phase_raw, phase_raw)
        numbers.append(FocusEventNumber(label="Фаза", value=phase_str))

    # 4. Active window
    af_dt = _to_utc_datetime(_get_field(primary_ev, "activeFrom") or _get_field(primary_ev, "active_from"))
    au_dt = _to_utc_datetime(_get_field(primary_ev, "activeUntil") or _get_field(primary_ev, "active_until"))
    if af_dt and au_dt:
        af_str = _format_local_datetime_short(af_dt, timezone_name)
        au_str = _format_local_datetime_short(au_dt, timezone_name)
        if af_str and au_str:
            numbers.append(FocusEventNumber(label="Окно действия", value=f"{af_str} — {au_str}"))

    # 5. Strength
    strength_raw = _get_field(primary_ev, "strength")
    if strength_raw is not None:
        try:
            st_val = float(strength_raw)
            numbers.append(FocusEventNumber(label="Сила влияния", value=f"{int(round(st_val * 100))}%"))
        except (TypeError, ValueError):
            pass

    # 6. Polarity / Tone
    if aspect_tone:
        tone_map = {
            "supportive": "поддерживающий",
            "tense": "напряжённый",
            "mixed": "смешанный",
            "neutral": "нейтральный",
        }
        numbers.append(FocusEventNumber(label="Полюс", value=tone_map.get(aspect_tone, aspect_tone)))

    return FocusEventDrilldown(
        event_id=event_id,
        human_title=human_title,
        technical_title=technical_title,
        kind=kind,
        kind_label=kind_label,
        occurs_at=occurs_at_dt,
        local_time=local_time,
        timezone=timezone_name,
        meaning=meaning,
        technique_label=technique_label,
        source=source_side,
        target=target_side,
        aspect_label=aspect_label,
        aspect_symbol=aspect_symbol,
        aspect_tone=aspect_tone,
        aspect_mechanics=aspect_mechanics,
        numbers=numbers,
        source_activation_ids=source_act_ids,
    )
# END_BLOCK: DRILLDOWN_BUILDER
