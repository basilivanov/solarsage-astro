# AI_HEADER
# module: M-DAY-SERVICE
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-1.3 (fixture-backed), W-3.4 (real pipeline), W-4.1 (normalization), W-4.2 (scoring), W-5.1 (LLM), W-5.2 (cache)
# purpose: TodayService returns TodayPayload for a given user and date.

# START_MODULE_CONTRACT: M-DAY-SERVICE
# purpose: Get TodayPayload for a user and date.
#          W-1.3: returns fixture-backed payload.
#          W-3.4: calls solarsage_client for natal + transits.
#          W-4.3: calls semantic_layer_service.
#          W-5.1: calls llm_service.
#          W-5.2: cache layer (check cache first, store on miss).
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
#   - M-SOLARSAGE-CLIENT (get_solarsage_client)
#   - M-LLM-SERVICE (W-5.1)
# invariants:
#   - W-1.3: loads fixture from apps/api/app/fixtures/day_*.json.
#   - W-3.4: calls solarsage_client.get_natal() and get_transits().
#   - W-5.2: meta.cached is true when returned from cache, false on fresh generation.
# failure_policy:
#   - W-3.4: calculation error → 500.
#   - missing profile → 404.
# non_goals:
#   - no LLM generation (W-5.1)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-DAY-SERVICE
# public_entrypoints:
#   - TodayService.get_today_payload
#   - TodayService.invalidate_cache (W-5.2)
# semantic_blocks:
#   - REAL_CALCULATION: call solarsage_client for natal + transits (W-3.4)
#   - PAYLOAD_BUILDER: construct TodayPayload from raw data
#   - CACHE_LAYER: check cache, store on miss (W-5.2)
# owned_tests:
#   - apps/api/tests/test_today_service.py
#   - apps/api/tests/test_cache.py (W-5.2)
# END_MODULE_MAP

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date as Date, datetime, timedelta
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

logger = logging.getLogger(__name__)


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

        # W-5.2: Check cache first
        cached = await self._get_cached_payload(user_id, target_date)
        if cached:
            # Update access state (may have changed since cache)
            cached.access = access_state
            return cached

        # Get user profile
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one()

        # Get SolarSage client
        client = get_solarsage_client()

        # Get natal chart
        natal = await client.get_natal(
            birth_date=profile.birthday.isoformat(),
            birth_time=profile.birth_time.strftime("%H:%M") if profile.birth_time else "12:00",
            birth_lat=float(profile.birth_lat),
            birth_lon=float(profile.birth_lon),
            birth_tz=profile.birth_tz or "UTC",
        )

        # Get transits for target date (noon in user's current timezone)
        # W-3.4: use birth_tz as current_tz (proper current_tz tracking deferred)
        transits = await client.get_transits(
            target_date=target_date.isoformat(),
            target_time="12:00",
            target_tz=profile.birth_tz or "UTC",
        )

        # W-4.1: Normalize raw data into AstroSignal[]
        normalization_service = NormalizationService()
        signals = normalization_service.normalize(natal, transits)

        # W-PHASE-1: Compute DayDelta — compare yesterday vs today signals
        yesterday_signals = await self._get_yesterday_signals(user_id, target_date, profile, client, natal)
        if yesterday_signals:
            delta_service = DayDeltaService(yesterday_signals, signals)
            signals = delta_service.compute_deltas()
            new_count = sum(1 for s in signals if s.delta_kind == "new_today")
            peak_count = sum(1 for s in signals if s.delta_kind == "peak_today")
            bg_count = sum(1 for s in signals if s.delta_kind == "background")
            logger.info(f"[DayDelta] Computed: {len(signals)} signals, {new_count} new_today, {peak_count} peak, {bg_count} background")
        else:
            logger.info("[DayDelta] No yesterday data — skipping delta computation")

        # W-4.2: Score signals and calculate day_status
        scoring_service = ScoringService()
        scoring_result = scoring_service.score(signals)

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
            natal,
            transits,
            semantic_layer,
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
            if signal.type == "aspect":
                top_flags.append(TopFlag(
                    icon_name=f"{signal.planet}-{signal.aspect_type}",
                    title=f"{signal.planet} {signal.aspect_type} {signal.target_planet}",
                    summary=f"Orb: {signal.orb:.1f}°, Strength: {signal.strength:.2f}",
                    hint=None,
                ))
            elif signal.type == "planet_in_house":
                top_flags.append(TopFlag(
                    icon_name=f"{signal.planet}-house",
                    title=f"{signal.planet} в {signal.house} доме",
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

        payload = TodayPayload(
            meta=TodayMeta(
                schema_version="today/v1",
                contract_version=1,
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
            actions=None,
        )

        # W-5.2: Cache payload
        await self._cache_payload(user_id, target_date, payload)

        # W-5.2: Prefetch week in background (don't block user)
        if not skip_prefetch:
            asyncio.ensure_future(self._prefetch_week(user_id, target_date))

        return payload

    async def _get_cached_payload(self, user_id, target_date: Date) -> TodayPayload | None:
        """Get cached payload if exists. W-5.2."""
        result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
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

    async def _cache_payload(self, user_id, target_date: Date, payload: TodayPayload) -> None:
        """Cache payload. W-5.2."""
        # Serialize to JSON
        payload_json = payload.model_dump_json()

        # Upsert cache entry
        result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
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
                payload_json=payload_json,
            )
            self.db.add(cache_entry)

        await self.db.commit()

    async def invalidate_cache(self, user_id) -> None:
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
                contract_version=1,
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

    async def _get_yesterday_signals(self, user_id, today: Date, profile, client, natal: dict) -> list | None:
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
            y_signals = normalization_service.normalize(natal=natal, transits=y_transits)
            return y_signals
        except Exception as e:
            logger.info(f"[DayDelta] Could not get yesterday signals: {e}")
            return None

    async def _prefetch_week(self, user_id, today: Date) -> None:
        """Prefetch 7 days of payloads in background. W-5.2.
        Skips already-cached days to avoid duplicate work.
        Errors are silently ignored (background task)."""
        days = [today + timedelta(days=i) for i in range(-3, 4)]  # today ±3 days

        async def _calc_one(day: Date):
            try:
                cached = await self._get_cached_payload(user_id, day)
                if cached:
                    return  # Already cached — skip
                # Use preview access state for prefetch (real access checked on-demand)
                await self.get_today_payload(user_id, day, None, skip_prefetch=True)
            except Exception:
                pass  # Background task — don't break the app

        tasks = [_calc_one(d) for d in days]
        try:
            await asyncio.gather(*tasks)
        except Exception:
            pass
