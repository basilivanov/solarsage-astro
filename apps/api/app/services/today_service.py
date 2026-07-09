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
# invariants:
#   - Never calls get_natal() directly; uses NatalContextService.
#   - profile_hash ties today cache to natal context version.
#   - If birth profile changes, cache misses and rebuilds.
#   - meta.cached is true when returned from cache, false on fresh generation.
# failure_policy:
#   - Incomplete profile → 409.
#   - Sidecar unavailable → 502/503.
# non_goals:
#   - No direct natal sidecar calls (use NatalContextService).
# END_MODULE_CONTRACT: M-DAY-SERVICE

# START_MODULE_MAP: M-DAY-SERVICE
# public_entrypoints:
#   - TodayService.get_today_payload
#   - TodayService.invalidate_cache
# semantic_blocks:
#   - NATAL_CONTEXT_REUSE: uses NatalContextService for natal facts (W-NATAL-FULL)
#   - TRANSIT_FETCH: calls solarsage_client.get_transits() for fresh transits
#   - PAYLOAD_BUILDER: construct TodayPayload from natal context + transits + LLM
#   - CACHE_LAYER: check cache by (user_id, date, profile_hash), store on miss
# owned_tests:
#   - apps/api/tests/test_day_no_birthday_fallback.py
#   - apps/api/tests/test_day_endpoints.py
#   - apps/api/tests/test_today_important.py
# END_MODULE_MAP: M-DAY-SERVICE

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date as Date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState
from app.schemas.today import (
    DayChart,
    DayChartAspect,
    DayChartHouse,
    DayChartTransitPlanet,
    PlanetInfluence,
    SphereScore,
    TodayMeta,
    TodayPayload,
    TopFlag,
)
from app.clients.solarsage_client import get_solarsage_client
from app.db.models import TodayPayloadCache, SemanticLayerCache, UserProfile
from app.services.astro_utils import find_house, strip_prefix
from app.services.day_scoring_signals import filter_day_scored_signals
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService
from app.services.semantic_service import SemanticService
from app.services.day_delta_service import DayDeltaService
from app.services.today_important_service import TodayImportantService
from app.services.natal_context_service import NatalContextService
from app.services.canon_service import get_canon_versions
from app.core.logging import log_event, log_block


TODAY_CONTENT_VERSION = 7

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
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_today_payload(
        self,
        user_id,
        target_date: Date,
        access_state: ContentAccessState | None,
        skip_prefetch: bool = False,
    ) -> TodayPayload:
        # START_FUNCTION_CONTRACT: F-M-DAY-SERVICE.get_today_payload
        # purpose: Get TodayPayload for user and date — the main day pipeline.
        # inputs: user_id, target_date (Date), access_state (ContentAccessState | None), skip_prefetch (bool)
        # returns: TodayPayload with day_status, headline, reading, top_flags, etc.
        # side_effects: reads/writes cache, calls sidecar for transits, calls LLM for text
        # emitted_logs: day.payload_built (TODO: W-1.6 — add day.viewed in API route)
        # error_behavior: HTTPException 409 on incomplete profile, 502 on sidecar failure
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
        # Default access state for prefetch (real state checked on-demand by API route)
        if access_state is None:
            access_state = ContentAccessState(state="full", reason="cached_prefetch", referralDaysLeft=None, subscriptionActive=None, accessUntil=None)

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

        # W-5.2: Check cache first (keyed by user_id + target_date + profile_hash)
        cached = await self._get_cached_payload(user_id, target_date, profile_hash)
        if cached:
            # Update access state (may have changed since cache)
            cached.access = access_state
            return cached

        # W-NATAL-FULL: Use cached natal context instead of direct sidecar call
        context_service = NatalContextService(self.db)
        natal_context = await context_service.get_or_build_natal_context(user_id)

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
        # normalize_day() uses cached natal context + fresh transits.
        # score_day() is the day scoring method (includes day_status).
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
                log_event(
                    "day.payload_built",
                    level="info",
                    msg=f"[DayDelta] Computed: {len(signals)} signals",
                    payload={
                        "signal_count": len(signals),
                        "new_today": new_count,
                        "peak": peak_count,
                        "background": bg_count,
                    },
                )
        else:
            with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="DAY_DELTA"):
                log_event(
                    "day.payload_built",
                    level="info",
                    msg="[DayDelta] No yesterday data — skipping delta computation",
                )

        # W-4.2: Score signals and calculate day_status using day-specific scorer
        day_signals = filter_day_scored_signals(signals)
        scoring_service = ScoringService()
        scoring_result = scoring_service.score_day(day_signals)

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
            activation_layer=None,
        )

        # W-4.3: Cache semantic layer
        await self._cache_semantic_layer(user_id, target_date, semantic_layer, profile_hash)

        # W-5.1: Generate text via LLM
        llm_service = LLMService()
        headline = await llm_service.generate_headline(
            scoring_result["day_status"],
            scoring_result["top_signals"],
        )
        reading_paragraphs = await llm_service.generate_reading(
            scoring_result["day_status"],
            scoring_result["top_signals"],
            scoring_result["sphere_scores"],
        )

        # W-4.2: Build day notes via LLM
        notes_text = await llm_service.generate_notes(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
            semantic_layer,
        )

        # W-4.2: Build why-this-happens sections via LLM
        why_sections = await llm_service.generate_why_sections(
            why_contexts,
            semantic_layer,
        )

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

        # Call interpretation service to build concrete advice and summary facts
        from app.services.today_interpretation_service import TodayInterpretationService
        interpretation_service = TodayInterpretationService()
        concrete_advice, day_summary, updated_day_chart = await interpretation_service.build(
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
        )

        payload = TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=3,
                calculation_version=1,
                normalization_version=1,
                scoring_version=1,
                prompt_version=2,
                content_version=TODAY_CONTENT_VERSION,
                generated_at=datetime.now(UTC).isoformat(),
                cached=False,  # W-5.2: Fresh generation
                canon_versions=get_canon_versions(),
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
            actions=None,
            day_chart=updated_day_chart,
            planet_influences=planet_influences,
            sphere_scores=sphere_scores,
        )

        # W-5.2: Cache payload (with profile_hash in key)
        await self._cache_payload(user_id, target_date, payload, profile_hash)

        # W-5.2: Prefetch week in background (don't block user)
        if not skip_prefetch:
            asyncio.ensure_future(self._prefetch_week(user_id, target_date))

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

    async def _get_cached_payload(self, user_id, target_date: Date, profile_hash: str) -> TodayPayload | None:
        """Get cached payload if exists. W-5.2.

        W-NATAL-FULL: profile_hash is part of the cache key. If user changes
        birth data, the hash changes → cache miss → fresh generation.
        This proves today cache is tied to natal context.
        """
        result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
                TodayPayloadCache.profile_hash == profile_hash,
            )
        )
        cache_entry = result.scalar_one_or_none()

        if not cache_entry:
            return None

        # Deserialize JSON
        payload_dict = json.loads(cache_entry.payload_json)
        meta = payload_dict.get("meta") or {}
        content_version = meta.get("contentVersion", meta.get("content_version"))
        if content_version != TODAY_CONTENT_VERSION:
            return None

        payload = TodayPayload(**payload_dict)

        # Mark as cached
        payload.meta.cached = True

        return payload

    async def _cache_payload(self, user_id, target_date: Date, payload: TodayPayload, profile_hash: str) -> None:
        """Cache payload. W-5.2.

        W-NATAL-FULL: profile_hash is part of the cache key.
        """
        # Serialize to JSON
        payload_json = payload.model_dump_json()

        # Upsert cache entry (keyed by user_id + target_date + profile_hash)
        result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
                TodayPayloadCache.profile_hash == profile_hash,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.payload_json = payload_json
            existing.created_at = datetime.now(UTC)
        else:
            cache_entry = TodayPayloadCache(
                user_id=user_id,
                target_date=target_date,
                profile_hash=profile_hash,
                payload_json=payload_json,
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

    async def _cache_semantic_layer(self, user_id, target_date: Date, semantic_layer, profile_hash: str) -> None:
        """Cache semantic layer. W-4.3."""
        cache_data = {
            "profile_hash": profile_hash,
            "content_version": TODAY_CONTENT_VERSION,
            "semantic_layer": semantic_layer.model_dump(),
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
                prompt_version=2,
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

    async def _prefetch_week(self, user_id, today: Date) -> None:
        """Prefetch 7 days of payloads in background. W-5.2.

        Delegates to get_today_payload(skip_prefetch=True) which handles
        cache check internally with the correct profile_hash.
        Errors are logged at debug level but do not break the app.
        """
        days = [today + timedelta(days=i) for i in range(-3, 4)]  # today ±3 days

        async def _calc_one(day: Date):
            try:
                await self.get_today_payload(user_id, day, None, skip_prefetch=True)
            except Exception:
                with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="PREFETCH_WEEK"):
                    log_event(
                        "day.payload_built",
                        level="warn",
                        msg=f"Prefetch failed for day {day}",
                    )

        tasks = [_calc_one(d) for d in days]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="PREFETCH_WEEK"):
                log_event(
                    "day.payload_built",
                    level="warn",
                    msg="Prefetch week gather failed",
                )
