# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROMO_ADMIN_CLI
# ROLE: Unit and integration tests for PromoAdminService and promo_campaign CLI.
# DEPENDENCIES: pytest, sqlalchemy, app.services.promo_admin_service, app.cli.promo_campaign
# GRACE_ANCHORS: [TEST_PROMO_ADMIN_CLI]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROMO-ADMIN-CLI
# purpose: Test token generation rules, display name control/bidi validation, timezone-aware datetime parsing, CLI subcommands (create, status, list-redemptions, disable), stdout JSON output shapes, worst-case totals, disable idempotency, and privacy safety (no token/hash/name in logs).
# owns:
#   - apps/api/tests/test_promo_admin_cli.py
# inputs: AsyncSession database fixture and CLI argument lists
# outputs: pytest execution assertions
# dependencies:
#   - app.services.promo_admin_service (PromoAdminService, generate_promo_token, validate_display_name, parse_timezone_aware_datetime)
#   - app.cli.promo_campaign (main, build_parser)
#   - app.db.models (PromoCampaign, PromoRedemption, UserProfile)
# side_effects: database transactions in test runner
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-PROMO-ADMIN-CLI

# START_MODULE_MAP: M-TEST-PROMO-ADMIN-CLI
# public_entrypoints:
#   - test_generate_promo_token_alphabet_and_length
#   - test_validate_display_name_rules_and_rejections
#   - test_parse_timezone_aware_datetime_accepts_utc_and_rejects_naive
#   - test_cli_create_campaign_stdout_shape_and_privacy
#   - test_cli_status_command_counter_consistency
#   - test_cli_list_redemptions_privacy
#   - test_cli_disable_idempotence
#   - test_commit_failure_prevents_event_logging
# owned_tests:
#   - apps/api/tests/test_promo_admin_cli.py
# END_MODULE_MAP: M-TEST-PROMO-ADMIN-CLI

from datetime import datetime, timezone
import json
import sys
import unittest.mock
import uuid
import pytest
from sqlalchemy import select

from app.db.models import PromoCampaign, PromoRedemption, UserProfile, User, HoraryCredit
from app.services.promo_admin_service import (
    PromoAdminService,
    generate_promo_token,
    parse_timezone_aware_datetime,
    validate_display_name,
)
from app.cli.promo_campaign import build_parser, handle_create, handle_status, handle_list_redemptions, handle_disable
from app.services.promo_campaign_service import hash_promo_token


def test_generate_promo_token_alphabet_and_length() -> None:
    for length in (12, 14, 16):
        token = generate_promo_token(length)
        assert len(token) == length
        # Must be valid Base58 lowercase without i, l, o, 0, 1
        assert any(c.isalpha() for c in token)
        for char in token:
            assert char in "23456789abcdefghjkmnpqrstuvwxyz"

    with pytest.raises(ValueError):
        generate_promo_token(11)

    with pytest.raises(ValueError):
        generate_promo_token(17)


def test_validate_display_name_rules_and_rejections() -> None:
    # Valid names
    assert validate_display_name("  Летний Спешл 2026  ") == "Летний Спешл 2026"
    assert validate_display_name("Promo-1") == "Promo-1"

    # Empty / whitespace
    with pytest.raises(ValueError):
        validate_display_name("   ")

    # Too long (> 120 chars)
    with pytest.raises(ValueError):
        validate_display_name("a" * 121)

    # C0 control characters (\n, \r, \t)
    with pytest.raises(ValueError):
        validate_display_name("Promo\nName")

    with pytest.raises(ValueError):
        validate_display_name("Promo\tName")

    # Bidi control characters (U+202E RTL override, U+2066)
    with pytest.raises(ValueError):
        validate_display_name("Promo\u202eName")

    with pytest.raises(ValueError):
        validate_display_name("Promo\u2066Name")


def test_parse_timezone_aware_datetime_accepts_utc_and_rejects_naive() -> None:
    # Valid Z or offset
    dt_z = parse_timezone_aware_datetime("2026-07-25T12:00:00Z")
    assert dt_z.tzinfo == timezone.utc
    assert dt_z.hour == 12

    dt_offset = parse_timezone_aware_datetime("2026-07-25T15:00:00+03:00")
    assert dt_offset.tzinfo == timezone.utc
    assert dt_offset.hour == 12

    # Naive rejection
    with pytest.raises(ValueError):
        parse_timezone_aware_datetime("2026-07-25T12:00:00")


@pytest.mark.asyncio
async def test_cli_create_campaign_stdout_shape_and_privacy(
    db_session, capsys, monkeypatch
) -> None:
    events_logged = []

    def mock_log_event(event: str, payload: dict | None = None, **kwargs):
        events_logged.append((event, payload or {}))

    monkeypatch.setattr("app.services.promo_admin_service.log_event", mock_log_event)

    parser = build_parser()
    args = parser.parse_args([
        "create",
        "--name", "Блогер Июль 2026",
        "--max-redemptions", "100",
        "--access-days", "30",
        "--bonus-credits", "50",
        "--token-length", "12",
    ])

    with unittest.mock.patch("app.cli.promo_campaign.SessionLocal", return_value=db_session):
        exit_code = await handle_create(args)

    assert exit_code == 0

    captured = capsys.readouterr()
    stdout_text = captured.out
    stderr_text = captured.err

    assert stderr_text == ""
    data = json.loads(stdout_text)

    assert "campaignId" in data
    assert data["displayName"] == "Блогер Июль 2026"
    assert "token" in data
    raw_token = data["token"]

    # Raw token format check
    assert len(raw_token) == 12
    assert "https://t.me/" in data["deepLink"]
    assert f"startapp={raw_token}" in data["deepLink"]

    assert data["worstCaseTotals"] == {
        "maximumAccessGrants": 100,
        "maximumBonusCredits": 5000,
        "maximumNatalUnlocks": 100,
    }

    # Privacy check: raw token appears ONLY in stdout, never in DB or log events
    db_campaign = await db_session.scalar(
        select(PromoCampaign).where(PromoCampaign.id == uuid.UUID(data["campaignId"]))
    )
    assert db_campaign is not None
    assert db_campaign.code_hash == hash_promo_token(raw_token)
    assert db_campaign.code_hash != raw_token

    # Logged events check
    assert len(events_logged) == 1
    event_name, event_payload = events_logged[0]
    assert event_name == "promo.campaign_created"
    assert "name" not in event_payload
    assert "token" not in event_payload
    assert "code_hash" not in event_payload
    assert event_payload["campaign_id"] == data["campaignId"]


@pytest.mark.asyncio
async def test_cli_status_command_counter_consistency(
    db_session, capsys
) -> None:
    service = PromoAdminService(db_session)
    campaign, _ = await service.create_campaign("Status Test", max_redemptions=50)

    parser = build_parser()
    args = parser.parse_args(["status", "--campaign-id", str(campaign.id)])

    with unittest.mock.patch("app.cli.promo_campaign.SessionLocal", return_value=db_session):
        exit_code = await handle_status(args)

    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["campaignId"] == str(campaign.id)
    assert data["displayName"] == "Status Test"
    assert data["maxRedemptions"] == 50
    assert data["redemptionsUsed"] == 0
    assert data["redemptionsCount"] == 0
    assert data["counterConsistent"] is True

    # Ensure token and code_hash are never present in status output
    assert "token" not in data
    assert "code_hash" not in data


@pytest.mark.asyncio
async def test_cli_list_redemptions_privacy(
    db_session, capsys
) -> None:
    service = PromoAdminService(db_session)
    campaign, _ = await service.create_campaign("Redemption List Test", max_redemptions=10)

    # Seed user and redemption
    user = User(tg_user_id=881122)
    db_session.add(user)
    await db_session.commit()

    credit = HoraryCredit(user_id=user.id, source="gift", amount=25)
    db_session.add(credit)
    await db_session.flush()

    redemption = PromoRedemption(
        campaign_id=campaign.id,
        user_id=user.id,
        credit_id=credit.id,
        natal_purchase_id=uuid.uuid4(),
    )
    db_session.add(redemption)
    campaign.redemptions_used += 1
    await db_session.commit()

    parser = build_parser()
    args = parser.parse_args(["list-redemptions", "--campaign-id", str(campaign.id)])

    with unittest.mock.patch("app.cli.promo_campaign.SessionLocal", return_value=db_session):
        exit_code = await handle_list_redemptions(args)

    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["campaignId"] == str(campaign.id)
    assert len(data["redemptions"]) == 1
    red = data["redemptions"][0]
    assert red["userId"] == str(user.id)
    assert red["bonusCredits"] == 25
    assert red["natalUnlocked"] is True

    # Privacy check: no Telegram username or PII in list output
    assert "secret_tg_user" not in captured.out
    assert "username" not in captured.out
    assert "first_name" not in captured.out


@pytest.mark.asyncio
async def test_cli_disable_idempotence(
    db_session, capsys, monkeypatch
) -> None:
    events_logged = []

    def mock_log_event(event: str, payload: dict | None = None, **kwargs):
        events_logged.append((event, payload or {}))

    monkeypatch.setattr("app.services.promo_admin_service.log_event", mock_log_event)

    service = PromoAdminService(db_session)
    campaign, _ = await service.create_campaign("Disable Test", max_redemptions=10)
    assert campaign.active is True

    parser = build_parser()
    args = parser.parse_args(["disable", "--campaign-id", str(campaign.id)])

    # First disable call
    with unittest.mock.patch("app.cli.promo_campaign.SessionLocal", return_value=db_session):
        exit_code1 = await handle_disable(args)

    assert exit_code1 == 0
    captured1 = capsys.readouterr()
    data1 = json.loads(captured1.out)
    assert data1["disabled"] is True
    assert data1["active"] is False

    # Second idempotent disable call
    with unittest.mock.patch("app.cli.promo_campaign.SessionLocal", return_value=db_session):
        exit_code2 = await handle_disable(args)

    assert exit_code2 == 0
    captured2 = capsys.readouterr()
    data2 = json.loads(captured2.out)
    assert data2["disabled"] is True

    # Log event logged exactly once on initial disable
    disabled_events = [e for e in events_logged if e[0] == "promo.campaign_disabled"]
    assert len(disabled_events) == 1


@pytest.mark.asyncio
async def test_commit_failure_prevents_event_logging(
    db_session, monkeypatch
) -> None:
    events_logged = []

    def mock_log_event(event: str, payload: dict | None = None, **kwargs):
        events_logged.append((event, payload or {}))

    monkeypatch.setattr("app.services.promo_admin_service.log_event", mock_log_event)

    service = PromoAdminService(db_session)

    # Force commit failure
    with unittest.mock.patch.object(db_session, "commit", side_effect=RuntimeError("DB Commit Failed")):
        with pytest.raises(RuntimeError, match="DB Commit Failed"):
            await service.create_campaign("Failing Campaign", max_redemptions=10)

    # No success event emitted on commit failure
    assert len(events_logged) == 0
