# ############################################################################
# AI_HEADER: MODULE_CLI_PROMO_CAMPAIGN — operator CLI for named promo campaigns.
# ROLE: Command-line entrypoint for create, status, list-redemptions, and disable subcommands.
# DEPENDENCIES: argparse, asyncio, json, sys, app.db.session, app.services.promo_admin_service
# GRACE_ANCHORS: [PROMO_CAMPAIGN_CLI]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-CLI-PROMO-CAMPAIGN
# purpose: Expose python -m app.cli.promo_campaign entrypoint for operators to manage promo campaigns securely.
# owns:
#   - apps/api/app/cli/promo_campaign.py
# inputs: CLI flags and subcommands (create, status, list-redemptions, disable)
# outputs: single JSON document on stdout for success; error text on stderr with non-zero exit code on failure
# dependencies:
#   - M-PROMO-ADMIN-SERVICE (PromoAdminService)
#   - M-DB-SESSION (SessionLocal)
#   - M-CONFIG (settings.bot_username)
# side_effects: DB writes via PromoAdminService, prints to stdout/stderr
# invariants:
#   - raw token is output exactly once on create stdout and never stored or logged
#   - status, list-redemptions, disable accept only --campaign-id UUID
# failure_policy: prints error to stderr and exits with status 1
# END_MODULE_CONTRACT: M-CLI-PROMO-CAMPAIGN

# START_MODULE_MAP: M-CLI-PROMO-CAMPAIGN
# public_entrypoints:
#   - main
# semantic_blocks:
#   - CLI_PARSER: argparse configuration and subcommand handlers
# owned_tests:
#   - apps/api/tests/test_promo_admin_cli.py
# END_MODULE_MAP: M-CLI-PROMO-CAMPAIGN

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.promo_admin_service import (
    PromoAdminService,
    parse_timezone_aware_datetime,
)


def _format_error(msg: str) -> None:
    sys.stderr.write(f"Error: {msg}\n")


async def handle_create(args: argparse.Namespace) -> int:
    try:
        starts_at = parse_timezone_aware_datetime(args.starts_at) if args.starts_at else None
    except Exception as err:
        _format_error(str(err))
        return 1

    async with SessionLocal() as db:
        service = PromoAdminService(db)
        try:
            campaign, raw_token = await service.create_campaign(
                name=args.name,
                max_redemptions=args.max_redemptions,
                starts_at=starts_at,
                activation_days=args.activation_days,
                access_days=args.access_days,
                bonus_credits=args.bonus_credits,
                unlock_natal=args.unlock_natal,
                token_length=args.token_length,
            )
        except Exception as err:
            _format_error(str(err))
            return 1

    deep_link = f"https://t.me/{settings.bot_username}/app?startapp={raw_token}"
    maximum_access = campaign.max_redemptions if campaign.access_days > 0 else 0
    maximum_credits = campaign.max_redemptions * campaign.bonus_credits
    maximum_natal = campaign.max_redemptions if campaign.unlock_natal else 0

    out = {
        "campaignId": str(campaign.id),
        "displayName": campaign.display_name,
        "token": raw_token,
        "deepLink": deep_link,
        "active": campaign.active,
        "activationStartsAt": campaign.activation_starts_at.isoformat(),
        "activationEndsAt": campaign.activation_ends_at.isoformat(),
        "maxRedemptions": campaign.max_redemptions,
        "redemptionsUsed": campaign.redemptions_used,
        "offer": {
            "accessDays": campaign.access_days,
            "bonusCredits": campaign.bonus_credits,
            "unlockNatal": campaign.unlock_natal,
        },
        "worstCaseTotals": {
            "maximumAccessGrants": maximum_access,
            "maximumBonusCredits": maximum_credits,
            "maximumNatalUnlocks": maximum_natal,
        },
    }

    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


async def handle_status(args: argparse.Namespace) -> int:
    try:
        campaign_id = uuid.UUID(args.campaign_id)
    except Exception as err:
        _format_error(f"Invalid campaign-id UUID: {err}")
        return 1

    async with SessionLocal() as db:
        service = PromoAdminService(db)
        try:
            status_data = await service.get_campaign_status(campaign_id)
        except Exception as err:
            _format_error(str(err))
            return 1

    sys.stdout.write(json.dumps(status_data, indent=2, ensure_ascii=False) + "\n")
    return 0


async def handle_list_redemptions(args: argparse.Namespace) -> int:
    try:
        campaign_id = uuid.UUID(args.campaign_id)
    except Exception as err:
        _format_error(f"Invalid campaign-id UUID: {err}")
        return 1

    async with SessionLocal() as db:
        service = PromoAdminService(db)
        try:
            redemptions = await service.list_redemptions(campaign_id, limit=args.limit)
        except Exception as err:
            _format_error(str(err))
            return 1

    out = {
        "campaignId": str(campaign_id),
        "redemptions": redemptions,
    }
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    return 0


async def handle_disable(args: argparse.Namespace) -> int:
    try:
        campaign_id = uuid.UUID(args.campaign_id)
    except Exception as err:
        _format_error(f"Invalid campaign-id UUID: {err}")
        return 1

    async with SessionLocal() as db:
        service = PromoAdminService(db)
        try:
            res = await service.disable_campaign(campaign_id)
        except Exception as err:
            _format_error(str(err))
            return 1

    sys.stdout.write(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.promo_campaign",
        description="Operator CLI for named promo campaign management",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create command
    create_p = subparsers.add_parser("create", help="Create a new promo campaign")
    create_p.add_argument("--name", required=True, type=str, help="Display name of campaign")
    create_p.add_argument("--max-redemptions", required=True, type=int, help="Maximum allowed redemptions")
    create_p.add_argument("--starts-at", type=str, default=None, help="Timezone-aware start time (ISO 8601)")
    create_p.add_argument("--activation-days", type=int, default=7, help="Activation window in days")
    create_p.add_argument("--access-days", type=int, default=30, help="Access grant duration in days")
    create_p.add_argument("--bonus-credits", type=int, default=50, help="Bonus credits amount")

    unlock_group = create_p.add_mutually_exclusive_group()
    unlock_group.add_argument("--unlock-natal", dest="unlock_natal", action="store_true", default=True)
    unlock_group.add_argument("--no-unlock-natal", dest="unlock_natal", action="store_false")

    create_p.add_argument("--token-length", type=int, default=12, help="Token length (12..16)")

    # Status command
    status_p = subparsers.add_parser("status", help="Get campaign status")
    status_p.add_argument("--campaign-id", required=True, type=str, help="Campaign UUID")

    # List-redemptions command
    list_p = subparsers.add_parser("list-redemptions", help="List campaign redemptions")
    list_p.add_argument("--campaign-id", required=True, type=str, help="Campaign UUID")
    list_p.add_argument("--limit", type=int, default=50, help="Limit number of redemptions returned")

    # Disable command
    disable_p = subparsers.add_parser("disable", help="Disable a campaign")
    disable_p.add_argument("--campaign-id", required=True, type=str, help="Campaign UUID")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        code = asyncio.run(handle_create(args))
    elif args.command == "status":
        code = asyncio.run(handle_status(args))
    elif args.command == "list-redemptions":
        code = asyncio.run(handle_list_redemptions(args))
    elif args.command == "disable":
        code = asyncio.run(handle_disable(args))
    else:
        _format_error(f"Unknown command: {args.command}")
        code = 1

    sys.exit(code)


if __name__ == "__main__":
    main()
