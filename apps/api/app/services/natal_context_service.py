# AI_HEADER: MODULE_NATAL_CONTEXT_SERVICE
# module: M-NATAL-CONTEXT-SERVICE
# wave: W-NATAL-FULL
# purpose: Persistent natal context cache — single source of truth for all natal facts.
#          Ensures chart is calculated once, reused by preview/day/report.

# START_MODULE_CONTRACT: M-NATAL-CONTEXT-SERVICE
# purpose: Provide get_or_build_natal_context(user) — the single production path
#          for natal chart facts. All consumers (preview, day, report) must go
#          through this service. Never call SolarSage directly for natal data.
# owns:
#   - apps/api/app/services/natal_context_service.py
# inputs:
#   - user_id: UUID
#   - UserProfile with birth data
# outputs:
#   - NatalContextData: deterministic chart context (angles, planets, houses, aspects,
#     scores, balances)
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-SOLARSAGE-CLIENT (get_solarsage_client)
#   - M-NORMALIZATION-SERVICE
#   - M-SCORING-SERVICE
#   - M-CONTRACTS.natal (NatalContextData, SolarSageNatalResponse)
# invariants:
#   - Only one active NatalChartCache per (user_id, profile_hash, engine_version,
#     calculation_version, house_system, invalidated_at IS NULL).
#   - profile_hash changes when any birth field changes → cache miss → rebuild.
#   - Service never calls transits.
#   - Service never calls LLM.
# failure_policy:
#   - Incomplete profile → raises HTTPException 409 with missing fields.
#   - Sidecar unavailable → raises HTTPException 502.
#   - Sidecar invalid schema → raises HTTPException 502.
# non_goals:
#   - No transit calculation.
#   - No report generation.
#   - No LLM integration.
# END_MODULE_CONTRACT: M-NATAL-CONTEXT-SERVICE

# START_MODULE_MAP: M-NATAL-CONTEXT-SERVICE
# public_entrypoints:
#   - get_or_build_natal_context
#   - build_natal_context
#   - invalidate_for_user
#   - compute_profile_hash
# semantic_blocks:
#   - NATAL_CONTEXT_BUILD: build and cache natal context
#   - NATAL_CONTEXT_INVALIDATE: invalidate on profile change
# END_MODULE_MAP: M-NATAL-CONTEXT-SERVICE

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.solarsage_client import get_solarsage_client
from app.db.models import NatalChartCache, UserProfile
from app.schemas.natal import (
    ElementsBalance,
    ModalitiesBalance,
    NatalChartAngle,
    NatalChartAspect,
    NatalChartHouse,
    NatalChartPlanet,
    NatalChartSpecialPoint,
    NatalContextData,
    SolarSageNatalResponse,
)
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.core.logging import log_event, log_block

# ── Versioning constants ──────────────────────────────────────────
ENGINE_VERSION = "1"
CALCULATION_VERSION = "1"
HOUSE_SYSTEM_DEFAULT = "placidus"

# ── Required profile fields for natal context ────────────────────
REQUIRED_PROFILE_FIELDS = ["birthday", "birth_time", "birth_lat", "birth_lon", "birth_tz", "gender"]

# ── Sign lists for element/modality balance ──────────────────────
_FIRE_SIGNS = {"Aries", "Leo", "Sagittarius"}
_EARTH_SIGNS = {"Taurus", "Virgo", "Capricorn"}
_AIR_SIGNS = {"Gemini", "Libra", "Aquarius"}
_WATER_SIGNS = {"Cancer", "Scorpio", "Pisces"}

_CARDINAL_SIGNS = {"Aries", "Cancer", "Libra", "Capricorn"}
_FIXED_SIGNS = {"Taurus", "Leo", "Scorpio", "Aquarius"}
_MUTABLE_SIGNS = {"Gemini", "Virgo", "Sagittarius", "Pisces"}


class NatalContextService:
    """Single source of truth for all natal chart facts.

    Every consumer — preview, daily forecast, full report — must go through
    get_or_build_natal_context(). Never call the SolarSage sidecar directly.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Public API ────────────────────────────────────────────────

    # START_BLOCK: PUBLIC_API
    async def get_or_build_natal_context(self, user_id: uuid.UUID) -> NatalContextData:
        # START_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.get_or_build_natal_context
        # purpose: Return cached natal context or build and persist a new one.
        # inputs: user_id (UUID)
        # returns: NatalContextData with angles, planets, houses, aspects, scores
        # side_effects: reads/writes NatalChartCache, calls sidecar on cache miss
        # emitted_logs: natal.context_cache_hit, natal.context_cache_miss, natal.context_cached, natal.sidecar_called
        # error_behavior: HTTPException 404 on missing profile, 409 on incomplete profile, 502 on sidecar failure
        # END_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.get_or_build_natal_context
        """Return cached natal context or build and persist a new one.

        This is the ONLY production path for natal chart facts.
        """
        # 1. Load profile and validate completeness
        profile = await self._load_profile(user_id)
        self._validate_profile_completeness(profile)

        # 2. Compute stable hash of all birth inputs
        profile_hash = self.compute_profile_hash(profile)

        # 3. Check active cache
        cached = await self._find_active_cache(user_id, profile_hash)
        if cached is not None:
            # Update last_used_at
            cached.last_used_at = datetime.now(UTC)
            await self.db.commit()
            return self._deserialize_context(cached.normalized_context_json)

        # 4. Cache miss: call sidecar, validate, normalize, score, persist
        context = await self._build_natal_context(profile, profile_hash)
        return context

    async def build_natal_context(self, profile: UserProfile) -> NatalContextData:
        # START_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.build_natal_context
        # purpose: Build natal context from profile (forces recalculation, no cache check).
        # inputs: profile (UserProfile)
        # returns: NatalContextData
        # side_effects: calls sidecar, normalizes, scores, persists to DB
        # emitted_logs: natal.context_build_started, natal.context_cached, natal.sidecar_called
        # error_behavior: HTTPException 502 on sidecar failure
        # END_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.build_natal_context
        """Build natal context from a profile (forces recalculation, no cache check).

        Used internally when we know the cache is stale or missing.
        """
        profile_hash = self.compute_profile_hash(profile)
        return await self._build_natal_context(profile, profile_hash)

    async def invalidate_for_user(self, user_id: uuid.UUID, reason: str) -> None:
        # START_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.invalidate_for_user
        # purpose: Invalidate all active natal contexts for a user on birth data change.
        # inputs: user_id (UUID), reason (str)
        # returns: None
        # side_effects: sets invalidated_at on all active NatalChartCache rows
        # emitted_logs: natal.context_invalidated
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.invalidate_for_user
        """Invalidate all active natal contexts for a user.

        Called when user changes birth data.
        """
        result = await self.db.execute(
            select(NatalChartCache).where(
                and_(
                    NatalChartCache.user_id == user_id,
                    NatalChartCache.invalidated_at.is_(None),
                )
            )
        )
        caches = result.scalars().all()

        now = datetime.now(UTC)
        for cache in caches:
            cache.invalidated_at = now

        await self.db.commit()
        with log_block(slice="W-NATAL-FULL", module="M-NATAL-CONTEXT-SERVICE", block="INVALIDATE_CONTEXT"):
            log_event(
                "natal.context_invalidated",
                level="info",
                msg=f"Invalidated {len(caches)} natal contexts: {reason}",
                payload={
                    "count": len(caches),
                    "reason": reason,
                }
            )

    @staticmethod
    def compute_profile_hash(profile: UserProfile) -> str:
        # START_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.compute_profile_hash
        # purpose: Compute deterministic hash of birth inputs for cache key.
        # inputs: profile (UserProfile)
        # returns: str — 16-char SHA-256 hex digest
        # side_effects: none (pure function)
        # emitted_logs: none
        # error_behavior: never raises (defaults missing fields to "")
        # END_FUNCTION_CONTRACT: F-M-NATAL-CONTEXT-SERVICE.compute_profile_hash
        """Compute deterministic hash of all birth inputs that affect natal chart.

        If user edits any birth field, hash changes → cache miss → rebuild.
        """
        parts = [
            str(profile.birthday or ""),
            str(profile.birth_time or ""),
            str(profile.birth_lat or ""),
            str(profile.birth_lon or ""),
            str(profile.birth_tz or ""),
            str(profile.gender or ""),
            HOUSE_SYSTEM_DEFAULT,
        ]
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    # END_BLOCK: PUBLIC_API

    # ── Private: profile loading & validation ─────────────────────

    async def _load_profile(self, user_id: uuid.UUID) -> UserProfile:
        """Load user profile or raise 404."""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "PROFILE_NOT_FOUND", "message": "Профиль не найден."},
            )
        return profile

    @staticmethod
    def _validate_profile_completeness(profile: UserProfile) -> None:
        """Validate that all required birth fields are present.

        Raises HTTPException 409 with missing fields list.
        """
        missing_fields = [
            field_name
            for field_name in REQUIRED_PROFILE_FIELDS
            if getattr(profile, field_name) is None
        ]
        if missing_fields:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Profile is incomplete",
                    "missingFields": missing_fields,
                },
            )
        if profile.gender not in {"male", "female"}:
            raise HTTPException(
                status_code=409,
                detail={"message": "Profile is incomplete", "missingFields": ["gender"]},
            )

    # START_BLOCK: CACHE_LOOKUP
    async def _find_active_cache(
        self, user_id: uuid.UUID, profile_hash: str
    ) -> NatalChartCache | None:
        """Find active (non-invalidated) cache entry for this user+hash+versions."""
        result = await self.db.execute(
            select(NatalChartCache).where(
                and_(
                    NatalChartCache.user_id == user_id,
                    NatalChartCache.profile_hash == profile_hash,
                    NatalChartCache.engine_version == ENGINE_VERSION,
                    NatalChartCache.calculation_version == CALCULATION_VERSION,
                    NatalChartCache.house_system == HOUSE_SYSTEM_DEFAULT,
                    NatalChartCache.invalidated_at.is_(None),
                )
            )
        )
        return result.scalar_one_or_none()

    # END_BLOCK: CACHE_LOOKUP

    # ── Private: context building ─────────────────────────────────

    # START_BLOCK: CONTEXT_BUILDING
    async def _build_natal_context(
        self, profile: UserProfile, profile_hash: str
    ) -> NatalContextData:
        """Build natal context: call sidecar → validate → normalize → score → persist."""
        # 1. Call SolarSage sidecar
        client = get_solarsage_client()
        birth_date = profile.birthday.isoformat()  # type: ignore[union-attr]
        birth_time = profile.birth_time.strftime("%H:%M")  # type: ignore[union-attr]
        birth_lat = float(profile.birth_lat)  # type: ignore[arg-type]
        birth_lon = float(profile.birth_lon)  # type: ignore[arg-type]
        birth_tz = profile.birth_tz  # type: ignore[assignment]

        try:
            # Client already returns validated.model_dump(by_alias=True),
            # so this dict is guaranteed to match the Pydantic schema.
            validated_chart_dict = await client.get_natal(
                birth_date=birth_date,
                birth_time=birth_time,
                birth_lat=birth_lat,
                birth_lon=birth_lon,
                birth_tz=birth_tz,
            )
        except httpx.HTTPError as exc:
            with log_block(slice="W-NATAL-FULL", module="M-NATAL-CONTEXT-SERVICE", block="BUILD_CONTEXT"):
                log_event(
                    "natal.sidecar_failed",
                    level="error",
                    msg=f"SolarSage sidecar error: {type(exc).__name__}",
                )
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "SOLARSAGE_UNAVAILABLE",
                    "message": "Сервис расчёта временно недоступен. Попробуй позже.",
                },
            ) from exc

        # 2. Re-validate sidecar response (defense-in-depth: client already
        #    validated, but this service is the authoritative boundary).
        try:
            validated = SolarSageNatalResponse.model_validate(validated_chart_dict)
        except Exception as exc:
            with log_block(slice="W-NATAL-FULL", module="M-NATAL-CONTEXT-SERVICE", block="BUILD_CONTEXT"):
                log_event(
                    "natal.sidecar_failed",
                    level="error",
                    msg=f"SolarSage natal response validation failed: {type(exc).__name__}",
                )
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "SOLARSAGE_INVALID_RESPONSE",
                    "message": "Ошибка формата данных натальной карты.",
                },
            ) from exc

        # 3. Normalize natal-only (no transits)
        normalization_service = NormalizationService()
        natal_signals = normalization_service.normalize_natal_only(validated_chart_dict)

        # 4. Score natal
        scoring_service = ScoringService()
        natal_scores = scoring_service.score_natal(natal_signals)

        # 5. Build NatalContextData
        context = self._build_context_data(validated, natal_scores)

        # 6. Persist to cache
        #    Defensive cleanup: remove any invalidated rows with the same key
        #    so the partial unique index (WHERE invalidated_at IS NULL) can't
        #    be violated by a race between invalidate and rebuild.
        await self._cleanup_invalidated_rows(profile.user_id, profile_hash)

        raw_chart_json = json.dumps(validated_chart_dict, ensure_ascii=False)
        normalized_context_json = context.model_dump_json(by_alias=False)
        summary_json = self._build_summary(context)

        cache_entry = NatalChartCache(
            user_id=profile.user_id,
            profile_hash=profile_hash,
            engine_version=ENGINE_VERSION,
            calculation_version=CALCULATION_VERSION,
            house_system=HOUSE_SYSTEM_DEFAULT,
            raw_chart_json=raw_chart_json,
            normalized_context_json=normalized_context_json,
            summary_json=summary_json,
        )
        self.db.add(cache_entry)
        await self.db.commit()
        await self.db.refresh(cache_entry)

        with log_block(slice="W-NATAL-FULL", module="M-NATAL-CONTEXT-SERVICE", block="BUILD_CONTEXT"):
            log_event(
                "natal.context_cached",
                level="info",
                msg="Built and cached natal context",
                payload={
                    "hash": profile_hash,
                    "cache_id": str(cache_entry.id),
                },
            )
        return context

    @staticmethod
    def _build_context_data(
        validated: SolarSageNatalResponse,
        natal_scores: dict,
    ) -> NatalContextData:
        """Build NatalContextData from validated sidecar output + natal scores."""
        # Angles from special_points
        angle_names = {"ASC", "MC", "DSC", "IC"}
        angles = []
        for sp in validated.special_points:
            if sp.name in angle_names:
                angles.append(NatalChartAngle(
                    name=sp.name,
                    sign=sp.sign,
                    degree=round(sp.longitude % 30, 2),
                    longitude=round(sp.longitude, 4),
                ))

        # Planets
        planets = []
        for p in validated.planets:
            planets.append(NatalChartPlanet(
                name=p.name,
                sign=p.sign,
                degree=round(p.longitude % 30, 2),
                house=p.house,
                retrograde=p.retrograde,
                longitude=round(p.longitude, 4),
            ))

        # Houses
        houses = []
        for h in validated.houses:
            houses.append(NatalChartHouse(
                number=h.number,
                sign=h.sign,
                degree=round(h.longitude % 30, 2),
                longitude=round(h.longitude, 4),
            ))

        # Aspects (from natal signals)
        aspect_signals = [s for s in natal_scores.get("natal_signals", []) if s.type == "aspect"]
        aspects = []
        for s in aspect_signals:
            aspects.append(NatalChartAspect(
                planet_a=s.planet or "",
                planet_b=s.target_planet or "",
                aspect_type=s.aspect_type or "",
                orb=round(s.orb or 0, 2),
                applying=None,
            ))

        # Special points (non-angle)
        special_points = []
        for sp in validated.special_points:
            if sp.name not in angle_names:
                special_points.append(NatalChartSpecialPoint(
                    name=sp.name,
                    sign=sp.sign,
                    degree=round(sp.longitude % 30, 2),
                    longitude=round(sp.longitude, 4),
                    house=sp.house,
                ))

        # Element/modality balance
        elements = ElementsBalance()
        modalities = ModalitiesBalance()
        for p in validated.planets:
            if p.sign in _FIRE_SIGNS:
                elements.fire += 1.0
            elif p.sign in _EARTH_SIGNS:
                elements.earth += 1.0
            elif p.sign in _AIR_SIGNS:
                elements.air += 1.0
            elif p.sign in _WATER_SIGNS:
                elements.water += 1.0

            if p.sign in _CARDINAL_SIGNS:
                modalities.cardinal += 1.0
            elif p.sign in _FIXED_SIGNS:
                modalities.fixed += 1.0
            elif p.sign in _MUTABLE_SIGNS:
                modalities.mutable += 1.0

        # Dominants: top 3 by score
        planet_scores = natal_scores.get("planet_scores", {})
        dominants = sorted(planet_scores, key=planet_scores.get, reverse=True)[:3]  # type: ignore[arg-type]

        return NatalContextData(
            angles=angles,
            planets=planets,
            houses=houses,
            aspects=aspects,
            special_points=special_points,
            elements_balance=elements,
            modalities_balance=modalities,
            house_system=validated.house_system,
            sphere_scores=natal_scores.get("sphere_scores", {}),
            top_signals=[
                {
                    "type": s.type,
                    "planet": s.planet,
                    "house": s.house,
                    "sign": s.sign,
                    "aspect_type": s.aspect_type,
                    "target_planet": s.target_planet,
                    "orb": round(s.orb or 0, 2),
                    "strength": round(s.strength, 4),
                }
                for s in natal_scores.get("top_signals", [])
            ],
            dominants=dominants,
        )

    async def _cleanup_invalidated_rows(
        self, user_id: uuid.UUID, profile_hash: str
    ) -> None:
        """Delete invalidated cache rows for this user+hash to prevent
        unique-index conflicts on rebuild.

        Belt-and-suspenders with the partial unique index: even if the
        partial index somehow fails (e.g. SQLite < 3.8), this ensures
        the INSERT won't collide with an invalidated row.
        """
        await self.db.execute(
            delete(NatalChartCache).where(
                and_(
                    NatalChartCache.user_id == user_id,
                    NatalChartCache.profile_hash == profile_hash,
                    NatalChartCache.invalidated_at.is_not(None),
                )
            )
        )
        # Don't commit here — caller will commit after the INSERT.

    @staticmethod
    def _build_summary(context: NatalContextData) -> str:
        """Build small denormalized summary JSON for list/preview/debug."""
        asc = next((a for a in context.angles if a.name == "ASC"), None)
        sun = next((p for p in context.planets if p.name == "Sun"), None)
        moon = next((p for p in context.planets if p.name == "Moon"), None)
        summary = {
            "asc_sign": asc.sign if asc else None,
            "sun_sign": sun.sign if sun else None,
            "moon_sign": moon.sign if moon else None,
            "planets_count": len(context.planets),
            "aspects_count": len(context.aspects),
            "dominants": context.dominants,
        }
        return json.dumps(summary, ensure_ascii=False)

    @staticmethod
    def _deserialize_context(json_str: str) -> NatalContextData:
        """Deserialize stored context JSON back to NatalContextData."""
        data = json.loads(json_str)
        return NatalContextData.model_validate(data)
# END_BLOCK: CONTEXT_BUILDING
