# ############################################################################
# AI_HEADER: MODULE_CACHE_KEY_SERVICE — versioned cache key builder.
# ROLE: Builds a deterministic versioned cache key for TodayPayloadCache.
# ############################################################################

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

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
    calculation_version: str = "1",
    activation_layer_version: str | None = None,
    scoring_version: int | str = 1,
    llm_prompt_version: int = 2,
    frontend_payload_version: int = 1,
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
    Includes a non-None activation_layer_version default of "al-1.0"."""
    from app.core.config import settings
    fe_version = 2 if getattr(settings, "solarsage_v2_frontend_enabled", False) else 1
    return build_today_cache_key(
        user_id=user_id,
        target_date=target_date,
        profile_hash=profile_hash,
        activation_layer_version="al-1.0",
        scoring_version=selected_scoring_version_for_flags(),
        frontend_payload_version=fe_version,
    )
