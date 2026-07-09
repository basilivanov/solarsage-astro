# ############################################################################
# AI_HEADER: MODULE_CACHE_KEY_SERVICE — versioned cache key builder.
# ROLE: Builds a deterministic versioned cache key for TodayPayloadCache.
# ############################################################################

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
    V2_FRONTEND_PAYLOAD_VERSION,
)
from app.services.canon_service import get_canon_versions
from app.services.day_scoring_runtime_service import selected_scoring_version_for_flags


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
    frontend_payload_version: int

    @property
    def cache_key_hash(self) -> str:
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
    llm_prompt_version: int = 2,
    frontend_payload_version: int = LEGACY_FRONTEND_PAYLOAD_VERSION,
) -> TodayCacheKey:
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
        frontend_payload_version=frontend_payload_version,
    )


def expected_cache_identity(
    *,
    user_id: UUID,
    target_date: str,
    profile_hash: str,
) -> TodayCacheKey:
    """Build a cache key with the current expected version fields.

    Used before cache read when runtime facts are not yet known.
    Selected scoring version is the source of truth for identity — not the
    frontend rollout flag.
    """
    selected_scoring = selected_scoring_version_for_flags()
    v2_selected = str(selected_scoring) == str(SCORING_V2_VERSION)

    if v2_selected:
        return build_today_cache_key(
            user_id=user_id,
            target_date=target_date,
            profile_hash=profile_hash,
            calculation_version=CALCULATION_VERSION,
            activation_layer_version=ACTIVATION_LAYER_VERSION,
            scoring_version=SCORING_V2_VERSION,
            frontend_payload_version=V2_FRONTEND_PAYLOAD_VERSION,
        )

    return build_today_cache_key(
        user_id=user_id,
        target_date=target_date,
        profile_hash=profile_hash,
        calculation_version=LEGACY_CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        scoring_version=LEGACY_SCORING_VERSION,
        frontend_payload_version=LEGACY_FRONTEND_PAYLOAD_VERSION,
    )
