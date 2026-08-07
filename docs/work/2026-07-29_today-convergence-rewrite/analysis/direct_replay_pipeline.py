#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: DIRECT_REPLAY_PIPELINE — in-process ephemeris-to-factor pipeline.
# ROLE: Replays the production deterministic calculation path without HTTP,
#       database reads, LLM calls, or persistence.
# ############################################################################

# START_MODULE_CONTRACT: M-DIRECT-REPLAY-PIPELINE
# purpose: Convert a synthetic chart and target day into the same normalized
#   factor records consumed by the convergence ablation classifier.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/direct_replay_pipeline.py
# inputs: ChartInput, birth control time, target date, optional previous-day
#   normalized signals, and timing scope.
# outputs: PreparedChart, TargetBundle, and compact FactorDay records.
# dependencies: shared sidecar calculation core; API normalization, scoring,
#   DayDelta, activation-layer, factor-ledger, focus normalization services,
#   and the strict W1 convergence canon loader.
# side_effects: Swiss Ephemeris artifact reads; process-local canon caches only.
# emitted_logs: none.
# invariants:
#   - No HTTP, DB, LLM, or user-profile access occurs.
#   - Sidecar HTTP routes and this module share the same calculation core.
#   - Corrected DayDelta keys use canonical semantic identities.
#   - Product spheres come from the new W1 canon, never the legacy Today map.
# failure_policy: raises on any invalid calculation or contract; corpus runner
#   records the shard failure and never treats it as a successful sample.
# END_MODULE_CONTRACT: M-DIRECT-REPLAY-PIPELINE

# START_MODULE_MAP: M-DIRECT-REPLAY-PIPELINE
# public_entrypoints:
#   - ChartInput
#   - PreparedChart
#   - TargetBundle
#   - FactorDay
#   - DirectReplayPipeline.prepare_chart
#   - DirectReplayPipeline.prepare_target
#   - DirectReplayPipeline.normalize_signals
#   - DirectReplayPipeline.calculate_factor_day
# semantic_blocks:
#   - PATH_BOOTSTRAP: repository-local import roots.
#   - DATA_MODELS: typed chart/context/day containers.
#   - SEMANTIC_KEYS: canonical factor identity helpers.
#   - DIRECT_PIPELINE: in-process product calculation path.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_direct_replay_pipeline.py
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# END_MODULE_MAP: M-DIRECT-REPLAY-PIPELINE

from __future__ import annotations

# START_BLOCK: PATH_BOOTSTRAP
import sys
from dataclasses import dataclass
from datetime import date as Date
from pathlib import Path
from typing import Any, Literal

REPO = Path(__file__).resolve().parents[4]
for import_root in (REPO / "apps/solarsage", REPO / "apps/api"):
    root_text = str(import_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
# END_BLOCK: PATH_BOOTSTRAP

from app.schemas.natal import SolarSageNatalResponse  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.day_factor_ledger import (  # noqa: E402
    _normalize_target_type,
    build_factor_ledger,
)
from app.services.day_scoring_signals import filter_day_scored_signals  # noqa: E402
from app.services.natal_context_service import NatalContextService  # noqa: E402
from app.services.normalization_service import NormalizationService  # noqa: E402
from app.services.scoring_service import ScoringService  # noqa: E402
from app.services.today_focus_builder import normalize_factors  # noqa: E402
from convergence_canon import resolve_factor_projection  # noqa: E402
from solarsage.services.calculation_core import (  # noqa: E402
    NatalCalculationContext,
    TargetCalculationContext,
    calculate_activation_layer,
    prepare_natal_context,
    prepare_target_context,
)
from solarsage.services.transit_timing import TransitTimingSolver  # noqa: E402


# START_BLOCK: DATA_MODELS
@dataclass(frozen=True)
class ChartInput:
    chart_id: str
    birth_date: str
    birth_time: str
    birth_lat: float
    birth_lon: float
    birth_tz: str
    target_tz: str
    house_system: str = "PLACIDUS"
    current_lat: float | None = None
    current_lon: float | None = None
    current_tz: str | None = None

    @property
    def current_location(self) -> dict[str, Any] | None:
        if self.current_lat is None or self.current_lon is None or self.current_tz is None:
            return None
        return {
            "lat": self.current_lat,
            "lon": self.current_lon,
            "tz": self.current_tz,
        }


@dataclass(frozen=True)
class PreparedChart:
    chart: ChartInput
    control_time: str
    sidecar_natal: NatalCalculationContext
    product_natal: dict[str, Any]


@dataclass(frozen=True)
class TargetBundle:
    context: TargetCalculationContext
    transits_payload: dict[str, Any]


@dataclass(frozen=True)
class FactorDay:
    target_date: str
    factors: tuple[dict[str, Any], ...]
    trigger_keys: frozenset[str]
    delta_new_today: tuple[str, ...]
    delta_peak: tuple[str, ...]
    raw_activation_count: int
    raw_ledger_count: int
    invalid_ledger_count: int
    duplicate_ledger_count: int
    timing_deferred_count: int
    sect_is_day: bool | None
    current_signals: tuple[Any, ...]
# END_BLOCK: DATA_MODELS


# START_BLOCK: SEMANTIC_KEYS
def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def activation_semantic_key(activation: Any) -> str | None:
    source = strip_prefix(
        str(_get(activation, "source_planet") or _get(activation, "planet") or "")
    ).strip().upper()
    target = strip_prefix(
        str(_get(activation, "target_key") or _get(activation, "target_planet") or "")
    ).strip().upper()
    aspect = str(
        _get(activation, "aspect") or _get(activation, "aspect_type") or ""
    ).strip().lower()
    if not (source and target and aspect):
        return None
    target_type = _normalize_target_type(
        str(_get(activation, "target_type") or "") or None,
        target,
    )
    return f"aspect:{source}:{aspect}:{target_type}:{target}"


def signal_semantic_key(signal: Any) -> str | None:
    signal_type = _get(signal, "type")
    source = strip_prefix(str(_get(signal, "planet") or "")).strip().upper()
    if not source:
        return None
    if signal_type == "aspect":
        target = strip_prefix(str(_get(signal, "target_planet") or "")).strip().upper()
        aspect = str(_get(signal, "aspect_type") or "").strip().lower()
        if not target or not aspect:
            return None
        target_type = _normalize_target_type(None, target)
        return f"aspect:{source}:{aspect}:{target_type}:{target}"
    if signal_type == "planet_in_house":
        house = _get(signal, "house")
        return f"house:{source}:{house}" if house is not None else None
    return None


def strict_product_projection(
    technical_spheres: list[str] | tuple[str, ...] | None,
    source_key: str | None,
    target_key: str | None,
    *,
    house: int | None = None,
    theme_keys: list[str] | tuple[str, ...] | None = None,
) -> tuple[str, str | None] | None:
    # START_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.strict_product_projection
    # purpose: Resolve one replay factor through the product sphere/facet canon.
    # inputs: factor technical spheres, source/target keys, optional house and
    #   explicit theme keys.
    # returns: one (sphere, facet) pair or None; never a sphere fan-out.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown/unmapped factor remains unresolved.
    # END_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.strict_product_projection
    return resolve_factor_projection(
        house=house,
        technical_spheres=technical_spheres,
        theme_keys=theme_keys,
        source_key=source_key,
        target_key=target_key,
    )
# END_BLOCK: SEMANTIC_KEYS


# START_BLOCK: DIRECT_PIPELINE
class DirectReplayPipeline:
    def __init__(
        self,
        *,
        timing_scope: Literal["all", "convergence_eligible"] = "convergence_eligible",
        techniques: list[str] | None = None,
    ) -> None:
        self.timing_scope = timing_scope
        self.techniques = techniques
        self.normalization = NormalizationService()
        self.scoring = ScoringService()
        self.activation_service = ActivationLayerService()

    def prepare_chart(
        self,
        chart: ChartInput,
        *,
        control_time: str | None = None,
    ) -> PreparedChart:
        # START_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.prepare_chart
        # purpose: Build sidecar and product natal contexts once per control time.
        # inputs: ChartInput and optional birth control time.
        # returns: PreparedChart reusable across target days.
        # side_effects: Swiss Ephemeris calculations.
        # emitted_logs: none.
        # error_behavior: propagates validation/calculation errors.
        # END_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.prepare_chart
        birth_time = control_time or chart.birth_time
        sidecar_natal = prepare_natal_context(
            birth_date=chart.birth_date,
            birth_time=birth_time,
            birth_lat=chart.birth_lat,
            birth_lon=chart.birth_lon,
            birth_tz=chart.birth_tz,
            house_system=chart.house_system,
        )
        natal_payload = {
            "house_system": sidecar_natal.resolved_house_system,
            "planets": list(sidecar_natal.natal_positions),
            "houses": list(sidecar_natal.natal_houses_raw),
            "special_points": list(sidecar_natal.natal_special_points),
        }
        validated = SolarSageNatalResponse.model_validate(natal_payload)
        natal_signals = self.normalization.normalize_natal_only(natal_payload)
        natal_scores = self.scoring.score_natal(natal_signals)
        product_natal = NatalContextService._build_context_data(
            validated,
            natal_scores,
        ).model_dump(by_alias=False)
        return PreparedChart(
            chart=chart,
            control_time=birth_time,
            sidecar_natal=sidecar_natal,
            product_natal=product_natal,
        )

    def prepare_target(
        self,
        *,
        target_date: str,
        target_tz: str,
        target_time: str = "12:00",
    ) -> TargetBundle:
        # START_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.prepare_target
        # purpose: Calculate one chart-independent target moment once.
        # inputs: target date/time/timezone.
        # returns: TargetBundle for normalization and activation calculation.
        # side_effects: Swiss Ephemeris calculations.
        # emitted_logs: none.
        # error_behavior: propagates calculation errors.
        # END_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.prepare_target
        context = prepare_target_context(
            target_date=target_date,
            target_time=target_time,
            target_tz=target_tz,
        )
        return TargetBundle(
            context=context,
            transits_payload={
                "planets": list(context.transit_positions),
                "target_jd": context.target_jd,
            },
        )

    def normalize_signals(
        self,
        prepared: PreparedChart,
        target: TargetBundle,
    ) -> list[Any]:
        return self.normalization.normalize_day(
            prepared.product_natal,
            target.transits_payload,
        )

    def calculate_factor_day(
        self,
        *,
        prepared: PreparedChart,
        target: TargetBundle,
        previous_signals: list[Any] | None,
        timing_solver: TransitTimingSolver | None = None,
    ) -> FactorDay:
        # START_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.calculate_factor_day
        # purpose: Run DayDelta -> activation -> ledger -> normalized factors.
        # inputs: prepared chart, target bundle, previous normalized signals.
        # returns: compact FactorDay consumed immediately by replay classifier.
        # side_effects: Swiss calculations for target-dependent techniques.
        # emitted_logs: none.
        # error_behavior: propagates any failure; never emits a partial success.
        # END_FUNCTION_CONTRACT: F-M-DIRECT-REPLAY-PIPELINE.calculate_factor_day
        target_date = target.context.target_date
        signals_raw = self.normalize_signals(prepared, target)
        signals = (
            DayDeltaService(previous_signals, signals_raw).compute_deltas()
            if previous_signals is not None
            else signals_raw
        )
        day_signals = filter_day_scored_signals(signals)

        new_today: set[str] = set()
        peak: set[str] = set()
        for signal in signals:
            delta_kind = _get(signal, "delta_kind")
            if delta_kind not in ("new_today", "peak_today"):
                continue
            semantic_key = signal_semantic_key(signal)
            if not semantic_key:
                continue
            (new_today if delta_kind == "new_today" else peak).add(semantic_key)
        trigger_keys = new_today | peak

        activation_layer = calculate_activation_layer(
            birth_date=prepared.chart.birth_date,
            birth_time=prepared.control_time,
            birth_lat=prepared.chart.birth_lat,
            birth_lon=prepared.chart.birth_lon,
            birth_tz=prepared.chart.birth_tz,
            target_date=target_date,
            target_time=target.context.target_time,
            target_tz=target.context.target_tz,
            house_system=prepared.chart.house_system,
            techniques=self.techniques,
            current_location=prepared.chart.current_location,
            timing_scope=self.timing_scope,
            natal_context=prepared.sidecar_natal,
            target_context=target.context,
            timing_solver=timing_solver,
        )
        product_activation_layer = self.activation_service.build(
            natal_context=prepared.product_natal,
            transits=target.transits_payload,
            day_signals=day_signals,
            target_date=Date.fromisoformat(target_date),
            target_time=target.context.target_time,
            target_tz=target.context.target_tz,
            house_system=prepared.chart.house_system,
            sidecar_activation_layer=activation_layer.model_dump(mode="json"),
        )
        ledger = build_factor_ledger(day_signals, product_activation_layer.activations)
        ledger_by_id = {item.factor_id: item for item in ledger.factors}

        activations_by_semantic: dict[str, list[Any]] = {}
        activations_by_id: dict[str, Any] = {}
        for activation in product_activation_layer.activations:
            activation_id = _get(activation, "id") or _get(activation, "activation_id")
            if activation_id:
                activations_by_id[str(activation_id)] = activation
            semantic_key = activation_semantic_key(activation)
            if semantic_key:
                activations_by_semantic.setdefault(semantic_key, []).append(activation)

        signal_orbs: dict[str, float] = {}
        for signal in day_signals:
            semantic_key = signal_semantic_key(signal)
            orb = _get(signal, "orb")
            if semantic_key and orb is not None:
                signal_orbs.setdefault(semantic_key, float(orb))

        normalized = normalize_factors(
            ledger=ledger,
            activation_layer=product_activation_layer,
            day_delta=None,
            target_date=Date.fromisoformat(target_date),
            tz_info=prepared.chart.target_tz,
        )
        records: list[dict[str, Any]] = []
        for factor in normalized:
            ledger_factor = ledger_by_id.get(factor.factor_id)
            semantic_key = (
                ledger_factor.semantic_key if ledger_factor is not None else factor.factor_id
            )
            matched = activations_by_semantic.get(semantic_key) or []
            if not matched:
                matched = [
                    activation
                    for activation_id, activation in activations_by_id.items()
                    if activation_id and activation_id in factor.factor_id
                ]
            orb = _get(matched[0], "orb") if matched else None
            orb_source = "activation" if orb is not None else "none"
            if orb is None and semantic_key in signal_orbs:
                orb = signal_orbs[semantic_key]
                orb_source = "day_signal"
            house = _get(factor, "house")
            technical_spheres = tuple(
                str(value).strip()
                for value in (ledger_factor.technical_spheres if ledger_factor else ())
                if str(value).strip()
            )
            theme_keys = tuple(str(value).strip() for value in (factor.theme_keys or ()) if str(value).strip())
            projection = strict_product_projection(
                technical_spheres,
                factor.source_key,
                factor.target_key,
                house=house if isinstance(house, int) and not isinstance(house, bool) else None,
                theme_keys=theme_keys,
            )
            # Keep the physical unit even when product projection is
            # unresolved. Production resolves sphere/facet after the unit
            # and physical-group boundaries; replay must therefore carry the
            # unresolved row into canonical IDs, grouping, and audit, while
            # publication/selection remains fail-closed downstream.
            records.append(
                {
                    "semantic_key": semantic_key,
                    "factor_id": factor.factor_id,
                    "source": ledger_factor.source if ledger_factor else None,
                    "temporal_role": factor.temporal_role,
                    "technique": factor.technique,
                    "technique_family": factor.technique_family,
                    "source_planet": factor.source_key,
                    "aspect_type": factor.aspect_type,
                    "orb": orb,
                    "orb_source": orb_source,
                    "strength": factor.strength,
                    "polarity": factor.polarity,
                    "target_type": factor.target_type,
                    "target_key": factor.target_key,
                    "theme_keys": list(theme_keys),
                    "technical_spheres": list(technical_spheres),
                    "house": house,
                    "spheres": [projection[0]] if projection is not None else [],
                    "facet": projection[1] if projection is not None else None,
                    "exact_at": factor.exact_at.isoformat() if factor.exact_at else None,
                }
            )

        timing_deferred = sum(
            1
            for activation in activation_layer.activations
            if activation.debug.get("timing", {}).get("status") == "not_requested"
        )
        return FactorDay(
            target_date=target_date,
            factors=tuple(records),
            trigger_keys=frozenset(trigger_keys),
            delta_new_today=tuple(sorted(new_today)),
            delta_peak=tuple(sorted(peak)),
            raw_activation_count=len(activation_layer.activations),
            raw_ledger_count=len(ledger.factors),
            invalid_ledger_count=ledger.invalid_count,
            duplicate_ledger_count=ledger.duplicate_count,
            timing_deferred_count=timing_deferred,
            sect_is_day=prepared.sidecar_natal.is_day,
            current_signals=tuple(signals_raw),
        )
# END_BLOCK: DIRECT_PIPELINE
