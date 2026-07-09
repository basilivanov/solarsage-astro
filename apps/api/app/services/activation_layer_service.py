# ############################################################################
# AI_HEADER: MODULE_ACTIVATION_LAYER_SERVICE — build activation layer from day signals.
# ROLE: W2 minimal activation layer — transit-to-natal aspects and transit-in-house.
#       Does not enable V2 scoring. Provides structured evidence for future waves.
# ############################################################################

from __future__ import annotations

from datetime import date as Date
from typing import Any

from app.schemas.activation import (
    ActivationEvidence,
    ActivationLayer,
    ActivationPhase,
    ActivationPolarity,
)
from app.schemas.normalization import AstroSignal
from app.services.astro_utils import strip_prefix


POLARITY_MAP: dict[str, ActivationPolarity] = {
    "trine": "supportive",
    "sextile": "supportive",
    "square": "tense",
    "opposition": "tense",
    "conjunction": "mixed",
}


def _build_id(prefix: str, signal: AstroSignal) -> str:
    """Deterministic stable id for a signal-based activation."""
    source = strip_prefix(signal.planet)
    target = strip_prefix(signal.target_planet) if signal.target_planet else str(signal.house or 0)
    return f"{prefix}__{source.upper()}__{target.upper()}"


def _polarity(aspect_type: str | None) -> ActivationPolarity:
    if aspect_type and aspect_type in POLARITY_MAP:
        return POLARITY_MAP[aspect_type]
    return "neutral"


def _phase(signal: AstroSignal) -> ActivationPhase:
    if signal.phase and signal.phase in ("applying", "exact", "separating", "background", "period"):
        return signal.phase  # type: ignore
    return "background"


class ActivationLayerService:
    """Build a deterministic ActivationLayer from day signals and optional sidecar layer.

    W2: builds only transit-to-natal and transit-in-house activations.
    Does not compute profection, firdar, return, progression, eclipse, lot, or angle activations.
    """

    def build(
        self,
        *,
        natal_context: dict,
        transits: dict,
        day_signals: list[AstroSignal],
        target_date: Date,
        target_time: str,
        target_tz: str,
        house_system: str,
        sidecar_activation_layer: ActivationLayer | dict | None = None,
    ) -> ActivationLayer:
        # If a sidecar layer is provided, validate and return it
        if sidecar_activation_layer is not None:
            if isinstance(sidecar_activation_layer, dict):
                return ActivationLayer.model_validate(sidecar_activation_layer)
            return sidecar_activation_layer

        return self._build_from_day_signals(
            day_signals=day_signals,
            target_date=target_date,
            target_time=target_time,
            target_tz=target_tz,
            house_system=house_system,
        )

    def _build_from_day_signals(
        self,
        *,
        day_signals: list[AstroSignal],
        target_date: Date,
        target_time: str,
        target_tz: str,
        house_system: str,
    ) -> ActivationLayer:
        from app.services.day_scoring_signals import filter_day_scored_signals

        # Use day-scored signals only (static natal background excluded)
        scored = filter_day_scored_signals(day_signals)

        activations: list[ActivationEvidence] = []
        by_planet: dict[str, list[str]] = {}
        by_house: dict[str, list[str]] = {}
        by_lot: dict[str, list[str]] = {}
        by_angle: dict[str, list[str]] = {}

        for signal in scored:
            # Explicit Transit_ guard: only process transit signals, not natal/static
            if not (signal.planet or "").startswith("Transit_"):
                continue
            if signal.type == "aspect" and signal.target_planet:
                act = self._build_transit_aspect(signal)
                activations.append(act)
                target_key = strip_prefix(signal.target_planet).upper()
                by_planet.setdefault(target_key, []).append(act.id)

            elif signal.type == "planet_in_house":
                act = self._build_transit_in_house(signal)
                activations.append(act)
                house_key = str(signal.house or 0)
                by_house.setdefault(house_key, []).append(act.id)

        return ActivationLayer(
            calculation_version="1",
            target_date=target_date.isoformat(),
            target_time=target_time,
            target_tz=target_tz,
            house_system=house_system,
            activations=activations,
            by_planet=by_planet,
            by_house=by_house,
            by_lot=by_lot,
            by_angle=by_angle,
        )

    @staticmethod
    def _build_transit_aspect(signal: AstroSignal) -> ActivationEvidence:
        source_clean = strip_prefix(signal.planet).upper()
        target_clean = strip_prefix(signal.target_planet).upper() if signal.target_planet else "UNKNOWN"
        aid = _build_id("t2n", signal)

        evidence = (
            f"Transit {strip_prefix(signal.planet)} {signal.aspect_type} "
            f"natal {strip_prefix(signal.target_planet) if signal.target_planet else ''}, "
            f"orb {signal.orb:.4f}°"
        )

        return ActivationEvidence(
            id=aid,
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key=target_clean,
            kind="aspect",
            active=True,
            source_planet=source_clean,
            source_frame="transit",
            target_planet=target_clean,
            target_frame="natal",
            aspect=signal.aspect_type,
            orb=signal.orb,
            strength=signal.strength,
            phase=_phase(signal),
            polarity=_polarity(signal.aspect_type),
            evidence=evidence,
        )

    @staticmethod
    def _build_transit_in_house(signal: AstroSignal) -> ActivationEvidence:
        source_clean = strip_prefix(signal.planet).upper()
        house = signal.house or 0
        aid = _build_id("tih", signal)

        evidence = (
            f"Transit {strip_prefix(signal.planet)} in natal house {house}, "
            f"strength {signal.strength:.2f}"
        )

        return ActivationEvidence(
            id=aid,
            technique="transit_planet_in_house",
            technique_family="transit",
            target_type="house",
            target_key=str(house),
            kind="planet_in_house",
            active=True,
            source_planet=source_clean,
            source_frame="transit",
            house=house,
            strength=signal.strength,
            polarity="neutral",
            evidence=evidence,
        )
