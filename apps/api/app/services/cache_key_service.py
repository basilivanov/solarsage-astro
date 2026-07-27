# ############################################################################
# AI_HEADER: MODULE_CACHE_KEY_SERVICE — versioned cache key builder and runtime identity resolver.
# ROLE: Builds a deterministic versioned cache key for TodayPayloadCache.
#       Provides the canonical runtime identity resolver used by TodayService
#       and CalendarService for V1/V2 version-family mapping.
# ############################################################################

# START_MODULE_CONTRACT: M-CACHE-KEY-SERVICE
# purpose: Deterministic versioned cache key for TodayPayloadCache; canonical
#          V1/V2 runtime identity resolver used by TodayService and CalendarService.
# owns:
#   - apps/api/app/services/cache_key_service.py
# inputs:
#   - user_id: UUID
#   - target_date: str
#   - profile_hash: str
#   - selected_scoring_version: optional explicit int | str read authority
#   - activation_layer_version: str | None
# outputs:
#   - TodayCacheKey
#   - TodayRuntimeIdentity
# dependencies:
#   - M-VERSIONS (app.core.versions)
#   - M-CANON-SERVICE (get_canon_versions)
#   - M-DAY-SCORING-RUNTIME-SERVICE (selected_scoring_version_for_flags)
# side_effects: reads canon version services through get_canon_versions().
# emitted_logs: none.
# invariants:
#   - selected_scoring_version is the only family selector.
#   - SOLARSAGE_V2_FRONTEND_ENABLED never selects payload/cache identity.
#   - Dual-run computation does not imply V2 selection.
#   - Returned identity is immutable.
# failure_policy: propagates canon loading errors.
# END_MODULE_CONTRACT: M-CACHE-KEY-SERVICE

# START_MODULE_MAP: M-CACHE-KEY-SERVICE
# public_entrypoints:
#   - TodayCacheKey
#   - TodayRuntimeIdentity
#   - resolve_today_runtime_identity
#   - build_today_cache_key
#   - expected_cache_identity
# semantic_blocks:
#   - CACHE_KEY: TodayCacheKey + build_today_cache_key
#   - RESOLVER: TodayRuntimeIdentity + resolve_today_runtime_identity
#   - READ_IDENTITY: expected_cache_identity
# owned_tests:
#   - apps/api/tests/test_today_cache_v2_key.py
# END_MODULE_MAP: M-CACHE-KEY-SERVICE

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from app.core.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
    LEGACY_CALCULATION_VERSION,
    LEGACY_FRONTEND_PAYLOAD_VERSION,
    LEGACY_SCORING_VERSION,
    SCORING_V2_VERSION,
    SCORING_V2_1_VERSION,
    TODAY_CONTENT_VERSION,
    TODAY_V1_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
    TODAY_V2_2_PAYLOAD_VERSION,
    V2_FRONTEND_PAYLOAD_VERSION,
    V2_4_FRONTEND_PAYLOAD_VERSION,
    TODAY_LLM_PROMPT_VERSION,
)
from app.services.canon_service import get_canon_versions
from app.services.day_scoring_runtime_service import selected_scoring_version_for_flags


# START_BLOCK: CACHE_KEY
@dataclass(frozen=True)
class TodayCacheKey:
    """Deterministic versioned cache key for today payload."""

    user_id: UUID
    target_date: str
    profile_hash: str
    calculation_version: str
    activation_layer_version: str | None
    scoring_version: int | str
    canon_versions_hash: str
    llm_prompt_version: int
    content_version: int
    frontend_payload_version: int

    @property
    def cache_key_hash(self) -> str:
        # START_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.TodayCacheKey.cache_key_hash
        # purpose: Hash the complete Today cache identity including content, frontend, and canon hash fields.
        # inputs: self - immutable TodayCacheKey with user/date/profile and versioned identity fields.
        # returns: deterministic 16-character SHA-256 prefix.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.TodayCacheKey.cache_key_hash
        """Deterministic hash of all versioned fields."""
        raw = json.dumps({
            "user_id": str(self.user_id),
            "target_date": self.target_date,
            "profile_hash": self.profile_hash,
            "calculation_version": self.calculation_version,
            "activation_layer_version": self.activation_layer_version,
            "scoring_version": str(self.scoring_version),
            "canon_versions_hash": self.canon_versions_hash,
            "llm_prompt_version": self.llm_prompt_version,
            "content_version": self.content_version,
            "frontend_payload_version": self.frontend_payload_version,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_today_cache_key(
    *,
    user_id: UUID,
    target_date: str,
    profile_hash: str,
    calculation_version: str = LEGACY_CALCULATION_VERSION,
    activation_layer_version: str | None = None,
    scoring_version: int | str = LEGACY_SCORING_VERSION,
    llm_prompt_version: int = TODAY_LLM_PROMPT_VERSION,
    content_version: int = TODAY_CONTENT_VERSION,
    frontend_payload_version: int = LEGACY_FRONTEND_PAYLOAD_VERSION,
) -> TodayCacheKey:
    # START_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.build_today_cache_key
    # purpose: Build a deterministic Today cache key from request identity and current nine-canon hash.
    # inputs: user/date/profile identity plus calculation, activation, scoring, prompt, content, and frontend versions.
    # returns: TodayCacheKey whose canon_versions_hash reflects get_canon_versions() exactly.
    # side_effects: reads canon version services through get_canon_versions().
    # emitted_logs: none.
    # error_behavior: propagates canon loading errors.
    # END_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.build_today_cache_key
    """Build a versioned cache key with the current canon versions."""
    canon_versions = get_canon_versions()
    canon_versions_hash = hashlib.sha256(
        json.dumps(canon_versions, sort_keys=True).encode()
    ).hexdigest()[:16]

    return TodayCacheKey(
        user_id=user_id,
        target_date=target_date,
        profile_hash=profile_hash,
        calculation_version=calculation_version,
        activation_layer_version=activation_layer_version,
        scoring_version=scoring_version,
        canon_versions_hash=canon_versions_hash,
        llm_prompt_version=llm_prompt_version,
        content_version=content_version,
        frontend_payload_version=frontend_payload_version,
    )
# END_BLOCK: CACHE_KEY


# START_BLOCK: RESOLVER
@dataclass(frozen=True)
class TodayRuntimeIdentity:
    """Canonical runtime identity for the selected scoring family.

    One pure resolver eliminates duplicated V1/V2 version-family mapping
    across TodayService and CalendarService.
    """

    calculation_version: str
    activation_layer_version: str
    scoring_version: int | str
    payload_version: str
    frontend_payload_version: int
    content_version: int


def resolve_today_runtime_identity(
    *,
    selected_scoring_version: int | str,
    activation_layer_version: str | None = None,
) -> TodayRuntimeIdentity:
    # START_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.resolve_today_runtime_identity
    # purpose: Resolve canonical V1/V2 runtime identity family from the single
    #          selected scoring version authority.
    # inputs: selected_scoring_version — the scoring version that selects V1 or V2
    #         family; activation_layer_version — caller's current activation-layer
    #         version if known (retained when non-null, ACTIVATION_LAYER_VERSION
    #         used as fallback).
    # returns: immutable TodayRuntimeIdentity with the exact 6-field family.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.resolve_today_runtime_identity
    """Resolve canonical V1/V2 runtime identity from selected scoring version only."""
    str_selected = str(selected_scoring_version)
    if str_selected == str(SCORING_V2_1_VERSION):
        return TodayRuntimeIdentity(
            calculation_version=CALCULATION_VERSION,
            activation_layer_version=activation_layer_version or ACTIVATION_LAYER_VERSION,
            scoring_version=SCORING_V2_1_VERSION,
            payload_version=TODAY_V2_2_PAYLOAD_VERSION,
            frontend_payload_version=V2_4_FRONTEND_PAYLOAD_VERSION,
            content_version=TODAY_CONTENT_VERSION,
        )
    if str_selected == str(SCORING_V2_VERSION):
        return TodayRuntimeIdentity(
            calculation_version=CALCULATION_VERSION,
            activation_layer_version=activation_layer_version or ACTIVATION_LAYER_VERSION,
            scoring_version=SCORING_V2_VERSION,
            payload_version=TODAY_V2_PAYLOAD_VERSION,
            frontend_payload_version=V2_FRONTEND_PAYLOAD_VERSION,
            content_version=TODAY_CONTENT_VERSION,
        )
    return TodayRuntimeIdentity(
        calculation_version=LEGACY_CALCULATION_VERSION,
        activation_layer_version=activation_layer_version or ACTIVATION_LAYER_VERSION,
        scoring_version=LEGACY_SCORING_VERSION,
        payload_version=TODAY_V1_PAYLOAD_VERSION,
        frontend_payload_version=LEGACY_FRONTEND_PAYLOAD_VERSION,
        content_version=TODAY_CONTENT_VERSION,
    )
# END_BLOCK: RESOLVER


# START_BLOCK: READ_IDENTITY
def expected_cache_identity(
    *,
    user_id: UUID,
    target_date: str,
    profile_hash: str,
    selected_scoring_version: int | str | None = None,
) -> TodayCacheKey:
    # START_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.expected_cache_identity
    # purpose: Build the cache-read identity for the selected scoring family before fresh runtime objects exist.
    # inputs: user_id, target_date, profile_hash, and optional selected scoring
    #         version authority; None preserves global flag selection.
    # returns: V2 identity with current content/frontend and nine-canon hash, or legacy V1 identity.
    # side_effects: reads rollout scoring selection only when no explicit version
    #               is supplied; always reads canon version services.
    # emitted_logs: none.
    # error_behavior: propagates canon loading errors.
    # END_FUNCTION_CONTRACT: F-M-CACHE-KEY-SERVICE.expected_cache_identity
    """Build a cache key with the current expected version fields.

    Used before cache read when runtime facts are not yet known.
    Selected scoring version is the source of truth for identity — not the
    frontend rollout flag.
    """
    selected_scoring = (
        selected_scoring_version_for_flags()
        if selected_scoring_version is None
        else selected_scoring_version
    )
    identity = resolve_today_runtime_identity(
        selected_scoring_version=selected_scoring,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
    )
    return build_today_cache_key(
        user_id=user_id,
        target_date=target_date,
        profile_hash=profile_hash,
        calculation_version=identity.calculation_version,
        activation_layer_version=identity.activation_layer_version,
        scoring_version=identity.scoring_version,
        content_version=identity.content_version,
        frontend_payload_version=identity.frontend_payload_version,
    )
# END_BLOCK: READ_IDENTITY
