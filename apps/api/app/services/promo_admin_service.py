# ############################################################################
# AI_HEADER: PROMO_ADMIN_SERVICE — secure campaign management for operators.
# ROLE: Create, inspect, list redemptions, and disable promo campaigns without exposing raw tokens.
# DEPENDENCIES: SQLAlchemy AsyncSession, secrets, unicodedata, app.db.models, app.services.promo_campaign_service
# GRACE_ANCHORS: [PROMO_ADMIN_SERVICE]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-PROMO-ADMIN-SERVICE
# purpose: Provide administrative operations for creating, inspecting, listing redemptions, and disabling promo campaigns safely without logging tokens or hashes.
# owns:
#   - apps/api/app/services/promo_admin_service.py
# inputs:
#   - DB session, campaign parameters, campaign_id UUID
# outputs:
#   - created campaign + raw token tuple, status dict, redemption list, disable confirmation
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-DB-MODELS (PromoCampaign, PromoRedemption)
#   - M-PROMO-CAMPAIGN-SERVICE (hash_promo_token)
# side_effects:
#   - DB writes to promo_campaigns
#   - logs promo.campaign_created and promo.campaign_disabled structured events after commit
# invariants:
#   - raw token is generated in-process via secrets and never stored or logged (returned once for operator output)
#   - display name is validated against C0/C1 control and Bidi characters
#   - starts_at must be timezone-aware
# failure_policy:
#   - raises ValueError / RuntimeError on validation or generation failures
# END_MODULE_CONTRACT: M-PROMO-ADMIN-SERVICE

# START_MODULE_MAP: M-PROMO-ADMIN-SERVICE
# public_entrypoints:
#   - PromoAdminService
#   - validate_display_name
#   - parse_timezone_aware_datetime
#   - generate_promo_token
# semantic_blocks:
#   - VALIDATION_HELPERS: display name, datetime, token generator
#   - ADMIN_SERVICE: PromoAdminService class
# owned_tests:
#   - apps/api/tests/test_promo_admin_cli.py
# END_MODULE_MAP: M-PROMO-ADMIN-SERVICE

from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log_event
from app.db.models import AccessLedger, HoraryCredit, PromoCampaign, PromoRedemption
from app.services.promo_campaign_service import hash_promo_token

PROMO_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
PROMO_LETTER_REGEX = re.compile(r"[a-hj-km-np-z]")


# START_BLOCK: VALIDATION_HELPERS
def validate_display_name(name: str) -> str:
    """Trim and validate display name against length and control/Bidi characters."""
    if not name or not isinstance(name, str):
        raise ValueError("Display name must be a non-empty string")
    name = name.strip()
    if not (1 <= len(name) <= 120):
        raise ValueError("Display name must be between 1 and 120 characters after trimming")
    for ch in name:
        cat = unicodedata.category(ch)
        if cat.startswith("C"):  # Cc, Cf (format/bidi), Cs, Co, Cn
            raise ValueError("Display name contains invalid control or Bidi characters")
    return name


def parse_timezone_aware_datetime(dt_str: str) -> datetime:
    """Parse ISO 8601 string and ensure it is timezone-aware."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception as err:
        raise ValueError(f"Invalid ISO 8601 datetime format: {err}") from err
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Datetime must be timezone-aware (ISO 8601 with Z or timezone offset)")
    return dt.astimezone(timezone.utc)


def generate_promo_token(length: int = 12) -> str:
    """Generate cryptographically secure Base58 promo token of length 12..16."""
    if not (12 <= length <= 16):
        raise ValueError("Token length must be between 12 and 16")
    for _ in range(100):
        candidate = "".join(secrets.choice(PROMO_ALPHABET) for _ in range(length))
        if PROMO_LETTER_REGEX.search(candidate):
            return candidate
    raise RuntimeError("Failed to generate a valid promo token")
# END_BLOCK: VALIDATION_HELPERS


# START_BLOCK: ADMIN_SERVICE
class PromoAdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_campaign(
        self,
        name: str,
        max_redemptions: int,
        starts_at: datetime | None = None,
        activation_days: int = 7,
        access_days: int = 30,
        bonus_credits: int = 50,
        unlock_natal: bool = True,
        token_length: int = 12,
    ) -> tuple[PromoCampaign, str]:
        # START_FUNCTION_CONTRACT: F-M-PROMO-ADMIN-SERVICE.create_campaign
        # purpose: Create a new named promo campaign with generated Base58 token.
        # inputs: campaign parameters
        # returns: tuple[PromoCampaign, raw_token]
        # side_effects: DB insert, emits promo.campaign_created after commit
        # emitted_logs: promo.campaign_created
        # error_behavior: raises ValueError on invalid parameters, RuntimeError on hash conflict exhausted
        # END_FUNCTION_CONTRACT: F-M-PROMO-ADMIN-SERVICE.create_campaign

        clean_name = validate_display_name(name)

        if max_redemptions < 1:
            raise ValueError("max_redemptions must be at least 1")
        if activation_days < 1:
            raise ValueError("activation_days must be at least 1")
        if access_days < 0:
            raise ValueError("access_days cannot be negative")
        if bonus_credits < 0:
            raise ValueError("bonus_credits cannot be negative")

        start_time = starts_at or datetime.now(timezone.utc)
        if start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
            raise ValueError("starts_at must be timezone-aware")
        start_time = start_time.astimezone(timezone.utc)
        end_time = start_time + timedelta(days=activation_days)

        # Generate token with collision check
        token: str | None = None
        code_hash: str | None = None

        for _ in range(10):
            cand_token = generate_promo_token(token_length)
            cand_hash = hash_promo_token(cand_token)
            existing = await self.db.scalar(
                select(PromoCampaign).where(PromoCampaign.code_hash == cand_hash)
            )
            if existing is None:
                token = cand_token
                code_hash = cand_hash
                break

        if not token or not code_hash:
            raise RuntimeError("Failed to generate unique promo token hash after multiple attempts")

        campaign = PromoCampaign(
            display_name=clean_name,
            code_hash=code_hash,
            active=True,
            activation_starts_at=start_time,
            activation_ends_at=end_time,
            max_redemptions=max_redemptions,
            redemptions_used=0,
            access_days=access_days,
            bonus_credits=bonus_credits,
            unlock_natal=unlock_natal,
        )

        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)

        # Emit log after commit without name, token or hash
        log_event(
            "promo.campaign_created",
            payload={
                "campaign_id": str(campaign.id),
                "max_redemptions": campaign.max_redemptions,
                "access_days": campaign.access_days,
                "bonus_credits": campaign.bonus_credits,
                "unlock_natal": campaign.unlock_natal,
            },
        )

        return campaign, token

    async def get_campaign_status(self, campaign_id: uuid.UUID) -> dict[str, Any]:
        campaign = await self.db.scalar(
            select(PromoCampaign).where(PromoCampaign.id == campaign_id)
        )
        if not campaign:
            raise ValueError(f"Campaign with ID {campaign_id} not found")

        redemption_count = (
            await self.db.scalar(
                select(func.count(PromoRedemption.id)).where(
                    PromoRedemption.campaign_id == campaign.id
                )
            )
        ) or 0

        counter_consistent = campaign.redemptions_used == redemption_count

        return {
            "campaignId": str(campaign.id),
            "displayName": campaign.display_name,
            "active": campaign.active,
            "activationStartsAt": campaign.activation_starts_at.isoformat(),
            "activationEndsAt": campaign.activation_ends_at.isoformat(),
            "maxRedemptions": campaign.max_redemptions,
            "redemptionsUsed": campaign.redemptions_used,
            "redemptionsCount": redemption_count,
            "counterConsistent": counter_consistent,
            "offer": {
                "accessDays": campaign.access_days,
                "bonusCredits": campaign.bonus_credits,
                "unlockNatal": campaign.unlock_natal,
            },
        }

    async def list_redemptions(
        self, campaign_id: uuid.UUID, limit: int = 50
    ) -> list[dict[str, Any]]:
        campaign = await self.db.scalar(
            select(PromoCampaign).where(PromoCampaign.id == campaign_id)
        )
        if not campaign:
            raise ValueError(f"Campaign with ID {campaign_id} not found")

        stmt = (
            select(PromoRedemption, AccessLedger, HoraryCredit)
            .outerjoin(AccessLedger, PromoRedemption.access_ledger_id == AccessLedger.id)
            .outerjoin(HoraryCredit, PromoRedemption.credit_id == HoraryCredit.id)
            .where(PromoRedemption.campaign_id == campaign_id)
            .order_by(PromoRedemption.redeemed_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()

        return [
            {
                "redemptionId": str(r.id),
                "userId": str(r.user_id),
                "redeemedAt": r.redeemed_at.isoformat(),
                "accessStartsAt": al.starts_at.isoformat() if al else None,
                "accessUntil": al.ends_at.isoformat() if al else None,
                "bonusCredits": hc.amount if hc else 0,
                "natalUnlocked": bool(r.natal_purchase_id),
            }
            for r, al, hc in rows
        ]

    async def disable_campaign(self, campaign_id: uuid.UUID) -> dict[str, Any]:
        stmt = select(PromoCampaign).where(PromoCampaign.id == campaign_id).with_for_update()
        campaign = await self.db.scalar(stmt)
        if not campaign:
            raise ValueError(f"Campaign with ID {campaign_id} not found")

        if not campaign.active:
            return {
                "campaignId": str(campaign.id),
                "active": False,
                "disabled": True,
            }

        campaign.active = False
        await self.db.commit()

        log_event(
            "promo.campaign_disabled",
            payload={"campaign_id": str(campaign.id)},
        )

        return {
            "campaignId": str(campaign.id),
            "active": False,
            "disabled": True,
        }
# END_BLOCK: ADMIN_SERVICE
