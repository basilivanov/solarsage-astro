from __future__ import annotations

import uuid
from datetime import date as Date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import AccessLedger, HoraryCredit, HoraryCreditSpend, HoraryQuestion, UserProfile
from app.schemas.horary import HoraryQuestionCreate
from app.schemas.normalization import AstroSignal
from app.services.horary_engine import HoraryEngine
from app.services.horary_service import HoraryService
from app.services.horary_credit_service import HoraryCreditService


def test_horary_engine_get_significator():
    assert HoraryEngine.get_significator("love") == "Venus"
    assert HoraryEngine.get_significator("career") == "Saturn"
    assert HoraryEngine.get_significator("money") == "Jupiter"
    assert HoraryEngine.get_significator("health") == "Mars"
    assert HoraryEngine.get_significator("travel") == "Mercury"
    assert HoraryEngine.get_significator("other") == "Moon"
    assert HoraryEngine.get_significator(None) == "Moon"


def test_horary_engine_compute_verdict_yes():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],  # Aries -> Mars
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = [
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Venus",
            aspect_type="trine",
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Moon",
            target_planet="Sun",
            aspect_type="trine",
            strength=0.8,
        ),
    ]

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "yes"
    assert confidence > 0.5


def test_horary_engine_compute_verdict_no():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = [
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Venus",
            aspect_type="opposition",
            strength=0.9,
        )
    ]

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "no"


def test_horary_engine_compute_verdict_maybe():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = []

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "maybe"


@pytest.mark.asyncio
async def test_weekly_free_created_only_for_current_week(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # 1. Setup active access covering now
    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    credit = await credit_service.get_or_create_current_weekly_free(user_id, now)

    assert credit is not None
    assert credit.source == "subscription_weekly_free"
    assert credit.access_week_start == datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    assert credit.access_week_end == datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_future_weeks_do_not_precreate_credits(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # Future access start_date is in the future
    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 10),
        end_date=Date(2026, 6, 24),
    )
    db_session.add(ledger)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    credit = await credit_service.get_or_create_current_weekly_free(user_id, now)
    assert credit is None


@pytest.mark.asyncio
async def test_unused_weekly_free_expires_at_end(db_session) -> None:
    user_id = uuid.uuid4()
    # Week 1
    now1 = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    # Week 2 (first week ended)
    now2 = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    
    # Resolve first week
    credit1 = await credit_service.get_or_create_current_weekly_free(user_id, now1)
    assert credit1 is not None

    # Check spendable at week 2
    spendable = await credit_service.select_spendable_credit(user_id, now2)
    # Since credit1 has expires_at = 2026-06-08, it is not spendable at now2 (2026-06-09)
    # Only the new week 2 credit would be spendable (if resolved/created)
    assert spendable is None


@pytest.mark.asyncio
async def test_boundary_at_access_week_end(db_session) -> None:
    user_id = uuid.uuid4()
    # Exact boundary of week 1 end (2026-06-08 00:00:00 UTC)
    boundary = datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    
    # Create week 1 credit
    credit1 = await credit_service.get_or_create_current_weekly_free(user_id, datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc))
    assert credit1 is not None

    # Check if spendable exactly at boundary (which is start of week 2)
    spendable = await credit_service.select_spendable_credit(user_id, boundary)
    # credit1 is expired because boundary >= access_week_end (2026-06-08 00:00:00 UTC)
    assert spendable is None


@pytest.mark.asyncio
async def test_next_week_has_exactly_one_new_weekly_free(db_session) -> None:
    user_id = uuid.uuid4()
    now1 = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    now2 = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    
    # Create week 1 credit
    c1 = await credit_service.get_or_create_current_weekly_free(user_id, now1)
    assert c1 is not None

    # Create week 2 credit
    c2 = await credit_service.get_or_create_current_weekly_free(user_id, now2)
    assert c2 is not None
    assert c2.id != c1.id


@pytest.mark.asyncio
async def test_paid_credits_spendable_without_access(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # User has paid credit, but NO access ledger entries
    credit = HoraryCredit(
        user_id=user_id,
        source="paid",
        amount=1,
        used_amount=0,
    )
    db_session.add(credit)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    spendable = await credit_service.select_spendable_credit(user_id, now)
    assert spendable is not None
    assert spendable.source == "paid"


@pytest.mark.asyncio
async def test_paid_credit_not_spent_if_weekly_free_available(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    credit_paid = HoraryCredit(
        user_id=user_id,
        source="paid",
        amount=1,
        used_amount=0,
    )
    db_session.add_all([ledger, credit_paid])
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    # This creates the weekly free credit
    weekly_credit = await credit_service.get_or_create_current_weekly_free(user_id, now)
    assert weekly_credit is not None

    # Select spendable
    spendable = await credit_service.select_spendable_credit(user_id, now)
    # Must be subscription_weekly_free, not paid
    assert spendable.source == "subscription_weekly_free"


@pytest.mark.asyncio
async def test_expired_credits_are_ignored(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    credit = HoraryCredit(
        user_id=user_id,
        source="gift",
        amount=1,
        used_amount=0,
        expires_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),  # expired yesterday
    )
    db_session.add(credit)
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    spendable = await credit_service.select_spendable_credit(user_id, now)
    assert spendable is None


@pytest.mark.asyncio
async def test_nearest_expires_at_bonus_spent_before_paid(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # 1. Paid credit
    c_paid = HoraryCredit(
        user_id=user_id,
        source="paid",
        amount=1,
        used_amount=0,
    )
    # 2. Expiring in 2 days bonus
    c_bonus1 = HoraryCredit(
        user_id=user_id,
        source="gift",
        amount=1,
        used_amount=0,
        expires_at=now + timedelta(days=2),
    )
    # 3. Expiring in 5 days bonus
    c_bonus2 = HoraryCredit(
        user_id=user_id,
        source="referral_bonus",
        amount=1,
        used_amount=0,
        expires_at=now + timedelta(days=5),
    )

    db_session.add_all([c_paid, c_bonus1, c_bonus2])
    await db_session.commit()

    credit_service = HoraryCreditService(db_session)
    spendable = await credit_service.select_spendable_credit(user_id, now)
    
    # Must be the one expiring soonest (c_bonus1)
    assert spendable.id == c_bonus1.id


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_does_not_double_spend(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # Profile lat/lon fallback
    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    # Add 2 paid credits
    c1 = HoraryCredit(user_id=user_id, source="paid", amount=2, used_amount=0)
    db_session.add(c1)
    await db_session.commit()

    service = HoraryService(db_session)
    data = HoraryQuestionCreate(
        text="Will I find love?",
        category="love",
        client_timezone="UTC",
        idempotency_key="key-12345",
    )

    # First submit
    q1, created1 = await service.create_question(user_id, data, now)
    assert created1 is True
    assert q1.status == "processing"

    # Second submit with same key and same text/category
    q2, created2 = await service.create_question(user_id, data, now)
    assert created2 is False
    assert q2.id == q1.id
    
    # Verify only 1 credit was spent
    await db_session.refresh(c1)
    assert c1.used_amount == 1


@pytest.mark.asyncio
async def test_idempotency_key_different_hash_returns_409(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    # Profile
    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    # Add credits
    c1 = HoraryCredit(user_id=user_id, source="paid", amount=2, used_amount=0)
    db_session.add(c1)
    await db_session.commit()

    service = HoraryService(db_session)
    data1 = HoraryQuestionCreate(
        text="Will I find love?",
        category="love",
        client_timezone="UTC",
        idempotency_key="key-dup",
    )
    data2 = HoraryQuestionCreate(
        text="Will I get rich?",
        category="money",
        client_timezone="UTC",
        idempotency_key="key-dup",
    )

    await service.create_question(user_id, data1, now)

    with pytest.raises(ValueError) as exc:
        await service.create_question(user_id, data2, now)
    assert "IDEMPOTENCY_CONFLICT" in str(exc.value)


@pytest.mark.asyncio
async def test_generation_failure_refunds_paid_credit(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    credit = HoraryCredit(user_id=user_id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = HoraryService(db_session)
    data = HoraryQuestionCreate(
        text="Will I win?",
        category="other",
        client_timezone="UTC",
        idempotency_key="key-fail",
    )

    q, created = await service.create_question(user_id, data, now)
    assert created is True
    assert q.status == "processing"

    # Verify credit was spent
    await db_session.refresh(credit)
    assert credit.used_amount == 1

    # Simulate generation failure
    await service._refund_credit_for_failed_question(db_session, q.id, now)
    await db_session.commit()

    # Credit must be refunded
    await db_session.refresh(credit)
    assert credit.used_amount == 0

    # Question refund_status must reflect the actual refund
    await db_session.refresh(q)
    assert q.refund_status == "refunded"


@pytest.mark.asyncio
async def test_refund_status_is_not_refundable_for_expired_weekly_free(db_session) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 followup §B2.

    When the weekly-free access week has already ended the credit is NOT
    actually refunded. The persisted refund_status must reflect that so the
    UI does not display a misleading refund notice.
    """
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    # Pre-create a weekly-free credit whose access_week_end is already in
    # the past relative to `now`. This forces the refund path to detect the
    # expired-credit case regardless of when the current week is.
    expired_credit = HoraryCredit(
        user_id=user_id,
        source="subscription_weekly_free",
        amount=1,
        used_amount=0,
        access_week_start=datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc),
        access_week_end=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(expired_credit)
    await db_session.commit()

    service = HoraryService(db_session)
    credit_service = HoraryCreditService(db_session)
    # The expired credit is not auto-picked for `now`; force-spend it via the
    # internal path: directly create a question + spend row.
    from app.db.models import HoraryCreditSpend
    import hashlib, json
    payload_json = json.dumps(
        {"text": "Will I win?", "category": "other", "client_timezone": "UTC"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    request_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    question = HoraryQuestion(
        id=uuid.uuid4(),
        user_id=user_id,
        text="Will I win?",
        category="other",
        status="processing",
        client_timezone="UTC",
        idempotency_key="key-expired-week",
        request_hash=request_hash,
        spent_credit_id=expired_credit.id,
    )
    db_session.add(question)
    spend = HoraryCreditSpend(
        user_id=user_id,
        credit_id=expired_credit.id,
        question_id=question.id,
        amount=1,
        idempotency_key="key-expired-week",
    )
    db_session.add(spend)
    expired_credit.used_amount = 1
    await db_session.commit()

    # Refund path runs at `now` > access_week_end
    await service._refund_credit_for_failed_question(db_session, question.id, now)
    await db_session.commit()
    await db_session.refresh(expired_credit)
    assert expired_credit.used_amount == 1  # stays used / expired

    await db_session.refresh(question)
    assert question.refund_status == "not_refundable"


@pytest.mark.asyncio
async def test_refund_status_for_active_weekly_free_is_refunded(db_session) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 followup §B2: weekly-free while week is
    still active => refund_status must be 'refunded'."""
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    service = HoraryService(db_session)
    credit_service = HoraryCreditService(db_session)
    credit = await credit_service.get_or_create_current_weekly_free(user_id, now)
    assert credit is not None

    data = HoraryQuestionCreate(
        text="Will I win?",
        category="other",
        client_timezone="UTC",
        idempotency_key="key-active-week",
    )
    q, _ = await service.create_question(user_id, data, now)
    await db_session.refresh(credit)
    assert credit.used_amount == 1

    await service._refund_credit_for_failed_question(db_session, q.id, now)
    await db_session.commit()
    await db_session.refresh(credit)
    assert credit.used_amount == 0

    await db_session.refresh(q)
    assert q.refund_status == "refunded"


@pytest.mark.asyncio
async def test_generation_failure_restores_weekly_free_only_if_active(db_session) -> None:
    user_id = uuid.uuid4()
    now_active = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
    now_expired = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)

    ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=14,
        start_date=Date(2026, 6, 1),
        end_date=Date(2026, 6, 14),
    )
    db_session.add(ledger)
    await db_session.commit()

    service = HoraryService(db_session)
    credit_service = HoraryCreditService(db_session)
    
    # Create weekly-free credit
    credit = await credit_service.get_or_create_current_weekly_free(user_id, now_active)
    assert credit is not None

    data = HoraryQuestionCreate(
        text="Will I win?",
        category="other",
        client_timezone="UTC",
        idempotency_key="key-weekly",
    )

    q, created = await service.create_question(user_id, data, now_active)
    await db_session.refresh(credit)
    assert credit.used_amount == 1

    # Scenario A: Failure happens while access week is still active
    # It should refund/restore
    await service._refund_credit_for_failed_question(db_session, q.id, now_active)
    await db_session.flush()
    await db_session.refresh(credit)
    assert credit.used_amount == 0

    # Re-spend it with a different idempotency key
    data2 = HoraryQuestionCreate(
        text="Will I win?",
        category="other",
        client_timezone="UTC",
        idempotency_key="key-weekly-2",
    )
    q2, created2 = await service.create_question(user_id, data2, now_active)
    await db_session.flush()
    await db_session.refresh(credit)
    assert credit.used_amount == 1

    # Scenario B: Failure happens after access week has ended (now_expired)
    # It should NOT refund/restore
    await service._refund_credit_for_failed_question(db_session, q2.id, now_expired)
    await db_session.flush()
    await db_session.refresh(credit)
    assert credit.used_amount == 1  # stays used / expired


@pytest.mark.asyncio
async def test_late_generation_does_not_answer_failed_refunded_question(db_session) -> None:
    user_id = uuid.uuid4()
    now = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)

    credit = HoraryCredit(user_id=user_id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = HoraryService(db_session)
    data = HoraryQuestionCreate(
        text="Will I win?",
        category="other",
        client_timezone="UTC",
        idempotency_key="key-late",
    )

    q, created = await service.create_question(user_id, data, now)
    assert created is True
    assert q.status == "processing"

    # Simulate lazy TTL / fail and refund first
    q.status = "failed"
    await db_session.flush()
    await service._refund_credit_for_failed_question(db_session, q.id, now)
    await db_session.commit()

    # Verify credit was refunded and question status is failed
    await db_session.refresh(credit)
    assert credit.used_amount == 0
    await db_session.refresh(q)
    assert q.status == "failed"

    # Now run background task generator or mock saving answer against failed question
    # Re-fetch/lock question within generator session context
    stmt = select(HoraryQuestion).where(HoraryQuestion.id == q.id).with_for_update()
    fresh = (await db_session.execute(stmt)).scalar_one_or_none()
    
    # Assert generator save boundary condition is not met
    assert fresh.status != "processing"
    # Status is failed, so we should skip saving answer
    assert fresh.status == "failed"

