# ############################################################################
# AI_HEADER: TEST_API_TODAY_CONVERGENCE — HTTP orchestration contract suite.
# ROLE: Exercises the public day envelope, snapshot cache boundary, and narrative lease.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-API-TODAY-CONVERGENCE
# purpose: Prove the P4-D2 GET/retry HTTP contract without legacy TodayService wire data.
# owns:
#   - apps/api/tests/test_day_convergence_api.py
# inputs: authenticated test users, stable in-memory snapshot rows, and mocked runtime/LLM boundaries.
# outputs: HTTP evidence for full, preview, locked, unavailable, pending, and retry states.
# dependencies: M-API-DAY, M-TODAY-CONVERGENCE-PROJECTION, M-TODAY-SNAPSHOT-SERVICE,
#   M-TODAY-NARRATIVE-LEASE-SERVICE, and conftest HTTP fixtures.
# side_effects: isolated SQLite auth/profile writes and mocked boundary calls only.
# emitted_logs: day.viewed and day lifecycle events are observed through the route boundary.
# invariants: no sidecar/provider call on locked, preview, or warm deterministic hits;
#   no legacy TodayPayload assertions; retry remains single-flight.
# failure_policy: pytest assertion failure on wire, status, ownership, or orchestration drift.
# END_MODULE_CONTRACT: M-TEST-API-TODAY-CONVERGENCE

# START_MODULE_MAP: M-TEST-API-DAY-CONVERGENCE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - FULL_PATH: cold publish, pending, ready cache hit, and warm no-call behavior.
#   - ACCESS_MATRIX: preview teaser and locked empty envelope.
#   - FAILURE_PATH: unavailable calculation and background exception completion.
#   - RETRY_SINGLE_FLIGHT: retry-after, due retry, ready no-op, and concurrent claims.
#   - VALIDATION: auth, date, timezone, and onboarding boundaries.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-API-DAY-CONVERGENCE

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta, time
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import day as day_api
from app.db.models import TodaySnapshot, TodaySnapshotNarrative, User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.access_service import AccessService
from app.services.today_convergence_runtime import (
    TodayConvergenceCalculationBuilt,
    TodayConvergenceCalculationUnavailable,
)
from app.services.today_narrative_lease_service import (
    NarrativeLeaseClaim,
    NarrativeLeaseCompletion,
    NarrativeLeaseSkip,
)
from app.services.today_narrative_service import TodayNarrativeSuccess
from app.services.today_snapshot_service import TodaySnapshotPublication


TARGET_DATE = date(2026, 7, 31)
PROFILE_HASH = "profile-hash"
PROMPT_VERSION = "today-narrative-v1"
PUBLISHED_AT = datetime(2026, 7, 30, 21, 0, tzinfo=UTC)


def _access(state: str) -> ContentAccessState:
    if state == "full":
        return ContentAccessState(
            state="full",
            reason="active_subscription",
            subscription_active=True,
            access_until="2026-08-31",
        )
    if state == "preview":
        return ContentAccessState(
            state="preview",
            reason="active_referral_days",
            referral_days_left=2,
            subscription_active=False,
            access_until="2026-08-02",
        )
    return ContentAccessState(
        state="locked",
        reason="outside_access_window",
        referral_days_left=0,
        subscription_active=False,
    )


def _factor(event_id: str, *, source_key: str | None = None) -> dict[str, object]:
    return {
        "canonical_event_id": event_id,
        "event_class": "aspect",
        "technique_horizon": "today",
        "source_key": source_key or f"activation-{event_id}",
        "semantic_key": f"semantic-{event_id}",
        "driver_key": f"driver-{event_id}",
        "product_spheres": ["work"],
        "polarity": "tense",
        "exact_at": "2026-07-31T15:40:00+03:00",
        "active_from": "2026-07-31T13:00:00+03:00",
        "active_until": "2026-07-31T18:00:00+03:00",
    }


def _snapshot(user_id, *, target_date: date = TARGET_DATE, profile_hash: str = PROFILE_HASH) -> TodaySnapshot:
    return TodaySnapshot(
        id=uuid4(),
        user_id=user_id,
        target_date=target_date,
        timezone="Europe/Moscow",
        profile_hash=profile_hash,
        input_hash="i" * 64,
        canon_hash="c" * 64,
        formula_version="today-convergence-2",
        calculation_version="ss-calc-1.3.0",
        ephemeris_artifact_id="ephemeris-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        deterministic_result_json={
            "schema_version": "today-deterministic-result.v1",
            "state": "convergence_today",
            "day_tone": "tense",
            "selected": {
                "convergences": [
                    {
                        "group_id": "cvg-hero",
                        "anchor_event_id": "evt-1",
                        "member_event_ids": ["evt-1", "evt-2"],
                        "evidence_event_ids": ["evt-1", "evt-2"],
                        "primary_sphere": "work",
                        "secondary_sphere": "documents",
                        "polarity": "tense",
                        "evidence_level": "high",
                    }
                ],
                "main_event": None,
                "impulses": [],
                "selected_unit_ids": ["evt-1", "evt-2"],
                "selected_spheres": ["work", "documents"],
            },
        },
        canonical_input_json={
            "schema_version": "today-canonical-input.v1",
            "birth_time": {
                "mode": "exact",
                "bucket": None,
                "range": {"start": "14:30", "end": "14:30"},
                "capabilities": {
                    "houses": True,
                    "angles": True,
                    "lots": True,
                    "exact_timing": True,
                },
            },
            "factor_units": [_factor("evt-1"), _factor("evt-2")],
        },
        published_at=PUBLISHED_AT,
    )


def _narrative(snapshot: TodaySnapshot, status: str) -> TodaySnapshotNarrative:
    return TodaySnapshotNarrative(
        id=uuid4(),
        snapshot_id=snapshot.id,
        prompt_version=PROMPT_VERSION,
        status=status,
        content_json={} if status == "ready" else None,
        attempt_count=1,
        lease_until=None if status != "pending" else datetime.now(UTC) + timedelta(minutes=5),
    )


def _claim(snapshot: TodaySnapshot) -> NarrativeLeaseClaim:
    return NarrativeLeaseClaim(
        narrative_id=uuid4(),
        snapshot_id=snapshot.id,
        prompt_version=PROMPT_VERSION,
        attempt_count=1,
        lease_until=datetime.now(UTC) + timedelta(minutes=5),
        outcome="created",
    )


async def _login_onboarded_user(
    async_client,
    db_session: AsyncSession,
    make_initdata,
    *,
    user_id: int,
) -> User:
    login = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=user_id, username=f"today_{user_id}")},
    )
    assert login.status_code == 200, login.text
    user = (await db_session.execute(select(User).where(User.tg_user_id == user_id))).scalar_one()
    await db_session.execute(
        update(UserProfile)
        .where(UserProfile.user_id == user.id)
        .values(
            is_onboarded=True,
            birthday=date(1990, 1, 15),
            birth_time=time(14, 30),
            birth_time_mode="exact",
            birth_time_bucket=None,
            birth_lat=55.7558,
            birth_lon=37.6173,
            birth_tz="Europe/Moscow",
            current_tz="Europe/Moscow",
        )
    )
    await db_session.commit()
    return user


def _install_access(monkeypatch, state: str) -> AsyncMock:
    access = AsyncMock(return_value=_access(state))
    monkeypatch.setattr(AccessService, "can_access_day", access)
    return access


def _install_profile_hash(monkeypatch) -> None:
    monkeypatch.setattr("app.api.day.compute_today_profile_hash", lambda profile, resolution: PROFILE_HASH)


def _install_current_snapshot(monkeypatch, snapshot: TodaySnapshot | None) -> AsyncMock:
    lookup = AsyncMock(return_value=snapshot)
    monkeypatch.setattr("app.api.day.TodaySnapshotService.load_current", lookup)
    return lookup


def _install_lease(monkeypatch, snapshot: TodaySnapshot, *, initial_status: str = "pending") -> dict[str, object]:
    state: dict[str, object] = {"status": initial_status, "claim": _claim(snapshot)}

    async def acquire(*args, **kwargs):
        if state["status"] == "ready":
            return NarrativeLeaseSkip(
                state["claim"].narrative_id,
                snapshot.id,
                PROMPT_VERSION,
                "ready",
                "ready",
                None,
            )
        if state["status"] == "pending" and state.get("claimed"):
            return NarrativeLeaseSkip(
                state["claim"].narrative_id,
                snapshot.id,
                PROMPT_VERSION,
                "pending",
                "in_flight",
                state["claim"].lease_until,
            )
        state["claimed"] = True
        state["status"] = "pending"
        return state["claim"]

    async def load(*args, **kwargs):
        return _narrative(snapshot, state["status"])

    async def complete_ready(*args, **kwargs):
        state["status"] = "ready"
        return NarrativeLeaseCompletion(outcome="completed")

    async def complete_unavailable(*args, **kwargs):
        state["status"] = "unavailable"
        state["unavailable_args"] = args
        return NarrativeLeaseCompletion(outcome="completed")

    acquire_mock = AsyncMock(side_effect=acquire)
    load_mock = AsyncMock(side_effect=load)
    ready_mock = AsyncMock(side_effect=complete_ready)
    unavailable_mock = AsyncMock(side_effect=complete_unavailable)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.acquire", acquire_mock)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.load", load_mock)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.complete_ready", ready_mock)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.complete_unavailable", unavailable_mock)
    state.update(
        acquire_mock=acquire_mock,
        load_mock=load_mock,
        ready_mock=ready_mock,
        unavailable_mock=unavailable_mock,
    )
    return state


def _install_publication(monkeypatch, snapshot: TodaySnapshot) -> AsyncMock:
    publication = AsyncMock(
        return_value=TodaySnapshotPublication(snapshot=snapshot, outcome="published")
    )
    monkeypatch.setattr("app.api.day.TodaySnapshotService.publish_or_load", publication)
    return publication


# START_BLOCK: FULL_PATH
@pytest.mark.asyncio
async def test_full_cold_get_publishes_pending_then_warm_get_is_ready(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60101)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, None)
    publication = _install_publication(monkeypatch, snapshot)
    lease = _install_lease(monkeypatch, snapshot)
    built = object.__new__(TodayConvergenceCalculationBuilt)
    monkeypatch.setattr("app.api.day.calculate_today_convergence", AsyncMock(return_value=built))
    monkeypatch.setattr(
        "app.api.day.build_today_convergence_snapshot_document",
        lambda profile, result: object(),
    )
    generate = AsyncMock(
        return_value=TodayNarrativeSuccess(content_json={}, output_tokens=1, latency_ms=1)
    )
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)

    first = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    assert first.status_code == 200, first.text
    assert first.json()["contentState"] == "pending"
    assert first.json()["snapshotId"] == str(snapshot.id)
    assert generate.await_count == 1
    assert publication.await_count == 1

    second = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    assert second.status_code == 200, second.text
    assert second.json()["contentState"] == "ready"
    assert generate.await_count == 1
    assert lease["acquire_mock"].await_count == 1
# END_BLOCK: FULL_PATH


@pytest.mark.asyncio
async def test_full_warm_hit_never_calls_runtime_or_provider(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60102)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, snapshot)
    lease = _install_lease(monkeypatch, snapshot, initial_status="ready")
    calculate = AsyncMock()
    generate = AsyncMock()
    monkeypatch.setattr("app.api.day.calculate_today_convergence", calculate)
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)

    response = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")

    assert response.status_code == 200, response.text
    assert response.json()["contentState"] == "ready"
    calculate.assert_not_awaited()
    generate.assert_not_awaited()
    lease["acquire_mock"].assert_not_awaited()
# END_BLOCK: FULL_PATH


@pytest.mark.asyncio
async def test_preview_publishes_projection_without_events_or_llm(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60103)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "preview")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, snapshot)
    calculate = AsyncMock()
    generate = AsyncMock()
    lease_acquire = AsyncMock(side_effect=AssertionError("preview acquired narrative lease"))
    monkeypatch.setattr("app.api.day.calculate_today_convergence", calculate)
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.acquire", lease_acquire)

    response = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    payload = response.json()

    assert response.status_code == 200, response.text
    assert payload["access"]["state"] == "preview"
    assert payload["contentState"] == "not_needed"
    assert len(payload["previewTeaser"]["spheres"]) <= 3
    assert payload["events"] == []
    calculate.assert_not_awaited()
    generate.assert_not_awaited()
    lease_acquire.assert_not_awaited()
# END_BLOCK: FULL_PATH


@pytest.mark.asyncio
async def test_locked_returns_empty_envelope_without_snapshot_or_sidecar(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60104)
    _install_access(monkeypatch, "locked")
    lookup = _install_current_snapshot(monkeypatch, None)
    calculate = AsyncMock()
    monkeypatch.setattr("app.api.day.calculate_today_convergence", calculate)
    publish = AsyncMock(side_effect=AssertionError("locked published snapshot"))
    monkeypatch.setattr("app.api.day.TodaySnapshotService.publish_or_load", publish)

    response = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    payload = response.json()

    assert response.status_code == 200, response.text
    assert payload["access"]["state"] == "locked"
    assert payload["state"] is None
    assert payload["snapshotId"] is None
    assert payload["contentState"] == "not_needed"
    lookup.assert_not_awaited()
    calculate.assert_not_awaited()
    publish.assert_not_awaited()
# END_BLOCK: FULL_PATH


@pytest.mark.asyncio
async def test_unavailable_calculation_is_http_200_without_snapshot(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60105)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, None)
    unavailable = TodayConvergenceCalculationUnavailable(
        state="unavailable",
        target_date=TARGET_DATE,
        failure_stage="activation_grid",
        failure_reason="today_convergence_runtime:activation_grid:client_contract",
        target_timezone="Europe/Moscow",
        target_time="12:00",
        birth_time=None,
        facts_audit=None,
        pipeline=None,
    )
    calculate = AsyncMock(return_value=unavailable)
    publish = AsyncMock(side_effect=AssertionError("unavailable published snapshot"))
    monkeypatch.setattr("app.api.day.calculate_today_convergence", calculate)
    monkeypatch.setattr("app.api.day.TodaySnapshotService.publish_or_load", publish)

    response = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    payload = response.json()

    assert response.status_code == 200, response.text
    assert payload["state"] == "unavailable"
    assert payload["snapshotId"] is None
    assert payload["contentState"] == "unavailable"
    publish.assert_not_awaited()
# END_BLOCK: FULL_PATH


# START_BLOCK: RETRY_SINGLE_FLIGHT
@pytest.mark.asyncio
async def test_retry_pending_returns_202_and_retry_after_without_provider_call(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60106)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, snapshot)
    lease_until = datetime.now(UTC) + timedelta(seconds=20)
    pending = NarrativeLeaseSkip(uuid4(), snapshot.id, PROMPT_VERSION, "pending", "in_flight", lease_until)
    acquire = AsyncMock(return_value=pending)
    load = AsyncMock(return_value=_narrative(snapshot, "pending"))
    generate = AsyncMock()
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.acquire", acquire)
    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.load", load)
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)

    response = await async_client.post(f"/api/day/{TARGET_DATE.isoformat()}/retry")

    assert response.status_code == 202, response.text
    assert int(response.headers["retry-after"]) >= 1
    assert response.json()["contentState"] == "pending"
    generate.assert_not_awaited()
# END_BLOCK: RETRY_SINGLE_FLIGHT


@pytest.mark.asyncio
async def test_retry_due_unavailable_claims_again_and_ready_is_noop(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60107)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, snapshot)
    lease = _install_lease(monkeypatch, snapshot, initial_status="unavailable")
    generate = AsyncMock(
        return_value=TodayNarrativeSuccess(content_json={}, output_tokens=1, latency_ms=1)
    )
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)

    response = await async_client.post(f"/api/day/{TARGET_DATE.isoformat()}/retry")

    assert response.status_code == 200, response.text
    assert response.json()["contentState"] == "pending"
    assert generate.await_count == 1

    response = await async_client.post(f"/api/day/{TARGET_DATE.isoformat()}/retry")
    assert response.status_code == 200, response.text
    assert response.json()["contentState"] == "ready"
    assert generate.await_count == 1
    assert lease["acquire_mock"].await_count == 1
# END_BLOCK: RETRY_SINGLE_FLIGHT


@pytest.mark.asyncio
async def test_background_exception_completes_unavailable_with_future_retry(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60108)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, None)
    _install_publication(monkeypatch, snapshot)
    lease = _install_lease(monkeypatch, snapshot)
    monkeypatch.setattr(
        "app.api.day.calculate_today_convergence",
        AsyncMock(return_value=object.__new__(TodayConvergenceCalculationBuilt)),
    )
    monkeypatch.setattr("app.api.day.build_today_convergence_snapshot_document", lambda profile, result: object())
    generate = AsyncMock(side_effect=RuntimeError("provider exploded"))
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)

    response = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")

    assert response.status_code == 200, response.text
    assert response.json()["contentState"] == "pending"
    assert generate.await_count == 1
    assert lease["unavailable_mock"].await_count == 1
    args = lease["unavailable_mock"].await_args.args
    assert args[1] == "internal_error"
    assert args[2] > datetime.now(UTC)
# END_BLOCK: RETRY_SINGLE_FLIGHT


@pytest.mark.asyncio
async def test_two_parallel_retries_have_one_claim_and_one_provider_call(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60109)
    snapshot = _snapshot(user.id)
    _install_access(monkeypatch, "full")
    _install_profile_hash(monkeypatch)
    _install_current_snapshot(monkeypatch, snapshot)
    claim = _claim(snapshot)
    pending = NarrativeLeaseSkip(uuid4(), snapshot.id, PROMPT_VERSION, "pending", "in_flight", claim.lease_until)
    acquire_calls = 0

    async def acquire(*args, **kwargs):
        nonlocal acquire_calls
        acquire_calls += 1
        await asyncio.sleep(0)
        return claim if acquire_calls == 1 else pending

    monkeypatch.setattr("app.api.day.TodayNarrativeLeaseService.acquire", AsyncMock(side_effect=acquire))
    monkeypatch.setattr(
        "app.api.day.TodayNarrativeLeaseService.load",
        AsyncMock(return_value=_narrative(snapshot, "pending")),
    )
    generate = AsyncMock(
        return_value=TodayNarrativeSuccess(content_json={}, output_tokens=1, latency_ms=1)
    )
    monkeypatch.setattr("app.api.day.generate_today_narrative", generate)
    monkeypatch.setattr(
        "app.api.day.TodayNarrativeLeaseService.complete_ready",
        AsyncMock(return_value=NarrativeLeaseCompletion(outcome="completed")),
    )

    responses = await asyncio.gather(
        async_client.post(f"/api/day/{TARGET_DATE.isoformat()}/retry"),
        async_client.post(f"/api/day/{TARGET_DATE.isoformat()}/retry"),
    )

    assert sorted(response.status_code for response in responses) == [200, 202]
    assert acquire_calls == 2
    assert generate.await_count == 1
# END_BLOCK: RETRY_SINGLE_FLIGHT


# START_BLOCK: VALIDATION
@pytest.mark.parametrize(
    ("instant", "timezone_name", "expected"),
    [
        (datetime(2026, 7, 29, 0, 30, tzinfo=UTC), "America/Los_Angeles", date(2026, 7, 28)),
        (datetime(2026, 7, 28, 23, 30, tzinfo=UTC), "Asia/Tokyo", date(2026, 7, 29)),
    ],
)
def test_today_date_uses_selected_user_local_timezone(
    monkeypatch, instant: datetime, timezone_name: str, expected: date
) -> None:
    user = SimpleNamespace(
        profile=SimpleNamespace(current_tz=timezone_name, birth_tz="UTC")
    )
    monkeypatch.setattr(day_api, "datetime", SimpleNamespace(now=lambda _tz: instant))

    target_date, resolved_timezone = day_api._resolve_target_date(user, "today")

    assert target_date == expected
    assert resolved_timezone == timezone_name


def test_explicit_day_date_bypasses_local_date_resolution(monkeypatch) -> None:
    user = SimpleNamespace(
        profile=SimpleNamespace(current_tz="Asia/Tokyo", birth_tz="UTC")
    )
    monkeypatch.setattr(
        day_api,
        "resolve_user_local_date",
        lambda *_args: pytest.fail("explicit date must not resolve local today"),
    )

    target_date, resolved_timezone = day_api._resolve_target_date(user, "2026-07-28")

    assert target_date == date(2026, 7, 28)
    assert resolved_timezone == "Asia/Tokyo"


@pytest.mark.asyncio
async def test_day_validation_requires_auth_and_returns_422_for_date_timezone_and_onboarding(
    async_client, db_session, make_initdata, monkeypatch
) -> None:
    no_session = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    assert no_session.status_code == 401

    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=60110)
    invalid_date = await async_client.get("/api/day/not-a-date")
    assert invalid_date.status_code == 422
    assert invalid_date.json()["detail"]["code"] == "INVALID_DATE"

    await db_session.execute(
        update(UserProfile).where(UserProfile.user_id == user.id).values(current_tz="Not/AZone")
    )
    await db_session.commit()
    invalid_tz = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    assert invalid_tz.status_code == 422
    assert invalid_tz.json()["detail"]["code"] == "INVALID_USER_TIMEZONE"

    await db_session.execute(
        update(UserProfile)
        .where(UserProfile.user_id == user.id)
        .values(current_tz="Europe/Moscow", is_onboarded=False)
    )
    await db_session.commit()
    not_onboarded = await async_client.get(f"/api/day/{TARGET_DATE.isoformat()}")
    assert not_onboarded.status_code == 422
    assert not_onboarded.json()["detail"]["code"] == "NOT_ONBOARDED"
# END_BLOCK: VALIDATION
