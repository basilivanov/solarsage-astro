# AI_HEADER: MODULE_DAY_SERVICE
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-NATAL-FULL (Wave 3 — day pipeline reuse)
# purpose: TodayService returns TodayPayload for a given user and date.

# START_MODULE_CONTRACT: M-DAY-SERVICE
# purpose: Get TodayPayload for a user and date.
#          W-NATAL-FULL: Uses NatalContextService for natal facts.
#          Only calls sidecar for transits, never for natal chart.
#          Day cache keyed by (user_id, target_date, profile_hash).
# owns:
#   - apps/api/app/services/today_service.py
# inputs:
#   - user_id: UUID
#   - target_date: date
#   - access_state: ContentAccessState
#   - selection_context: optional immutable request-scoped V1/V2 authority
#   - db: AsyncSession
# outputs:
#   - TodayPayload
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-CONTRACTS.today (TodayPayload)
#   - M-ACCESS (ContentAccessState)
#   - M-NATAL-CONTEXT-SERVICE (NatalContextService)
#   - M-SOLARSAGE-CLIENT (get_solarsage_client — transits only)
#   - M-LLM-SERVICE
#   - M-TODAY-HORIZON-INTEGRATION-SERVICE (request-local V2 horizons bridge)
#   - M-CACHE-KEY-SERVICE (resolve_today_runtime_identity)
#   - M-TODAY-SELECTION-CONTEXT (explicit request-local selection value)
# invariants:
#   - Never calls get_natal() directly; uses NatalContextService.
#   - profile_hash ties today cache to natal context version.
#   - If birth profile changes, cache misses and rebuilds.
#   - meta.cached is true when returned from cache, false on fresh generation.
#   - V2 horizons reuse exact request-local activation, scoring, natal, and advice objects once.
#   - The same resolved runtime identity drives both cache key and public meta
#     version fields.
#   - One pre-cache scoring-family selection drives cache read, sidecar policy,
#     runtime force propagation, public identity, cache write, and horizons.
#   - Runtime selection must match the pre-cache family or fail closed before
#     public payload construction and cache write.
#   - A degraded concrete-advice batch (< 9 non-fallback rows) is never written
#     to the payload cache (conservative false-negative skip allowed; cache
#     poisoning never); any deadline-degraded phase is never cached.
#   - A foreground Today request never schedules calculations for adjacent dates.
#   - The six independent LLM calls (headline, reading, notes, why, concrete
#     advice batch, planet interpretations) are issued concurrently via
#     a bounded request-local task group (10s LLM phase deadline,
#     cancelled+awaited) once their deterministic contexts are ready; concrete
#     advice remains a single 12-sphere batch call and DB session operations
#     stay sequential. A request-level cancellation cancels every child task
#     and consumes all results before re-raise; the phase emits exactly one
#     day.llm_phase_completed event per run (completed|deadline counts).
# emitted_logs: day.payload_built, day.llm_phase_completed,
#   llm.response_rejected (reason=timeout when the LLM phase hits the deadline).
# failure_policy:
#   - Incomplete profile → 409.
#   - Sidecar unavailable → 502/503.
# non_goals:
#   - No direct natal sidecar calls (use NatalContextService).
#   - Speculative adjacent-day materialization disabled.
# END_MODULE_CONTRACT: M-DAY-SERVICE

# START_MODULE_MAP: M-DAY-SERVICE
# public_entrypoints:
#   - TodayService.get_today_payload
#   - TodayService.invalidate_cache
# semantic_blocks:
#   - NATAL_CONTEXT_REUSE: uses NatalContextService for natal facts (W-NATAL-FULL)
#   - TRANSIT_FETCH: calls solarsage_client.get_transits() for fresh transits
#   - PAYLOAD_BUILDER: construct TodayPayload from natal context + transits + LLM
#   - HORIZON_INTEGRATION: request-local V2 horizon pipeline bridge after final advice
#   - REQUEST_SELECTION: pre-cache request-local V1/V2 family snapshot and assertion
#   - CACHE_LAYER: check cache by (user_id, date, profile_hash), store on miss
# owned_tests:
#   - apps/api/tests/test_day_no_birthday_fallback.py
#   - apps/api/tests/test_day_endpoints.py
#   - apps/api/tests/test_today_important.py
# END_MODULE_MAP: M-DAY-SERVICE

from __future__ import annotations

import asyncio
import os
import time
import json
from datetime import UTC, date as Date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState
from app.schemas.day import RelativeDayStatusRead
from app.schemas.today import (
    DayChart,
    DayChartAspect,
    DayChartHouse,
    DayChartTransitPlanet,
    PlanetInfluence,
    SphereScore,
    TodayMeta,
    TodayPayload,
    TodayV2HorizonPipelineAudit,
    TodayV2HorizonPipelineAuditBuilt,
    TodayV2HorizonPipelineAuditUnavailable,
    TopFlag,
)
from app.clients.solarsage_client import get_solarsage_client
from app.db.models import TodayPayloadCache, SemanticLayerCache, UserProfile, DayScoreHistory
from app.services.astro_utils import find_house, strip_prefix
from app.services.day_relative_status import compute_relative_status
from app.services.day_scoring_signals import filter_day_scored_signals
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService  # noqa: F401 -- legacy test patch point
from app.services.day_scoring_runtime_service import (
    DayScoringRuntimeService, should_compute_v2, selected_scoring_version_for_flags,
)
from app.services.cache_key_service import (
    build_today_cache_key, expected_cache_identity, resolve_today_runtime_identity,
)
from app.services.llm_service import LLMService
from app.services.semantic_service import SemanticService
from app.services.day_delta_service import DayDeltaService
from app.services.today_important_service import TodayImportantService
from app.core.versions import (
    SCORING_V2_VERSION,
    SCORING_V2_1_VERSION,
    TODAY_CONTENT_VERSION,
    TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS,
    TODAY_V2_PAYLOAD_VERSION,
    TODAY_V2_2_PAYLOAD_VERSION,
    V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS,
    V2_FRONTEND_PAYLOAD_VERSION,
    V2_4_FRONTEND_PAYLOAD_VERSION,
    TODAY_LLM_PROMPT_VERSION,
)
from app.services.natal_context_service import NatalContextService
from app.services.canon_service import get_canon_versions
from app.services.activation_layer_service import ActivationLayerService
from app.services.today_horizon_integration_service import TodayHorizonIntegrationService
from app.services.today_selection_context import TodaySelectionContext
from app.core.logging import log_event, log_block

# Request-local hard deadline for the Today foreground LLM phase (seconds).
# Ceiling for the LLM work only; sidecar/DB are outside it.
# The structured 12-sphere drilldown output does not fit into the old 10s
# budget on cache miss; configurable via TODAY_LLM_PHASE_DEADLINE_SECONDS.
LLM_PHASE_DEADLINE_SECONDS = float(os.getenv("TODAY_LLM_PHASE_DEADLINE_SECONDS", "25"))


PLANET_LABELS_RU = {
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
    "Node": "Узел",
    "Chiron": "Хирон",
}

ASPECT_LABELS_RU = {
    "conjunction": "соединение",
    "sextile": "секстиль",
    "square": "квадратура",
    "trine": "тригон",
    "opposition": "оппозиция",
}

SOFT_ASPECTS = {"sextile", "trine"}
TENSE_ASPECTS = {"square", "opposition"}


# START_BLOCK: REAL_CALCULATION
class TodayService:
    def __init__(
        self,
        db: AsyncSession,
        horizon_integration_service: TodayHorizonIntegrationService | None = None,
    ):
        self.db = db
        self._horizon_integration_service = (
            horizon_integration_service
            if horizon_integration_service is not None
            else TodayHorizonIntegrationService()
        )

    async def get_today_payload(
        self,
        user_id,
        target_date: Date,
        access_state: ContentAccessState | None,
        skip_prefetch: bool = False,
        *,
        selection_context: TodaySelectionContext | None = None,
    ) -> TodayPayload:
        # START_FUNCTION_CONTRACT: F-M-DAY-SERVICE.get_today_payload
        # purpose: Get TodayPayload for user and date — the main day pipeline.
        # inputs: user_id, target_date, access_state, skip_prefetch (compatibility-only;
        #   week prefetch is disabled), and optional immutable selection_context.
        # returns: TodayPayload with day_status, headline, reading, top_flags, etc.
        # side_effects: reads/writes cache; calls sidecar for transits and LLM for text.
        # emitted_logs: day.payload_built, day.llm_phase_completed, llm.response_rejected (on LLM phase deadline)
        # error_behavior: HTTPException 409 on incomplete profile, 502 on sidecar failure;
        #   raises RuntimeError if a successfully validated natal profile lacks birth identity.
        # END_FUNCTION_CONTRACT: F-M-DAY-SERVICE.get_today_payload
        """
        Get TodayPayload for a user and date.

        W-1.3: returns fixture-backed payload.
        W-3.4: calls solarsage_client for natal + transits.
        W-4.1: normalization layer (raw → AstroSignal[]).
        W-4.2: scoring layer.
        W-5.1: calls llm_service.
        W-5.2: cache layer (check cache first, store on miss).
        W-ACCESS.3: returns preview payload for locked days.
        """
        del skip_prefetch  # compatibility-only; week prefetch is disabled
        # Internal callers may omit access state; the API route performs the real access check.
        if access_state is None:
            access_state = ContentAccessState(state="full")

        # W-ACCESS.3: If locked, return preview payload
        if access_state.state == "locked":
            return await self._build_preview_payload(user_id, target_date, access_state)

        # Get user profile (need it early for profile_hash in cache key)
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one()

        if profile.birth_lat is None or profile.birth_lon is None:
            raise HTTPException(
                status_code=409,
                detail={"message": "Birth coordinates are required", "missingFields": ["birth_lat", "birth_lon"]},
            )

        # W-NATAL-FULL: profile_hash ties today cache to natal context.
        # If user changes birth data, hash changes → cache miss → fresh data.
        profile_hash = NatalContextService.compute_profile_hash(profile)

        # W2: Snapshot one request-local selection family before cache read.
        force_v2 = selection_context.force_v2 if selection_context is not None else False
        selected_scoring_version = selected_scoring_version_for_flags(force_v2=force_v2)
        selected_v2 = str(selected_scoring_version) in (
            str(SCORING_V2_VERSION),
            str(SCORING_V2_1_VERSION),
        )
        compute_v2 = should_compute_v2(force_v2=force_v2)

        # W5: Build versioned cache key for read with expected identity
        cache_key = expected_cache_identity(
            user_id=user_id,
            target_date=target_date.isoformat(),
            profile_hash=profile_hash,
            selected_scoring_version=selected_scoring_version,
        )

        # W-5.2: Check cache first (keyed by user_id + target_date + profile_hash + cache_key_hash)
        cached = await self._get_cached_payload(user_id, target_date, profile_hash, cache_key)
        if cached:
            cached.access = access_state
            return cached

        # W-NATAL-FULL: Use cached natal context instead of direct sidecar call
        context_service = NatalContextService(self.db)
        natal_context = await context_service.get_or_build_natal_context(user_id)
        birth_date = profile.birthday
        birth_tz = profile.birth_tz
        if birth_date is None or birth_tz is None:
            raise RuntimeError("validated natal profile is missing birth identity")

        # Get SolarSage client — only for transits now
        client = get_solarsage_client()

        # Get transits for target date (noon in user's current timezone)
        target_tz = profile.current_tz or profile.birth_tz or "UTC"
        transits = await client.get_transits(
            target_date=target_date.isoformat(),
            target_time="12:00",
            target_tz=target_tz,
        )

        # W-NATAL-FULL: Use the new day-specific normalization path.
        natal_context_dict = natal_context.model_dump(by_alias=False)
        normalization_service = NormalizationService()
        signals = normalization_service.normalize_day(natal_context_dict, transits)

        # W-PHASE-1: Compute DayDelta — compare yesterday vs today signals
        yesterday_signals = await self._get_yesterday_signals(user_id, target_date, profile, client, natal_context_dict)
        if yesterday_signals:
            delta_service = DayDeltaService(yesterday_signals, signals)
            signals = delta_service.compute_deltas()
            new_count = sum(1 for s in signals if s.delta_kind == "new_today")
            peak_count = sum(1 for s in signals if s.delta_kind == "peak_today")
            bg_count = sum(1 for s in signals if s.delta_kind == "background")
            with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="DAY_DELTA"):
                log_event("day.payload_built", level="info",
                          msg=f"[DayDelta] Computed: {len(signals)} signals",
                          payload={"signal_count": len(signals), "new_today": new_count,
                                   "peak": peak_count, "background": bg_count})
        else:
            with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="DAY_DELTA"):
                log_event("day.payload_built", level="info",
                          msg="[DayDelta] No yesterday data — skipping delta computation")

        day_signals = filter_day_scored_signals(signals)

        # W5: Fetch sidecar activation layer when V2 may be computed
        sidecar_layer = None
        # Build current_location only when all three fields are present
        current_location = None
        if (profile.current_lat is not None and profile.current_lon is not None
                and profile.current_tz is not None):
            current_location = {
                "lat": float(profile.current_lat),
                "lon": float(profile.current_lon),
                "tz": profile.current_tz,
            }
        if compute_v2:
            try:
                sidecar_layer = await client.get_activation_layer(
                    birth_date=birth_date.isoformat(),
                    birth_time=profile.birth_time.strftime("%H:%M") if profile.birth_time else "12:00",
                    birth_lat=float(profile.birth_lat),
                    birth_lon=float(profile.birth_lon),
                    birth_tz=birth_tz,
                    target_date=target_date.isoformat(),
                    target_time="12:00",
                    target_tz=profile.current_tz or profile.birth_tz or "UTC",
                    house_system=natal_context_dict.get("house_system", "PLACIDUS"),
                    current_location=current_location,
                )
            except Exception as e:
                if selected_v2:
                    raise  # Fail loudly when V2 is enabled
                # Shadow fail-open logging (only reached when V2 is not enabled)
                with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="V2_SHADOW"):
                    log_event(
                        "scoring.v2_diff",
                        level="warning",
                        msg="V2 shadow mode: sidecar activation-layer failed, using local fallback",
                        payload={
                            "date": target_date.isoformat(),
                            "fallback": "local_activation",
                        },
                        error={
                            "kind": type(e).__name__,
                        },
                    )

        # Build activation layer with optional sidecar layer
        activation_layer = ActivationLayerService().build(
            natal_context=natal_context_dict,
            transits=transits,
            day_signals=day_signals,
            target_date=target_date,
            target_time="12:00",
            target_tz=profile.current_tz or profile.birth_tz or "UTC",
            house_system=natal_context_dict.get("house_system", "PLACIDUS"),
            sidecar_activation_layer=sidecar_layer,
        )

        # W5: V2 dual-run via DayScoringRuntimeService
        runtime = DayScoringRuntimeService()
        dual = runtime.compute(
            day_signals=day_signals,
            activation_layer=activation_layer,
            user_id=user_id,
            target_date=target_date.isoformat(),
            force_v2=force_v2,
        )
        if str(dual.selected_scoring_version) != str(selected_scoring_version):
            raise RuntimeError("Today scoring selection split-brain detected")
        scoring_result = dict(dual.selected_result)
        from app.schemas.normalization import normalize_top_signals
        scoring_result["top_signals"] = normalize_top_signals(scoring_result.get("top_signals", []))

        # Use canonical runtime identity resolver — single source of truth
        # for V1/V2 version family mapping. Selected scoring version is the
        # only family selector; the caller's activation-layer version is
        # retained when non-null.
        identity = resolve_today_runtime_identity(
            selected_scoring_version=dual.selected_scoring_version,
            activation_layer_version=activation_layer.activation_layer_version,
        )
        v2_selected = identity.payload_version in (
            TODAY_V2_PAYLOAD_VERSION,
            TODAY_V2_2_PAYLOAD_VERSION,
        )

        cache_key = build_today_cache_key(
            user_id=user_id,
            target_date=target_date.isoformat(),
            profile_hash=profile_hash,
            calculation_version=identity.calculation_version,
            activation_layer_version=identity.activation_layer_version,
            scoring_version=identity.scoring_version,
            content_version=identity.content_version,
            frontend_payload_version=identity.frontend_payload_version,
        )

        # W-4.3: Build semantic layer
        semantic_service = SemanticService()
        semantic_layer = semantic_service.build_semantic_layer(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
        )

        # Calculate natal background signals
        day_ids = {id(s) for s in day_signals}
        natal_background_signals = [s for s in signals if id(s) not in day_ids]

        # W-4.3: Compute WhyThisHappens section contexts (pre-computed, no LLM)
        why_contexts = semantic_service.build_why_contexts(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
            scoring_result["top_signals"],
            natal_context_dict,
            transits,
            semantic_layer,
            all_signals=signals,
            day_scored_signals=day_signals,
            natal_background_signals=natal_background_signals,
            activation_layer=activation_layer,
        )

        # W-4.3: Cache semantic layer
        await self._cache_semantic_layer(user_id, target_date, semantic_layer, profile_hash, cache_key)

        # Deterministic contexts for every downstream LLM call are fully ready
        # at this point; the six independent LLM calls are issued concurrently
        # via asyncio.gather (DB session operations stay sequential).
        why_evidence_packet = None
        if v2_selected:
            if dual.v2_result is None:
                raise RuntimeError("V2 selected but v2_result is missing")
            from app.services.semantic_v2_service import SemanticV2Service
            why_evidence_packet = SemanticV2Service().build_llm_evidence_packet(
                day_status=scoring_result["day_status"],
                activation_layer=activation_layer,
                scoring_result=dual.v2_result,
                contexts=[],
            )

        # W-PHASE-2: Compute "Today Important" items (deterministic)
        important_service = TodayImportantService()
        important_items = important_service.build_items(
            target_date=target_date,
            timezone=profile.current_tz or profile.birth_tz or "Europe/Moscow",
            natal=natal_context_dict,
            transits=transits,
            signals=signals,
            scoring_result=scoring_result,
            semantic_layer=semantic_layer,
        )
        day_chart = self._build_day_chart(natal_context_dict, transits, signals)
        planet_influences = self._build_planet_influences(day_signals)
        sphere_scores = self._build_sphere_scores(scoring_result["sphere_scores"])

        # W-5.1 + W-4.2 + interpretation: concurrent LLM generation with one
        # request-local hard deadline for the whole foreground LLM phase.
        # All branches start concurrently; completed results are kept;
        # pending branches are cancelled AND awaited at the deadline (no
        # leaked tasks); the existing deterministic/honest fallbacks then
        # apply. Target typical 7-8s, hard LLM phase ceiling 10s — the
        # sidecar/DB work is OUTSIDE this ceiling.
        from app.services.today_interpretation_service import TodayInterpretationService
        llm_service = LLMService()
        interpretation_service = TodayInterpretationService()

        llm_phase_started = time.perf_counter()
        llm_tasks: dict[str, asyncio.Task] = {
            "headline": asyncio.create_task(llm_service.generate_headline(
                scoring_result["day_status"],
                scoring_result["top_signals"],
            )),
            "reading": asyncio.create_task(llm_service.generate_reading(
                scoring_result["day_status"],
                scoring_result["top_signals"],
                scoring_result["sphere_scores"],
            )),
            "notes": asyncio.create_task(llm_service.generate_notes(
                scoring_result["day_status"],
                scoring_result["sphere_scores"],
                semantic_layer.model_dump(),
            )),
            "why": asyncio.create_task(llm_service.generate_why_sections(
                why_contexts,
                semantic_layer,
                evidence_packet=why_evidence_packet,
            )),
            "interpretation": asyncio.create_task(interpretation_service.build(
                target_date=target_date,
                day_status=scoring_result["day_status"],
                scoring_result=scoring_result,
                signals=day_signals,
                semantic_layer=semantic_layer,
                day_chart=day_chart,
                planet_influences=planet_influences,
                sphere_scores=sphere_scores,
                important_items=important_items,
                lunar=None,
                activation_layer=activation_layer if v2_selected else None,
                scoring_v2_result=dual.v2_result if v2_selected else None,
                valence_assessments=getattr(dual, "valence_assessments", None),
            )),
        }
        try:
            done, pending = await asyncio.wait(
                llm_tasks.values(), timeout=LLM_PHASE_DEADLINE_SECONDS
            )
        except BaseException:
            # The request itself was cancelled (or any unexpected failure
            # happened) while the LLM phase was in flight: cancel EVERY
            # unfinished child, consume all results, and re-raise the
            # original exception. No paid provider request keeps running in
            # the background, and force_no_llm never rebuilds after a
            # request-level cancellation.
            for task in llm_tasks.values():
                if not task.done():
                    task.cancel()
            await asyncio.gather(*llm_tasks.values(), return_exceptions=True)
            raise
        timed_out_names = sorted(
            name for name, task in llm_tasks.items() if task in pending
        )
        for task in pending:
            task.cancel()
        if pending:
            # Await every cancellation so no task leaks past the deadline
            # and every result/cancellation is consumed.
            await asyncio.gather(*pending, return_exceptions=True)

        headline = llm_tasks["headline"].result() if llm_tasks["headline"] in done else None
        reading_paragraphs = llm_tasks["reading"].result() if llm_tasks["reading"] in done else None
        notes_text = llm_tasks["notes"].result() if llm_tasks["notes"] in done else None
        why_sections = llm_tasks["why"].result() if llm_tasks["why"] in done else None
        if llm_tasks["interpretation"] in done:
            interpretation_result = llm_tasks["interpretation"].result()
        else:
            # Honest deterministic fallback for the whole interpretation
            # tuple: the same builder with LLM disabled (advice fallback
            # rows, planet interpretation fallback, deterministic summary).
            interpretation_result = await interpretation_service.build(
                target_date=target_date,
                day_status=scoring_result["day_status"],
                scoring_result=scoring_result,
                signals=day_signals,
                semantic_layer=semantic_layer,
                day_chart=day_chart,
                planet_influences=planet_influences,
                sphere_scores=sphere_scores,
                important_items=important_items,
                lunar=None,
                activation_layer=activation_layer if v2_selected else None,
                scoring_v2_result=dual.v2_result if v2_selected else None,
                valence_assessments=getattr(dual, "valence_assessments", None),
                force_no_llm=True,
            )

        llm_phase_duration_ms = (time.perf_counter() - llm_phase_started) * 1000
        with log_block(slice="W-5.1", module="M-TODAY-SERVICE", block="LLM_PHASE_DEADLINE"):
            # Exactly once per foreground LLM phase, on success AND on
            # deadline: structured counts only, never model text/user data.
            log_event(
                "day.llm_phase_completed",
                level="warn" if timed_out_names else "info",
                msg=(
                    f"[LLM] today llm phase {'deadline' if timed_out_names else 'completed'}: "
                    f"completed={len(done)}/{len(llm_tasks)} timed_out={len(pending)}"
                ),
                payload={
                    "outcome": "deadline" if timed_out_names else "completed",
                    "total_branches": len(llm_tasks),
                    "completed_branches": len(done),
                    "timed_out_branches": len(pending),
                    "deadline_ms": int(LLM_PHASE_DEADLINE_SECONDS * 1000),
                },
                duration_ms=llm_phase_duration_ms,
            )
        if timed_out_names:
            with log_block(slice="W-5.1", module="M-TODAY-SERVICE", block="LLM_PHASE_DEADLINE"):
                log_event(
                    "llm.response_rejected",
                    level="warn",
                    msg=(
                        f"[LLM] today llm phase deadline: "
                        f"completed={len(done)} timed_out={len(pending)} branches={','.join(timed_out_names)}"
                    ),
                    payload={"reason": "timeout"},
                    duration_ms=llm_phase_duration_ms,
                )

        concrete_advice, day_summary, updated_day_chart = interpretation_result

        # W-4.2: Build top_flags from top signals
        top_flags = self._build_top_flags(scoring_result["top_signals"])

        # W-3.4: Build minimal TodayPayload from raw data
        # W-4.2: Add scoring layer
        # W-5.1: Add LLM-generated text
        # W-5.2: meta.cached = False (fresh generation)

        # Fallback for LLM failures — show placeholder text so tests catch it
        if not headline:
            headline = "Ваш персональный разбор дня"
        if not reading_paragraphs:
            reading_paragraphs = ["Данные временно недоступны. Пожалуйста, попробуйте позже."]
        if not notes_text:
            notes_text = "Данные временно недоступны"
        if not why_sections:
            why_sections = [{
                "id": "why-fallback",
                "title": "Данные временно недоступны",
                "blocks": [{"kind": "paragraph", "text": "Пожалуйста, попробуйте позже."}],
            }]

        v2_block = None
        if v2_selected:
            if dual.v2_result is None:
                raise RuntimeError("V2 selected but v2_result is missing")
            from app.services.semantic_v2_service import SemanticV2Service
            horizon_result = self._horizon_integration_service.build(
                activation_layer=activation_layer,
                scoring_result=dual.v2_result,
                natal_context=natal_context,
                concrete_advice=concrete_advice,
            )
            horizon_pipeline_audit: TodayV2HorizonPipelineAudit
            if horizon_result.status == "built":
                horizon_pipeline_audit = TodayV2HorizonPipelineAuditBuilt(
                    status="built",
                    reason="selected",
                    selected_count=3,
                )
            else:
                horizon_pipeline_audit = TodayV2HorizonPipelineAuditUnavailable(
                    status="unavailable",
                    reason=horizon_result.selection_reason,
                    selected_count=0,
                )
            v2_block = SemanticV2Service().build_v2_block(
                activation_layer=activation_layer,
                scoring_result=dual.v2_result,
                v1_v2_diff=dual.diff,
                trace_id=getattr(dual, "trace_id", None),
                horizons=horizon_result.horizons,
                horizon_pipeline_audit=horizon_pipeline_audit,
                selected_identity=identity,
                valence_breakdown=dual.valence_breakdown,
            )

        # W-DAY: relative status calculation and history persistence
        if dual.v2_result is not None:
            today_support = float(dual.v2_result.status_breakdown.get("support_score", 0.0))
            today_tension = float(dual.v2_result.status_breakdown.get("tension_score", 0.0))
        else:
            from app.services.scoring_v2_service import ScoringV2Service
            v2_fb = ScoringV2Service().score_day(day_signals, activation_layer)
            today_support = float(v2_fb.status_breakdown.get("support_score", 0.0))
            today_tension = float(v2_fb.status_breakdown.get("tension_score", 0.0))

        relative_status = await self._record_and_compute_relative_status(
            user_id=user_id,
            target_date=target_date,
            support_score=today_support,
            tension_score=today_tension,
            absolute_v2_status=scoring_result["day_status"],
        )

        payload = TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=3,
                calculation_version=identity.calculation_version,
                normalization_version=1,
                scoring_version=identity.scoring_version,
                prompt_version=TODAY_LLM_PROMPT_VERSION,
                content_version=identity.content_version,
                generated_at=datetime.now(UTC).isoformat(),
                cached=False,  # W-5.2: Fresh generation
                canon_versions=get_canon_versions(),
                activation_layer_version=identity.activation_layer_version,
                payload_version=identity.payload_version,
                frontend_payload_version=identity.frontend_payload_version,
            ),
            date=target_date.isoformat(),
            title="Сегодня",
            subtitle=None,
            headline=headline,
            access=access_state.model_dump(by_alias=True),
            day_status=scoring_result["day_status"],
            day_summary=day_summary,
            concrete_advice=concrete_advice,
            day_quality=None,
            top_flags=top_flags,
            notes=notes_text,
            reading={"paragraphs": reading_paragraphs},
            why_this_happens={"sections": why_sections},
            week_strip=[
                {
                    "date": (target_date + timedelta(days=i - 3)).isoformat(),
                    "day_status": "steady",
                    "is_today": i == 3,
                }
                for i in range(7)
            ],
            microcopy=[],
            yesterday_echo=None,
            important_today=important_items,
            relative_status=relative_status,
            actions=None,
            day_chart=updated_day_chart,
            planet_influences=planet_influences,
            sphere_scores=sphere_scores,
            v2=v2_block,
        )

        # Defensive contract invariants: V2 identity requires a non-null V2 body.
        if payload.meta.payload_version in (
            TODAY_V2_PAYLOAD_VERSION,
            TODAY_V2_2_PAYLOAD_VERSION,
        ) and payload.v2 is None:
            raise RuntimeError("current V2 payload identity requires v2 block")
        if payload.meta.frontend_payload_version in (
            V2_FRONTEND_PAYLOAD_VERSION,
            V2_4_FRONTEND_PAYLOAD_VERSION,
        ) and payload.v2 is None:
            raise RuntimeError("current frontend V2 identity requires v2 block")

        # W-5.2: Cache payload (with profile_hash in key) — but NEVER cache a
        # degraded concrete-advice batch (fewer than 9 non-fallback rows after
        # the single advice call is rejected) and NEVER cache a
        # deadline-degraded phase (any timed-out branch leaves placeholder
        # text). A conservative false-negative skip is fine; cache poisoning
        # is not.
        from app.services.today_interpretation_service import (
            CONCRETE_ADVICE_CACHEABLE_MIN_ROWS,
            CONCRETE_ADVICE_FALLBACK_TEXT,
        )
        non_fallback_advice = len([
            advice_row
            for advice_row in (payload.concrete_advice.rows if payload.concrete_advice else [])
            if advice_row.text != CONCRETE_ADVICE_FALLBACK_TEXT
        ])
        # A deadline-degraded phase is also never cached: a payload carrying
        # placeholder text from any timed-out branch would poison every
        # later read, even when the advice batch itself validated.
        if non_fallback_advice >= CONCRETE_ADVICE_CACHEABLE_MIN_ROWS and not timed_out_names:
            await self._cache_payload(user_id, target_date, payload, profile_hash, cache_key)

        return payload

    @staticmethod
    def _build_top_flags(signals: list) -> list[TopFlag]:
        return [
            flag
            for signal in signals[:3]
            if (flag := TodayService._build_top_flag(signal)) is not None
        ]

    @staticmethod
    def _build_top_flag(signal) -> TopFlag | None:
        planet = TodayService._planet_label(signal.planet)
        icon_planet = strip_prefix(signal.planet) or "planet"

        if signal.type == "aspect" and signal.aspect_type and signal.target_planet:
            target = TodayService._planet_label(signal.target_planet)
            aspect = ASPECT_LABELS_RU.get(signal.aspect_type, "аспект")
            return TopFlag(
                icon_name=f"{icon_planet}-{signal.aspect_type}",
                title=f"{planet} {aspect} {target}",
                summary=TodayService._top_flag_aspect_summary(signal.aspect_type),
                hint=None,
            )

        if signal.type == "planet_in_house" and signal.house:
            return TopFlag(
                icon_name=f"{icon_planet}-house",
                title=f"{planet} в {signal.house} доме",
                summary="Акцент дня: эта тема заметнее обычного, полезно выбрать один практический шаг.",
                hint=None,
            )

        return None

    @staticmethod
    def _planet_label(name: str | None) -> str:
        stripped = strip_prefix(name)
        if not stripped:
            return "Планета"
        return PLANET_LABELS_RU.get(stripped, "Планета")

    @staticmethod
    def _top_flag_aspect_summary(aspect_type: str) -> str:
        if aspect_type in SOFT_ASPECTS:
            return "Поддерживающий аспект: легче договориться, связать идеи и действия."
        if aspect_type in TENSE_ASPECTS:
            return "Напряжённый аспект: лучше снизить резкость и перепроверить реакцию."
        return "Заметный аспект: тема дня может звучать сильнее обычного, лучше действовать без спешки."

    @staticmethod
    def _build_day_chart(
        natal_context: dict,
        transits: dict,
        signals: list,
    ) -> DayChart | None:
        houses_raw = natal_context.get("houses") or []
        transit_planets_raw = transits.get("planets") or []
        if not houses_raw and not transit_planets_raw:
            return None

        houses = [
            DayChartHouse(
                number=int(house["number"]),
                cusp_longitude=round(
                    float(house.get("longitude", house.get("cusp", 0.0))),
                    4,
                ),
                sign=house.get("sign"),
            )
            for house in houses_raw
            if house.get("number") is not None
        ]

        transit_planets = []
        for planet in transit_planets_raw:
            longitude = float(planet["longitude"])
            speed = planet.get("speed")
            retrograde = planet.get("retrograde")
            motion = None
            if speed is not None and abs(float(speed)) < 0.01:
                motion = "stationary"
            elif retrograde is True or (speed is not None and float(speed) < 0):
                motion = "retrograde"
            elif speed is not None or retrograde is False:
                motion = "direct"

            transit_planets.append(DayChartTransitPlanet(
                name=strip_prefix(planet.get("name")),
                longitude=round(longitude, 4),
                sign=planet.get("sign"),
                retrograde=retrograde,
                speed=float(speed) if speed is not None else None,
                motion=motion,
                house=planet.get("house") or find_house(longitude, houses_raw),
            ))

        aspects = [
            DayChartAspect(
                planet=strip_prefix(signal.planet),
                target_planet=strip_prefix(signal.target_planet),
                aspect_type=signal.aspect_type or "",
                orb=round(signal.orb, 4) if signal.orb is not None else None,
                strength=round(signal.strength, 4),
            )
            for signal in signals
            if signal.type == "aspect"
            and signal.aspect_type
            and signal.target_planet
            and (signal.planet or "").startswith("Transit_")
        ]

        return DayChart(
            source="solarsage",
            houses=houses,
            transit_planets=transit_planets,
            aspects=aspects,
        )

    @staticmethod
    def _build_planet_influences(signals: list) -> list[PlanetInfluence]:
        scores: dict[str, float] = {}
        for signal in signals:
            planet = strip_prefix(signal.planet)
            if planet:
                scores[planet] = scores.get(planet, 0.0) + float(signal.strength)
            target = strip_prefix(signal.target_planet)
            if target:
                scores[target] = scores.get(target, 0.0) + float(signal.strength) * 0.5

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [
            PlanetInfluence(name=name, score=round(score, 4), rank=index)
            for index, (name, score) in enumerate(ranked, start=1)
        ]

    @staticmethod
    def _build_sphere_scores(scores: dict[str, float]) -> list[SphereScore]:
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [
            SphereScore(key=key, score=round(float(score), 4), rank=index)
            for index, (key, score) in enumerate(ranked, start=1)
        ]

    async def _get_cached_payload(self, user_id, target_date: Date, profile_hash: str, cache_key=None) -> TodayPayload | None:
        """Get cached payload if exists. W-5.2.

        W-NATAL-FULL: profile_hash is part of the cache key.
        W5: Queries by cache_key_hash for versioned cache identity.
        """
        conditions = [
            TodayPayloadCache.user_id == user_id,
            TodayPayloadCache.target_date == target_date,
            TodayPayloadCache.profile_hash == profile_hash,
        ]
        if cache_key:
            conditions.append(TodayPayloadCache.cache_key_hash == cache_key.cache_key_hash)

        result = await self.db.execute(
            select(TodayPayloadCache).where(*conditions)
        )
        cache_entry = result.scalar_one_or_none()

        if not cache_entry:
            return None

        payload_dict = json.loads(cache_entry.payload_json)
        meta = payload_dict.get("meta") or {}
        content_version = meta.get("contentVersion", meta.get("content_version"))
        if content_version != TODAY_CONTENT_VERSION:
            return None

        # Treat legacy bad V2 cache rows as miss: V2 identity without v2 body.
        payload_version = meta.get("payload_version", meta.get("payloadVersion"))
        frontend_version = meta.get("frontend_payload_version", meta.get("frontendPayloadVersion"))
        v2_block = payload_dict.get("v2", payload_dict.get("V2"))
        if payload_version in TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS and v2_block is None:
            return None
        if frontend_version in V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS and v2_block is None:
            return None

        try:
            payload = TodayPayload(**payload_dict)
        except Exception:
            # Invalid/legacy cache rows must not crash the request path.
            return None
        payload.meta.cached = True
        return payload

    async def _cache_payload(self, user_id, target_date: Date, payload: TodayPayload, profile_hash: str, cache_key=None) -> None:
        """Cache payload. W-5.2.

        W-NATAL-FULL: profile_hash is part of the cache key.
        W5: Stores versioned cache columns.
        """
        payload_json = payload.model_dump_json()

        # Upsert cache entry (keyed by user_id + target_date + profile_hash + cache_key_hash)
        conditions = [
            TodayPayloadCache.user_id == user_id,
            TodayPayloadCache.target_date == target_date,
            TodayPayloadCache.profile_hash == profile_hash,
        ]
        if cache_key:
            conditions.append(TodayPayloadCache.cache_key_hash == cache_key.cache_key_hash)

        result = await self.db.execute(
            select(TodayPayloadCache).where(*conditions)
        )
        existing = result.scalar_one_or_none()

        ch = cache_key.cache_key_hash if cache_key else ""

        if existing:
            existing.payload_json = payload_json
            existing.cache_key_hash = ch
            existing.created_at = datetime.now(UTC)
        else:
            cache_entry = TodayPayloadCache(
                user_id=user_id,
                target_date=target_date,
                profile_hash=profile_hash,
                payload_json=payload_json,
                cache_key_hash=ch,
                calculation_version=cache_key.calculation_version if cache_key else "1",
                activation_layer_version=cache_key.activation_layer_version if cache_key else None,
                scoring_version=str(cache_key.scoring_version) if cache_key else "1",
                canon_versions_hash=cache_key.canon_versions_hash if cache_key else "",
                llm_prompt_version=cache_key.llm_prompt_version if cache_key else TODAY_LLM_PROMPT_VERSION,
                frontend_payload_version=cache_key.frontend_payload_version if cache_key else 1,
            )
            self.db.add(cache_entry)

        await self.db.commit()

    async def invalidate_cache(self, user_id) -> None:
        # START_FUNCTION_CONTRACT: F-M-DAY-SERVICE.invalidate_cache
        # purpose: Invalidate all cached today payloads for user.
        # inputs: user_id
        # returns: None
        # side_effects: deletes TodayPayloadCache rows for user
        # emitted_logs: profile.cache_invalidated
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-DAY-SERVICE.invalidate_cache
        """Invalidate all cached payloads for user (e.g., after profile edit). W-5.2."""
        await self.db.execute(
            delete(TodayPayloadCache).where(TodayPayloadCache.user_id == user_id)
        )
        await self.db.execute(
            delete(SemanticLayerCache).where(SemanticLayerCache.user_id == user_id)
        )
        await self.db.commit()

    async def _cache_semantic_layer(self, user_id, target_date: Date, semantic_layer, profile_hash: str, cache_key=None) -> None:
        """Cache semantic layer. W-4.3. W5: stores versioned cache identity."""
        cache_data = {
            "profile_hash": profile_hash,
            "content_version": TODAY_CONTENT_VERSION,
            "semantic_layer": semantic_layer.model_dump(),
            "cache_key_hash": cache_key.cache_key_hash if cache_key else "",
            "calculation_version": cache_key.calculation_version if cache_key else "1",
            "activation_layer_version": cache_key.activation_layer_version if cache_key else None,
            "scoring_version": str(cache_key.scoring_version) if cache_key else "1",
            "canon_versions_hash": cache_key.canon_versions_hash if cache_key else "",
            "llm_prompt_version": cache_key.llm_prompt_version if cache_key else TODAY_LLM_PROMPT_VERSION,
            "frontend_payload_version": cache_key.frontend_payload_version if cache_key else 1,
        }
        semantic_json = json.dumps(cache_data)

        result = await self.db.execute(
            select(SemanticLayerCache).where(
                SemanticLayerCache.user_id == user_id,
                SemanticLayerCache.target_date == target_date,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.semantic_json = semantic_json
            existing.created_at = datetime.now(UTC)
        else:
            cache_entry = SemanticLayerCache(
                user_id=user_id,
                target_date=target_date,
                semantic_json=semantic_json,
            )
            self.db.add(cache_entry)

        await self.db.commit()

    async def _build_preview_payload(
        self,
        user_id,
        target_date: Date,
        access_state: ContentAccessState,
    ) -> TodayPayload:
        """Build preview payload for locked day. W-ACCESS.3."""
        from app.schemas.today import ConcreteAdviceBlock, ConcreteAdviceCounts, DaySummaryBlock
        return TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=3,
                calculation_version=1,
                normalization_version=1,
                scoring_version=1,
                prompt_version=TODAY_LLM_PROMPT_VERSION,
                content_version=TODAY_CONTENT_VERSION,
                generated_at=datetime.now(UTC).isoformat(),
                cached=False,
                canon_versions=get_canon_versions(),
            ),
            date=target_date.isoformat(),
            title="Сегодня",
            subtitle=None,
            headline="Этот день доступен по подписке",
            access=access_state.model_dump(by_alias=True),
            day_status="steady",  # Neutral for preview
            day_summary=DaySummaryBlock(
                status_label="День заблокирован",
                status_line="Подпишитесь, чтобы увидеть разбор",
                facts=[]
            ),
            concrete_advice=ConcreteAdviceBlock(
                rows=[],
                counts=ConcreteAdviceCounts(good=0, caution=0, avoid=0, neutral=0)
            ),
            day_quality=None,
            top_flags=[],
            reading={"paragraphs": ["Подпишитесь, чтобы увидеть полный прогноз."]},
            why_this_happens={"sections": []},
            week_strip=[
                {
                    "date": (target_date + timedelta(days=i - 3)).isoformat(),
                    "day_status": "steady",
                    "is_today": i == 3,
                }
                for i in range(7)
            ],
            microcopy=[],
            yesterday_echo=None,
            actions=None,
        )
# END_BLOCK: REAL_CALCULATION

    async def _get_yesterday_signals(self, user_id, today: Date, profile, client, natal_context_dict: dict) -> list | None:
        """Get yesterday's normalized signals for DayDelta comparison.
        Returns None if yesterday's data can't be computed."""
        yesterday = today - timedelta(days=1)
        try:
            y_transits = await client.get_transits(
                target_date=yesterday.isoformat(),
                target_time="12:00",
                target_tz=profile.birth_tz or "UTC",
            )
            normalization_service = NormalizationService()
            y_signals = normalization_service.normalize_day(natal_context=natal_context_dict, transits=y_transits)
            return y_signals
        except Exception as e:
            with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="DAY_DELTA"):
                log_event(
                    "day.payload_built",
                    level="warn",
                    msg=f"[DayDelta] Could not get yesterday signals: {type(e).__name__}",
                )
            return None

    async def _record_and_compute_relative_status(
        self,
        user_id: UUID,
        target_date: Date,
        support_score: float,
        tension_score: float,
        absolute_v2_status: str,
    ) -> RelativeDayStatusRead:
        """Upsert today's scores into day_score_history and compute 14-day relative status."""
        stmt_upsert = pg_insert(DayScoreHistory).values(
            user_id=user_id,
            target_date=target_date,
            support_score=support_score,
            tension_score=tension_score,
        ).on_conflict_do_update(
            index_elements=["user_id", "target_date"],
            set_={
                "support_score": support_score,
                "tension_score": tension_score,
            },
        )
        await self.db.execute(stmt_upsert)
        await self.db.commit()

        stmt_history = (
            select(DayScoreHistory.support_score, DayScoreHistory.tension_score)
            .where(
                DayScoreHistory.user_id == user_id,
                DayScoreHistory.target_date < target_date,
                DayScoreHistory.target_date >= target_date - timedelta(days=14),
            )
            .order_by(DayScoreHistory.target_date.desc())
            .limit(14)
        )
        res = await self.db.execute(stmt_history)
        history_rows = [
            {"support": float(row.support_score), "tension": float(row.tension_score)}
            for row in res.all()
        ]

        return compute_relative_status(
            today_support=support_score,
            today_tension=tension_score,
            absolute_v2_status=absolute_v2_status,
            history=history_rows,
        )
