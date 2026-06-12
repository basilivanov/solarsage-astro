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
from app.schemas.today import TodayPayload, TodayMeta, TopFlag
from app.clients.solarsage_client import get_solarsage_client
from app.db.models import TodayPayloadCache, SemanticLayerCache, UserProfile
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService
from app.services.semantic_service import SemanticService
from app.services.day_delta_service import DayDeltaService
from app.services.today_important_service import TodayImportantService
from app.services.natal_context_service import NatalContextService
from app.core.logging import log_event, log_block


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
        scoring_service = ScoringService()
        scoring_result = scoring_service.score_day(signals)

        # W-4.3: Build semantic layer
        semantic_service = SemanticService()
        semantic_layer = semantic_service.build_semantic_layer(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
        )

        # W-4.3: Compute WhyThisHappens section contexts (pre-computed, no LLM)
        why_contexts = semantic_service.build_why_contexts(
            scoring_result["day_status"],
            scoring_result["sphere_scores"],
            scoring_result["top_signals"],
            natal_context_dict,
            transits,
            semantic_layer,
            signals,
        )

        # W-4.3: Cache semantic layer
        await self._cache_semantic_layer(user_id, target_date, semantic_layer)

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
        top_flags = []
        for signal in scoring_result["top_signals"][:3]:  # Top 3
            planet = (signal.planet or "").replace("Transit_", "").replace("Natal_", "")
            if signal.type == "aspect":
                target = (signal.target_planet or "").replace("Transit_", "").replace("Natal_", "")
                top_flags.append(TopFlag(
                    icon_name=f"{planet}-{signal.aspect_type}",
                    title=f"{planet} {signal.aspect_type} {target}",
                    summary=f"Orb: {signal.orb:.1f}°, Strength: {signal.strength:.2f}",
                    hint=None,
                ))
            elif signal.type == "planet_in_house":
                top_flags.append(TopFlag(
                    icon_name=f"{planet}-house",
                    title=f"{planet} в {signal.house} доме",
                    summary=f"Strength: {signal.strength:.2f}",
                    hint=None,
                ))

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

        payload = TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=2,
                calculation_version=1,
                normalization_version=1,
                scoring_version=1,
                prompt_version=1,
                content_version=1,
                generated_at=datetime.now(UTC).isoformat(),
                cached=False,  # W-5.2: Fresh generation
            ),
            date=target_date.isoformat(),
            title="Сегодня",
            subtitle=None,
            headline=headline,
            access=access_state.model_dump(by_alias=True),
            day_status=scoring_result["day_status"],
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
        )

        # W-5.2: Cache payload (with profile_hash in key)
        await self._cache_payload(user_id, target_date, payload, profile_hash)

        # W-5.2: Prefetch week in background (don't block user)
        if not skip_prefetch:
            asyncio.ensure_future(self._prefetch_week(user_id, target_date))

        return payload

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
        await self.db.commit()

    async def _cache_semantic_layer(self, user_id, target_date: Date, semantic_layer) -> None:
        """Cache semantic layer. W-4.3."""
        semantic_json = semantic_layer.model_dump_json()

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
        return TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=2,
                calculation_version=1,
                normalization_version=1,
                scoring_version=1,
                prompt_version=1,
                content_version=1,
                generated_at=datetime.now(UTC).isoformat(),
                cached=False,
            ),
            date=target_date.isoformat(),
            title="Сегодня",
            subtitle=None,
            headline="Этот день доступен по подписке",
            access=access_state.model_dump(by_alias=True),
            day_status="steady",  # Neutral for preview
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
