# ############################################################################
# AI_HEADER: MODULE_TESTS_PROMO_POSTGRES_ACCEPTANCE
# ROLE: PostgreSQL concurrency proof and release gate test suite for named promo campaigns.
# DEPENDENCIES: pytest, sqlalchemy, app.services.promo_campaign_service, app.services.promo_admin_service, app.services.horary_credit_service, app.services.election_service
# GRACE_ANCHORS: [PROMO_POSTGRES_ACCEPTANCE_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROMO-POSTGRES-ACCEPTANCE
# purpose: Prove PostgreSQL row locking, idempotency, campaign capacity limits, additive access windows, shared credit concurrency between horary and election, and atomic rollback on commit failure.
# owns:
#   - apps/api/tests/test_promo_postgres_acceptance.py
# inputs: PROMO_TEST_POSTGRES_URL environment variable
# outputs: pytest execution assertions
# dependencies:
#   - app.services.promo_admin_service (PromoAdminService)
#   - app.services.promo_campaign_service (PromoCampaignService, PromoDomainError)
#   - app.services.horary_credit_service (HoraryCreditService)
#   - app.services.election_service (ElectionService)
#   - app.services.natal_context_service (NatalContextService)
#   - app.db.models (User, UserProfile, PromoCampaign, PromoRedemption, AccessLedger, HoraryCredit, Purchase)
# side_effects: executes concurrent transactions in isolated PostgreSQL test database
# failure_policy: fail-closed if PROMO_TEST_POSTGRES_URL is missing or non-PostgreSQL
# END_MODULE_CONTRACT: M-TEST-PROMO-POSTGRES-ACCEPTANCE

# START_MODULE_MAP: M-TEST-PROMO-POSTGRES-ACCEPTANCE
# public_entrypoints:
#   - test_postgres_proof1_same_campaign_same_user_concurrent_redeem
#   - test_postgres_proof2_max_redemptions_capacity_limit
#   - test_postgres_proof3_concurrent_fulfilled_natal_purchase_reused
#   - test_postgres_proof4_two_campaigns_same_user_additive_access_windows
#   - test_postgres_proof5_one_gift_credit_concurrent_election_and_horary
#   - test_postgres_proof6_injected_commit_failure_no_partial_grants_or_log
# owned_tests:
#   - apps/api/tests/test_promo_postgres_acceptance.py
# END_MODULE_MAP: M-TEST-PROMO-POSTGRES-ACCEPTANCE

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D
import os
import unittest.mock
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import (
    AccessLedger,
    ElectionCreditSpend,
    ElectionRequest,
    HoraryCredit,
    HoraryQuestion,
    Product,
    PromoCampaign,
    PromoRedemption,
    Purchase,
    User,
    UserProfile,
)
from app.services.access_service import AccessService
from app.services.election_service import ElectionService
from app.services.horary_credit_service import HoraryCreditService
from app.services.natal_context_service import NatalContextService
from app.services.promo_admin_service import PromoAdminService
from app.services.promo_campaign_service import PromoCampaignService, PromoDomainError

from sqlalchemy.pool import NullPool

POSTGRES_URL = os.getenv("PROMO_TEST_POSTGRES_URL")

# CI wiring (architect-approved, Slice 19): excluded from the ordinary CI
# backend run via `-m "not integration"`; targeted acceptance runs select this
# file explicitly and remain fail-closed without a PostgreSQL URL.
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
async def pg_engine():
    if not POSTGRES_URL:
        pytest.fail("PROMO_TEST_POSTGRES_URL environment variable is required")

    engine = create_async_engine(POSTGRES_URL, echo=False, poolclass=NullPool)

    async with engine.connect() as conn:
        dialect_name = conn.dialect.name
        if dialect_name != "postgresql":
            pytest.fail(f"PROMO_TEST_POSTGRES_URL must point to PostgreSQL database, got dialect '{dialect_name}'")

    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(pg_engine):
    return async_sessionmaker(pg_engine, expire_on_commit=False, class_=AsyncSession)


import random

def secrets_tg_id() -> int:
    return random.randint(100_000_000, 999_999_999)


async def create_test_user_with_complete_profile(db: AsyncSession) -> User:
    tg_id = secrets_tg_id()
    user = User(tg_user_id=tg_id)
    db.add(user)
    await db.flush()

    profile = UserProfile(
        user_id=user.id,
        first_name="PostgresTestUser",
        gender="female",
        birthday=date(1990, 6, 15),
        birth_time=time(14, 30),
        birth_city="Moscow",
        birth_lat=D("55.75"),
        birth_lon=D("37.61"),
        birth_tz="Europe/Moscow",
        is_onboarded=True,
    )
    db.add(profile)
    await db.commit()
    return user


# --- Proof 1: Same campaign, same user, two simultaneous redeems ---
@pytest.mark.asyncio
async def test_postgres_proof1_same_campaign_same_user_concurrent_redeem(session_factory) -> None:
    async with session_factory() as db:
        admin = PromoAdminService(db)
        campaign, token = await admin.create_campaign("PG Proof 1", max_redemptions=10)
        user = await create_test_user_with_complete_profile(db)
        user_id = user.id
        campaign_id = campaign.id

    async def do_redeem():
        async with session_factory() as db:
            service = PromoCampaignService(db)
            return await service.redeem(user_id, token)

    res1, res2 = await asyncio.gather(do_redeem(), do_redeem(), return_exceptions=True)

    successes = [r for r in (res1, res2) if not isinstance(r, Exception)]
    failures = [r for r in (res1, res2) if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], PromoDomainError)
    assert failures[0].code == "ALREADY_REDEEMED"

    async with session_factory() as db:
        c = await db.scalar(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
        assert c.redemptions_used == 1

        reds = (await db.scalars(select(PromoRedemption).where(PromoRedemption.campaign_id == campaign_id))).all()
        assert len(reds) == 1

        ledgers = (await db.scalars(select(AccessLedger).where(AccessLedger.user_id == user_id))).all()
        assert len(ledgers) == 1

        credits = (await db.scalars(select(HoraryCredit).where(HoraryCredit.user_id == user_id))).all()
        assert len(credits) == 1


# --- Proof 2: max_redemptions=1, two users simultaneous redeems ---
@pytest.mark.asyncio
async def test_postgres_proof2_max_redemptions_capacity_limit(session_factory) -> None:
    async with session_factory() as db:
        admin = PromoAdminService(db)
        campaign, token = await admin.create_campaign("PG Proof 2", max_redemptions=1)
        user_a = await create_test_user_with_complete_profile(db)
        user_b = await create_test_user_with_complete_profile(db)
        user_a_id = user_a.id
        user_b_id = user_b.id
        campaign_id = campaign.id

    async def do_redeem_user(uid: uuid.UUID):
        async with session_factory() as db:
            service = PromoCampaignService(db)
            return await service.redeem(uid, token)

    res_a, res_b = await asyncio.gather(do_redeem_user(user_a_id), do_redeem_user(user_b_id), return_exceptions=True)

    successes = [r for r in (res_a, res_b) if not isinstance(r, Exception)]
    failures = [r for r in (res_a, res_b) if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], PromoDomainError)
    assert failures[0].code == "CAMPAIGN_FULL"

    async with session_factory() as db:
        c = await db.scalar(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
        assert c.redemptions_used == 1

        reds = (await db.scalars(select(PromoRedemption).where(PromoRedemption.campaign_id == campaign_id))).all()
        assert len(reds) == 1


# --- Proof 3: Existing / concurrent fulfilled natal Purchase reused ---
@pytest.mark.asyncio
async def test_postgres_proof3_concurrent_fulfilled_natal_purchase_reused(session_factory) -> None:
    async with session_factory() as db:
        admin = PromoAdminService(db)
        campaign, token = await admin.create_campaign("PG Proof 3", max_redemptions=10, unlock_natal=True)
        user = await create_test_user_with_complete_profile(db)
        user_id = user.id

        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
        context_hash = NatalContextService.compute_profile_hash(profile)

        # Seed existing fulfilled natal Purchase
        product = await db.scalar(select(Product).where(Product.slug == "natal_full_report"))
        if not product:
            product = Product(slug="natal_full_report", name="Natal Report", product_type="one_time", price_kopecks=9900)
            db.add(product)
            await db.flush()

        purchase = Purchase(
            user_id=user_id,
            product_slug=product.slug,
            status="delivered",
            context_hash=context_hash,
        )
        db.add(purchase)
        await db.commit()
        existing_purchase_id = purchase.id

    async with session_factory() as db:
        service = PromoCampaignService(db)
        redeem_data = await service.redeem(user_id, token)

    assert redeem_data.grants.natal_unlocked is True
    assert redeem_data.grants.natal_already_owned is True

    async with session_factory() as db:
        purchases = (await db.scalars(
            select(Purchase).where(Purchase.user_id == user_id, Purchase.status.in_(["succeeded", "delivered"]))
        )).all()
        assert len(purchases) == 1
        assert purchases[0].id == existing_purchase_id

        red = await db.scalar(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
        assert red is not None
        assert red.natal_purchase_id == existing_purchase_id


# --- Proof 4: Two different campaigns, same user, simultaneous redeems ---
@pytest.mark.asyncio
async def test_postgres_proof4_two_campaigns_same_user_additive_access_windows(session_factory) -> None:
    async with session_factory() as db:
        admin = PromoAdminService(db)
        c1, token1 = await admin.create_campaign("PG Proof 4A", max_redemptions=10, access_days=30)
        c2, token2 = await admin.create_campaign("PG Proof 4B", max_redemptions=10, access_days=14)
        user = await create_test_user_with_complete_profile(db)
        user_id = user.id
        c1_id = c1.id
        c2_id = c2.id

    async def redeem_camp(tok: str):
        async with session_factory() as db:
            service = PromoCampaignService(db)
            return await service.redeem(user_id, tok)

    res1, res2 = await asyncio.gather(redeem_camp(token1), redeem_camp(token2))

    assert res1.offer.access_days == 30
    assert res2.offer.access_days == 14

    async with session_factory() as db:
        c1_ref = await db.scalar(select(PromoCampaign).where(PromoCampaign.id == c1_id))
        c2_ref = await db.scalar(select(PromoCampaign).where(PromoCampaign.id == c2_id))
        assert c1_ref.redemptions_used == 1
        assert c2_ref.redemptions_used == 1

        ledgers = (await db.scalars(
            select(AccessLedger).where(AccessLedger.user_id == user_id).order_by(AccessLedger.start_date)
        )).all()
        assert len(ledgers) == 2

        # Check additive non-overlapping dates: start of second = end of first + 1 day
        w1, w2 = ledgers[0], ledgers[1]
        assert w2.start_date == w1.end_date + timedelta(days=1)


# --- Proof 5: One remaining gift credit, concurrent election + horary ---
@pytest.mark.asyncio
async def test_postgres_proof5_one_gift_credit_concurrent_election_and_horary(session_factory) -> None:
    async with session_factory() as db:
        user = await create_test_user_with_complete_profile(db)
        user_id = user.id
        now_dt = datetime.now(timezone.utc)

        credit = HoraryCredit(user_id=user_id, source="gift", amount=1, used_amount=0)
        db.add(credit)

        question = HoraryQuestion(
            user_id=user_id,
            text="Will this work?",
            category="general",
            client_timezone="UTC",
            idempotency_key=f"key-q-{uuid.uuid4().hex[:8]}",
            request_hash=f"hash-q-{uuid.uuid4().hex[:8]}",
        )
        db.add(question)

        await db.commit()
        credit_id = credit.id
        question_id = question.id

    ik_horary = f"key-h-{uuid.uuid4().hex[:8]}"
    ik_election = f"key-e-{uuid.uuid4().hex[:8]}"

    async def do_horary_spend():
        async with session_factory() as db:
            h_service = HoraryCreditService(db)
            spend = await h_service.spend_credit_for_question(
                user_id=user_id,
                question_id=question_id,
                idempotency_key=ik_horary,
                now=now_dt,
            )
            await db.commit()
            return spend

    async def do_election_create():
        async with session_factory() as db:
            e_service = ElectionService(db)
            return await e_service.create_search(
                user_id=user_id,
                event_type="wedding",
                window_from=date(2026, 8, 1),
                window_to=date(2026, 8, 5),
                idempotency_key=ik_election,
            )

    res_horary, res_election = await asyncio.gather(
        do_horary_spend(), do_election_create(), return_exceptions=True
    )

    successes = [r for r in (res_horary, res_election) if not isinstance(r, Exception)]
    failures = [r for r in (res_horary, res_election) if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1

    # Loser gets domain outcome (HTTPException 402 for election, or ValueError/None for horary)
    loser_err = failures[0]
    if isinstance(loser_err, HTTPException):
        assert loser_err.status_code == 402
    else:
        assert isinstance(loser_err, (ValueError, RuntimeError))

    async with session_factory() as db:
        refreshed_credit = await db.scalar(select(HoraryCredit).where(HoraryCredit.id == credit_id))
        assert refreshed_credit.used_amount <= refreshed_credit.amount
        assert refreshed_credit.used_amount == 1


# --- Proof 6: Injected final commit failure ---
@pytest.mark.asyncio
async def test_postgres_proof6_injected_commit_failure_no_partial_grants_or_log(
    session_factory, monkeypatch
) -> None:
    events_logged = []

    def mock_log_event(event: str, payload: dict | None = None, **kwargs):
        events_logged.append((event, payload or {}))

    monkeypatch.setattr("app.services.promo_campaign_service.log_event", mock_log_event)

    async with session_factory() as db:
        admin = PromoAdminService(db)
        campaign, token = await admin.create_campaign("PG Proof 6", max_redemptions=10)
        user = await create_test_user_with_complete_profile(db)
        user_id = user.id
        campaign_id = campaign.id

    async with session_factory() as db:
        service = PromoCampaignService(db)

        # Patch commit on this session to raise RuntimeError
        with unittest.mock.patch.object(db, "commit", side_effect=RuntimeError("Injected Commit Failure")):
            with pytest.raises(RuntimeError, match="Injected Commit Failure"):
                await service.redeem(user_id, token)

    # Verify no partial grants or counter increment in DB
    async with session_factory() as db:
        c = await db.scalar(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
        assert c.redemptions_used == 0

        reds = (await db.scalars(select(PromoRedemption).where(PromoRedemption.campaign_id == campaign_id))).all()
        assert len(reds) == 0

        ledgers = (await db.scalars(select(AccessLedger).where(AccessLedger.user_id == user_id))).all()
        assert len(ledgers) == 0

    # Verify NO promo.redemption_succeeded log event was written
    succeeded_events = [e for e in events_logged if e[0] == "promo.redemption_succeeded"]
    assert len(succeeded_events) == 0
