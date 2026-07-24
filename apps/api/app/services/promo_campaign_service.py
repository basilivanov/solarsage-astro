# ############################################################################
# AI_HEADER: PROMO_CAMPAIGN_SERVICE — named promo preview and redemption domain boundary.
# ROLE: Validate opaque promo intent and expose typed domain results without HTTP concerns.
# DEPENDENCIES: SQLAlchemy AsyncSession, promo/profile ORM models, profile readiness helpers
# GRACE_ANCHORS: [PROMO_DOMAIN_TYPES, PROMO_TOKEN_HELPERS, PROMO_PREVIEW]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-PROMO-CAMPAIGN-SERVICE
# purpose: Provide atomic promo preview method for validating promo tokens and checking user profile readiness.
# owns:
#   - apps/api/app/services/promo_campaign_service.py
# inputs:
#   - user_id: UUID
#   - token: str
#   - db: AsyncSession
# outputs:
#   - PromoOfferData, PromoPreviewData, PromoGrantData, PromoRedeemData, PromoDomainError, PromoErrorCode
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-DB-MODELS (PromoCampaign, PromoRedemption, UserProfile)
#   - M-PROFILE.service (missing_onboarding_fields)
#   - M-NATAL-CONTEXT-SERVICE (NatalContextService)
# invariants:
#   - raw token / hash is never included in exception messages, attributes or logs
#   - preview makes zero DB mutations and emits zero logs
#   - token validation uses exact Base58 fullmatch regex
#   - existing redemption check precedes window and capacity checks
# failure_policy:
#   - raises PromoDomainError with safe code and localized message
# END_MODULE_CONTRACT: M-PROMO-CAMPAIGN-SERVICE

# START_MODULE_MAP: M-PROMO-CAMPAIGN-SERVICE
# public_entrypoints:
#   - PromoErrorCode
#   - PromoOfferData
#   - PromoPreviewData
#   - PromoGrantData
#   - PromoRedeemData
#   - PromoDomainError
#   - PromoCampaignService
#   - PROMO_TOKEN_REGEX
#   - hash_promo_token
# semantic_blocks:
#   - DATACLASSES: domain data structures and safe error class
#   - TOKEN_HELPERS: regex and SHA-256 hash calculation
#   - SERVICE_PREVIEW: preview implementation
# owned_tests:
#   - apps/api/tests/test_promo_campaign_service.py
# END_MODULE_MAP: M-PROMO-CAMPAIGN-SERVICE

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
import datetime as dt
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PromoCampaign, PromoRedemption, UserProfile
from app.services.natal_context_service import NatalContextService
from app.services.profile_service import missing_onboarding_fields

PROMO_TOKEN_REGEX = re.compile(r"^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$")

PromoErrorCode = Literal[
    "INVALID_CODE",
    "CAMPAIGN_EXPIRED",
    "CAMPAIGN_FULL",
    "ALREADY_REDEEMED",
    "PROFILE_INCOMPLETE",
]


# START_BLOCK: DATACLASSES
class PromoDomainError(Exception):
    """Domain error for promo campaign validation failures."""

    def __init__(self, code: PromoErrorCode, safe_message: str):
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


@dataclass(frozen=True)
class PromoOfferData:
    display_name: str
    access_days: int
    bonus_credits: int
    unlock_natal: bool


@dataclass(frozen=True)
class PromoPreviewData:
    offer: PromoOfferData
    profile_complete: bool


@dataclass(frozen=True)
class PromoGrantData:
    access_starts_at: dt.date | None
    access_until: dt.date | None
    bonus_credits: int
    bonus_credits_expires_at: datetime | None
    natal_unlocked: bool
    natal_already_owned: bool


@dataclass(frozen=True)
class PromoRedeemData:
    offer: PromoOfferData
    grants: PromoGrantData
# END_BLOCK: DATACLASSES


# START_BLOCK: TOKEN_HELPERS
# START_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.hash_promo_token
# purpose: Return lowercase 64-character SHA-256 hex digest of the raw ASCII token.
# inputs: token (str)
# returns: str — 64-char lowercase hex digest
# side_effects: none (pure function)
# emitted_logs: none
# error_behavior: raises UnicodeEncodeError for non-ASCII input; callers validate token format first
# END_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.hash_promo_token
def hash_promo_token(token: str) -> str:
    """Return lowercase 64-character SHA-256 hex digest of the raw token."""
    return hashlib.sha256(token.encode("ascii")).hexdigest().lower()
# END_BLOCK: TOKEN_HELPERS


# START_BLOCK: SERVICE_PREVIEW
class PromoCampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # START_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService.preview
    # purpose: Preview a promo offer for a user and evaluate profile completeness without DB mutations or logs.
    # inputs: user_id (UUID), token (str), now (datetime | None for testing)
    # returns: PromoPreviewData
    # side_effects: none (read-only query)
    # emitted_logs: none
    # error_behavior: raises PromoDomainError(INVALID_CODE, CAMPAIGN_EXPIRED, CAMPAIGN_FULL, ALREADY_REDEEMED)
    # END_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService.preview
    async def preview(
        self,
        user_id: uuid.UUID,
        token: str,
        *,
        now: datetime | None = None,
    ) -> PromoPreviewData:
        """Preview a promo offer for a user and evaluate profile completeness."""
        current_time = now or datetime.now(UTC)

        # 1. Format check: exact Base58 fullmatch without hash lookup
        if not token or not isinstance(token, str) or not PROMO_TOKEN_REGEX.fullmatch(token):
            raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

        # 2. Hash lookup
        code_hash = hash_promo_token(token)
        result = await self.db.execute(
            select(PromoCampaign).where(PromoCampaign.code_hash == code_hash)
        )
        campaign = result.scalar_one_or_none()

        if campaign is None:
            raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

        # 3. Check existing redemption for this (campaign_id, user_id) IMMEDIATELY
        redemption_res = await self.db.execute(
            select(PromoRedemption).where(
                PromoRedemption.campaign_id == campaign.id,
                PromoRedemption.user_id == user_id,
            )
        )
        if redemption_res.scalar_one_or_none() is not None:
            raise PromoDomainError(code="ALREADY_REDEEMED", safe_message="Промокод уже активирован")

        # 4. Inactive or not-yet-started -> INVALID_CODE
        if not campaign.active or current_time < campaign.activation_starts_at:
            raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

        # 5. Campaign expired (now >= activation_ends_at) -> CAMPAIGN_EXPIRED
        if current_time >= campaign.activation_ends_at:
            raise PromoDomainError(code="CAMPAIGN_EXPIRED", safe_message="Срок действия промокода истёк")

        # 6. Capacity reached -> CAMPAIGN_FULL
        if campaign.redemptions_used >= campaign.max_redemptions:
            raise PromoDomainError(code="CAMPAIGN_FULL", safe_message="Лимит активаций промокода исчерпан")

        # 7. Profile readiness check
        profile_res = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_res.scalar_one_or_none()

        if not campaign.unlock_natal:
            missing = missing_onboarding_fields(profile)
        else:
            missing = NatalContextService.missing_profile_fields(profile)

        profile_complete = (len(missing) == 0)

        offer = PromoOfferData(
            display_name=campaign.display_name,
            access_days=campaign.access_days,
            bonus_credits=campaign.bonus_credits,
            unlock_natal=campaign.unlock_natal,
        )

        return PromoPreviewData(
            offer=offer,
            profile_complete=profile_complete,
        )
# END_BLOCK: SERVICE_PREVIEW
