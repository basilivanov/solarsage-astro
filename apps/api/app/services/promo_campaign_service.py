# ############################################################################
# AI_HEADER: PROMO_CAMPAIGN_SERVICE — named promo preview and redemption boundary.
# ROLE: Validate opaque promo intent and atomically issue configured grants.
# DEPENDENCIES: SQLAlchemy AsyncSession, promo/grant/profile models and services.
# GRACE_ANCHORS: [PROMO_DOMAIN_TYPES, PROMO_VALUE_HELPERS, PROMO_PREVIEW, PROMO_REDEEM]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-PROMO-CAMPAIGN-SERVICE
# purpose: Provide atomic promo preview and redeem methods for validating promo tokens, checking profile readiness, and issuing access/credit/natal grants.
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
#   - M-DB-MODELS (User, PromoCampaign, PromoRedemption, UserProfile, AccessLedger, HoraryCredit, Purchase)
#   - M-ACCESS.service (AccessService)
#   - M-PROFILE.service (missing_onboarding_fields)
#   - M-NATAL-CONTEXT-SERVICE (NatalContextService)
# invariants:
#   - raw token / hash is never included in exception messages, attributes or logs
#   - preview makes zero DB mutations and emits zero logs
#   - token validation uses exact Base58 fullmatch regex
#   - existing redemption check precedes window and capacity checks
#   - lock order during redeem is campaign first, user second
#   - redeem executes exactly one final commit and logs promo.redemption_succeeded strictly after commit
#   - concurrent natal entitlement creation recovers via SAVEPOINT and re-queries fulfilled Purchase
# failure_policy:
#   - raises PromoDomainError with safe code and localized message; rollbacks and emits safe structured log on error
# emitted_logs:
#   - promo.redemption_succeeded
#   - promo.redemption_rejected
#   - promo.redemption_failed
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
#   - VALUE_HELPERS: token hashing and UTC normalization
#   - SERVICE_PREVIEW: preview implementation
#   - SERVICE_REDEEM: atomic redeem implementation
# owned_tests:
#   - apps/api/tests/test_promo_campaign_service.py
# END_MODULE_MAP: M-PROMO-CAMPAIGN-SERVICE

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
import datetime as dt
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import (
    HoraryCredit,
    PromoCampaign,
    PromoRedemption,
    Purchase,
    User,
    UserProfile,
)
from app.services.access_service import AccessService
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


# START_BLOCK: VALUE_HELPERS
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


def _ensure_utc(dt_val: datetime) -> datetime:
    """Normalize database timestamps to UTC, including SQLite-naive values."""
    if dt_val.tzinfo is None:
        return dt_val.replace(tzinfo=UTC)
    return dt_val.astimezone(UTC)
# END_BLOCK: VALUE_HELPERS


# START_BLOCK: SERVICE_PREVIEW
class PromoCampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _find_fulfilled_natal_purchase(
        self, user_id: uuid.UUID, context_hash: str
    ) -> Purchase | None:
        # START_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService._find_fulfilled_natal_purchase
        # purpose: Find an existing fulfilled natal entitlement for the exact user context.
        # inputs: user_id (UUID), context_hash (str)
        # returns: fulfilled Purchase or None
        # side_effects: one read-only database query
        # emitted_logs: none
        # error_behavior: database errors propagate
        # END_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService._find_fulfilled_natal_purchase
        purch_res = await self.db.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.product_slug == "natal_full_report",
                Purchase.context_hash == context_hash,
                Purchase.status.in_(["succeeded", "delivered"]),
            )
        )
        return purch_res.scalars().first()

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
        starts_at = _ensure_utc(campaign.activation_starts_at)
        if not campaign.active or current_time < starts_at:
            raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

        # 5. Campaign expired (now >= activation_ends_at) -> CAMPAIGN_EXPIRED
        ends_at = _ensure_utc(campaign.activation_ends_at)
        if current_time >= ends_at:
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

# START_BLOCK: SERVICE_REDEEM
    # START_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService.redeem
    # purpose: Atomically validate and redeem a promo token for a user, granting access, credits, and natal entitlements.
    # inputs: user_id (UUID), token (str), now (datetime | None for testing)
    # returns: PromoRedeemData
    # side_effects: inserts/updates DB rows with locks, issues single commit, emits promo log events
    # emitted_logs: promo.redemption_succeeded, promo.redemption_rejected, promo.redemption_failed
    # error_behavior: rolls back transaction and emits safe log on any domain or system failure and re-raises
    # END_FUNCTION_CONTRACT: F-M-PROMO-CAMPAIGN-SERVICE.PromoCampaignService.redeem
    async def redeem(
        self,
        user_id: uuid.UUID,
        token: str,
        *,
        now: datetime | None = None,
    ) -> PromoRedeemData:
        """Atomically redeem a promo token for a user."""
        current_time = now or datetime.now(UTC)
        campaign_id_str: str | None = None
        campaign_access_days = 0
        campaign_bonus_credits = 0
        campaign_unlock_natal = False
        natal_already_owned = False

        try:
            # 1. Format check: exact Base58 fullmatch without hash lookup
            if not token or not isinstance(token, str) or not PROMO_TOKEN_REGEX.fullmatch(token):
                raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

            # 2. Lock campaign FOR UPDATE by code_hash (Lock 1)
            code_hash = hash_promo_token(token)
            campaign_res = await self.db.execute(
                select(PromoCampaign)
                .where(PromoCampaign.code_hash == code_hash)
                .with_for_update()
            )
            campaign = campaign_res.scalar_one_or_none()

            if campaign is None:
                raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

            # Snapshot campaign primitive values early
            campaign_id_str = str(campaign.id)
            campaign_access_days = campaign.access_days
            campaign_bonus_credits = campaign.bonus_credits
            campaign_unlock_natal = campaign.unlock_natal

            # 3. Existing redemption check IMMEDIATELY after campaign resolution
            redemption_res = await self.db.execute(
                select(PromoRedemption).where(
                    PromoRedemption.campaign_id == campaign.id,
                    PromoRedemption.user_id == user_id,
                )
            )
            if redemption_res.scalar_one_or_none() is not None:
                raise PromoDomainError(code="ALREADY_REDEEMED", safe_message="Промокод уже активирован")

            # 4. Inactive or not-yet-started -> INVALID_CODE
            starts_at = _ensure_utc(campaign.activation_starts_at)
            if not campaign.active or current_time < starts_at:
                raise PromoDomainError(code="INVALID_CODE", safe_message="Неверный промокод")

            # 5. Campaign expired -> CAMPAIGN_EXPIRED
            ends_at = _ensure_utc(campaign.activation_ends_at)
            if current_time >= ends_at:
                raise PromoDomainError(code="CAMPAIGN_EXPIRED", safe_message="Срок действия промокода истёк")

            # 6. Lock internal User row FOR UPDATE (Lock 2: campaign first, user second)
            user_res = await self.db.execute(
                select(User).where(User.id == user_id).with_for_update()
            )
            user = user_res.scalar_one_or_none()
            if user is None:
                raise PromoDomainError(code="INVALID_CODE", safe_message="Пользователь не найден")

            # 7. Profile readiness check according to campaign unlock_natal
            profile_res = await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = profile_res.scalar_one_or_none()

            if not campaign.unlock_natal:
                missing = missing_onboarding_fields(profile)
            else:
                missing = NatalContextService.missing_profile_fields(profile)

            if len(missing) > 0:
                raise PromoDomainError(
                    code="PROFILE_INCOMPLETE",
                    safe_message="Заполните профиль для активации промокода",
                )

            # 8. Capacity check
            if campaign.redemptions_used >= campaign.max_redemptions:
                raise PromoDomainError(code="CAMPAIGN_FULL", safe_message="Лимит активаций промокода исчерпан")

            # 9. Issue grants
            access_service = AccessService(self.db)
            access_starts_at: dt.date | None = None
            access_until: dt.date | None = None
            access_ledger_id: uuid.UUID | None = None

            if campaign.access_days > 0:
                start_date = await access_service.next_grant_start(user_id, current_time.date())
                ledger_entry = await access_service.grant_subscription(
                    user_id,
                    start_date,
                    days=campaign.access_days,
                    commit=False,
                )
                access_starts_at = ledger_entry.start_date
                access_until = ledger_entry.end_date
                access_ledger_id = ledger_entry.id

            credit_id: uuid.UUID | None = None
            credit_expires_at: datetime | None = None

            if campaign.bonus_credits > 0:
                if access_until is not None:
                    expiry_date = access_until + dt.timedelta(days=1)
                    credit_expires_at = datetime(
                        expiry_date.year, expiry_date.month, expiry_date.day, 0, 0, 0, tzinfo=UTC
                    )

                metadata = json.dumps(
                    {"grant_type": "promo", "campaign_id": campaign_id_str},
                    sort_keys=True,
                    separators=(",", ":"),
                )

                credit = HoraryCredit(
                    user_id=user_id,
                    source="gift",
                    amount=campaign.bonus_credits,
                    used_amount=0,
                    access_week_start=None,
                    access_week_end=None,
                    expires_at=credit_expires_at,
                    metadata_json=metadata,
                )
                self.db.add(credit)
                await self.db.flush()
                credit_id = credit.id

            natal_unlocked = False
            natal_purchase_id: uuid.UUID | None = None

            if campaign.unlock_natal:
                natal_unlocked = True
                assert profile is not None
                context_hash = NatalContextService.compute_profile_hash(profile)

                existing_purchase = await self._find_fulfilled_natal_purchase(user_id, context_hash)

                if existing_purchase is not None:
                    natal_already_owned = True
                    natal_purchase_id = existing_purchase.id
                else:
                    natal_already_owned = False
                    try:
                        async with self.db.begin_nested():
                            new_purchase = Purchase(
                                user_id=user_id,
                                product_slug="natal_full_report",
                                status="delivered",
                                payment_id=None,
                                horary_quota_added=None,
                                context_hash=context_hash,
                            )
                            self.db.add(new_purchase)
                            await self.db.flush()
                            natal_purchase_id = new_purchase.id
                    except IntegrityError:
                        rechecked_purchase = await self._find_fulfilled_natal_purchase(user_id, context_hash)
                        if rechecked_purchase is not None:
                            natal_already_owned = True
                            natal_purchase_id = rechecked_purchase.id
                        else:
                            raise

            # 10. Record redemption
            redemption = PromoRedemption(
                campaign_id=campaign.id,
                user_id=user_id,
                access_ledger_id=access_ledger_id,
                credit_id=credit_id,
                natal_purchase_id=natal_purchase_id,
            )
            self.db.add(redemption)

            # 11. Increment counter once
            campaign.redemptions_used += 1

            # Snapshot result primitives
            result = PromoRedeemData(
                offer=PromoOfferData(
                    display_name=campaign.display_name,
                    access_days=campaign.access_days,
                    bonus_credits=campaign.bonus_credits,
                    unlock_natal=campaign.unlock_natal,
                ),
                grants=PromoGrantData(
                    access_starts_at=access_starts_at,
                    access_until=access_until,
                    bonus_credits=campaign.bonus_credits,
                    bonus_credits_expires_at=credit_expires_at,
                    natal_unlocked=natal_unlocked,
                    natal_already_owned=natal_already_owned,
                ),
            )

            # 12. Flush and single final commit
            await self.db.flush()
            await self.db.commit()

            # Emit success log event STRICTLY AFTER commit
            try:
                with log_block(slice="W-PROMO-CAMPAIGN", module="M-PROMO-CAMPAIGN-SERVICE", block="REDEEM"):
                    log_event(
                        "promo.redemption_succeeded",
                        level="info",
                        msg="Promo redemption succeeded",
                        payload={
                            "campaign_id": campaign_id_str,
                            "access_days": campaign_access_days,
                            "bonus_credits": campaign_bonus_credits,
                            "unlock_natal": campaign_unlock_natal,
                            "natal_already_owned": natal_already_owned,
                        },
                    )
            except Exception:
                pass

            return result

        except PromoDomainError as err:
            await self.db.rollback()
            try:
                payload: dict[str, str] = {"error_code": err.code}
                if campaign_id_str is not None:
                    payload["campaign_id"] = campaign_id_str
                with log_block(slice="W-PROMO-CAMPAIGN", module="M-PROMO-CAMPAIGN-SERVICE", block="REDEEM"):
                    log_event(
                        "promo.redemption_rejected",
                        level="info",
                        msg="Promo redemption rejected",
                        payload=payload,
                    )
            except Exception:
                pass
            raise

        except Exception as exc:
            error_kind = type(exc).__name__
            await self.db.rollback()
            try:
                err_payload: dict[str, str] = {"error_kind": error_kind}
                if campaign_id_str is not None:
                    err_payload["campaign_id"] = campaign_id_str
                with log_block(slice="W-PROMO-CAMPAIGN", module="M-PROMO-CAMPAIGN-SERVICE", block="REDEEM"):
                    log_event(
                        "promo.redemption_failed",
                        level="error",
                        msg="Promo redemption failed",
                        payload=err_payload,
                    )
            except Exception:
                pass
            raise
# END_BLOCK: SERVICE_REDEEM
