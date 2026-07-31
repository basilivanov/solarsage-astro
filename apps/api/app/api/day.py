# AI_HEADER: MODULE_DAY_API
# module: M-API-DAY
# canon: docs/GRACE_CANON.md §6; docs/work/2026-07-29_today-convergence-rewrite/40_P4_D2_DAY_ENDPOINT_TZ.md
# wave: W-TODAY-CONVERGENCE-REWRITE (P4-D2)
# purpose: GET/POST /api/day/:date endpoints publish and project Today convergence snapshots.

# START_MODULE_CONTRACT: M-API-DAY
# purpose: HTTP surface for /api/day/:date and /api/day/:date/retry. Resolves the
#   user's local date, enforces access, publishes deterministic snapshots, and
#   orchestrates leased Today narrative generation.
# owns:
#   - apps/api/app/api/day.py
# inputs:
#   - date_str: path parameter (YYYY-MM-DD or 'today')
#   - request: correlation context for structured events
#   - user: from require_session dependency, including Telegram identity
#   - db: AsyncSession
# outputs:
#   - TodayConvergencePayload or 202 Retry-After response for a live retry lease
# dependencies:
#   - M-AUTH-TG.dependencies (require_session)
#   - M-ACCESS (AccessService)
#   - M-DB-SESSION (get_session)
#   - M-CONFIG (narrative prompt version and process concurrency)
#   - M-TODAY-CONVERGENCE-RUNTIME (deterministic calculation)
#   - M-TODAY-CONVERGENCE-SNAPSHOT-DOCUMENT (privacy-safe document/hash)
#   - M-TODAY-SNAPSHOT-SERVICE (publication and owner/date head lookup)
#   - M-TODAY-NARRATIVE-LEASE-SERVICE (persistent single-flight lease)
#   - M-TODAY-NARRATIVE (bounded LLM generation)
#   - M-TODAY-CONVERGENCE-PROJECTION (strict wire envelope)
#   - M-USER-LOCAL-DATE (canonical local-date resolver)
# invariants:
#   - 'today' resolves through current_tz → birth_tz → UTC exactly once.
#   - Explicit ISO dates are preserved exactly and never timezone-shifted.
#   - Invalid date format or selected user timezone → 422.
#   - Invalid selected user timezone → 422 INVALID_USER_TIMEZONE.
#   - Not onboarded → 422 NOT_ONBOARDED.
#   - No auth → 401 (from require_session).
#   - Locked requests never calculate or publish a snapshot.
#   - A matching current profile hash never calls the deterministic runtime.
#   - Preview requests never acquire or launch a narrative lease.
#   - Background narrative work always completes ready or unavailable.
# failure_policy:
#   - HTTPException with stable code + message in detail; calculation failures
#     return HTTP 200 with state=unavailable.
# non_goals:
#   - changing TodayService, Today payloads, or convergence/lease internals
# END_MODULE_CONTRACT: M-API-DAY

# START_MODULE_MAP: M-API-DAY
# public_entrypoints:
#   - router
#   - get_day
#   - retry_day
#   - get_focus_event_drilldown
# semantic_blocks:
#   - ROUTE_DAY_GET: GET /api/day/:date handler
#   - ROUTE_DAY_RETRY: POST /api/day/:date/retry handler
#   - DAY_ORCHESTRATION: shared date/access/snapshot/narrative path
#   - DAY_NARRATIVE_BACKGROUND: bounded background completion
#   - ROUTE_FOCUS_EVENT_DRILLDOWN_GET: GET /api/day/:date/focus-event/:event_id handler
# owned_tests:
#   - apps/api/tests/test_day_endpoints.py (W-1.3)
#   - apps/api/tests/test_day_convergence_api.py (P4-D2)
#   - apps/api/tests/test_focus_event_drilldown.py
#   - apps/api/tests/test_user_local_date_consumers.py
# END_MODULE_MAP: M-API-DAY

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date as Date, datetime, timedelta
from math import ceil
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import require_session
from app.core.logging import bind_log_context, log_block, log_event
from app.db.models import User, TodayPayloadCache
from app.db.session import get_session
from app.schemas.today_focus import FocusEventDrilldown
from app.schemas.today_convergence import TodayConvergenceBirthTime, TodayConvergencePayload
from app.services.access_service import AccessService
from app.services.today_birth_time import (
    BirthTimeResolution,
    TodayBirthTimeError,
    resolve_profile_birth_time,
)
from app.services.today_convergence_projection import (
    project_empty_payload,
    project_snapshot_payload,
)
from app.services.today_convergence_runtime import (
    TodayConvergenceCalculationBuilt,
    calculate_today_convergence,
)
from app.services.today_convergence_snapshot import (
    build_today_convergence_snapshot_document,
    compute_today_profile_hash,
)
from app.services.today_narrative_lease_service import (
    NarrativeLeaseClaim,
    NarrativeLeaseSkip,
    TodayNarrativeLeaseService,
)
from app.services.today_narrative_service import (
    TodayNarrativeFailure,
    TodayNarrativeSuccess,
    generate_today_narrative,
)
from app.services.today_snapshot_service import TodaySnapshotService
from app.services.user_local_date import UserLocalDateError, resolve_user_local_date

router = APIRouter(prefix="/api/day", tags=["day"])


_NARRATIVE_LEASE_DURATION = timedelta(minutes=5)
_NARRATIVE_RETRY_DELAY = timedelta(minutes=5)
_ON_DEMAND_LLM_SEMAPHORE = asyncio.Semaphore(
    max(1, settings.today_llm_on_demand_concurrency)
)


def _log_day_event(
    event: str,
    *,
    block: str,
    correlation_id: str | None = None,
    payload: dict[str, object] | None = None,
    error: dict[str, str] | None = None,
) -> None:
    try:
        with log_block(slice="W-TODAY-CONVERGENCE", module="M-API-DAY", block=block):
            if correlation_id:
                bind_log_context(correlation_id=correlation_id)
            log_event(
                event,
                level="error" if event == "system.error" else "info",
                msg="today convergence day boundary",
                payload=payload,
                error=error,
            )
    except Exception:
        # Logging is observability only and must never break the day flow.
        pass


def _request_correlation_id(request: Request) -> str | None:
    state = getattr(request, "state", None)
    value = getattr(state, "correlation_id", None)
    return value if isinstance(value, str) and value else None


def _target_timezone(user: User) -> str:
    profile = user.profile
    timezone_name = (profile.current_tz or profile.birth_tz) if profile is not None else None
    timezone_name = timezone_name or "UTC"
    try:
        ZoneInfo(timezone_name)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_USER_TIMEZONE", "reason": "invalid_timezone"},
        ) from None
    return timezone_name


def _resolve_target_date(user: User, date_str: str) -> tuple[Date, str]:
    timezone_name = _target_timezone(user)
    if date_str == "today":
        try:
            target_date = resolve_user_local_date(user, datetime.now(UTC))
        except UserLocalDateError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_USER_TIMEZONE", "reason": exc.code},
            ) from None
        return target_date, timezone_name

    try:
        target_date = Date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_DATE", "message": "Date must be YYYY-MM-DD or today"},
        ) from None
    if target_date.isoformat() != date_str:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_DATE", "message": "Date must be YYYY-MM-DD or today"},
        )
    return target_date, timezone_name


def _ensure_onboarded(user: User) -> None:
    profile = user.profile
    if (
        profile is None
        or not profile.is_onboarded
        or profile.birth_lat is None
        or profile.birth_lon is None
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": "NOT_ONBOARDED", "message": "User must complete onboarding first"},
        )


def _resolve_birth_time(user: User) -> tuple[BirthTimeResolution, TodayConvergenceBirthTime]:
    try:
        resolution = resolve_profile_birth_time(user.profile)
    except TodayBirthTimeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_BIRTH_TIME_STATE", "reason": str(exc)},
        ) from None
    birth_time = TodayConvergenceBirthTime(
        mode=resolution.mode,
        bucket=resolution.bucket,
        range_start=resolution.range_start,
        range_end=resolution.range_end,
        capabilities={
            "houses": resolution.capabilities.houses,
            "angles": resolution.capabilities.angles,
            "lots": resolution.capabilities.lots,
            "exact_timing": resolution.capabilities.exact_timing,
        },
    )
    return resolution, birth_time


def _viewed_payload(payload: TodayConvergencePayload, request: Request) -> None:
    _log_day_event(
        "day.viewed",
        block="DAY_ORCHESTRATION",
        correlation_id=_request_correlation_id(request),
        payload={
            "access_state": payload.access.state,
            "state": payload.state or "unavailable",
            "content_state": payload.content_state,
        },
    )


def _retry_at() -> datetime:
    return datetime.now(UTC) + _NARRATIVE_RETRY_DELAY


async def _run_narrative_background(
    db: AsyncSession,
    snapshot: object,
    claim: NarrativeLeaseClaim,
    correlation_id: str | None,
) -> None:
    # START_BLOCK: DAY_NARRATIVE_BACKGROUND
    try:
        async with _ON_DEMAND_LLM_SEMAPHORE:
            result = await generate_today_narrative(
                snapshot,
                prompt_version=claim.prompt_version,
                correlation_id=correlation_id,
            )
        lease_service = TodayNarrativeLeaseService(db)
        if isinstance(result, TodayNarrativeSuccess):
            await lease_service.complete_ready(claim, result.content_json)
        elif isinstance(result, TodayNarrativeFailure):
            await lease_service.complete_unavailable(
                claim,
                result.error_code,
                _retry_at(),
            )
        else:
            raise TypeError("today narrative result")
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _log_day_event(
            "system.error",
            block="DAY_NARRATIVE_BACKGROUND",
            correlation_id=correlation_id,
            error={"type": type(exc).__name__},
        )
        try:
            await TodayNarrativeLeaseService(db).complete_unavailable(
                claim,
                "internal_error",
                _retry_at(),
            )
        except Exception as completion_exc:
            _log_day_event(
                "system.error",
                block="DAY_NARRATIVE_BACKGROUND",
                correlation_id=correlation_id,
                error={"type": type(completion_exc).__name__},
            )
    # END_BLOCK: DAY_NARRATIVE_BACKGROUND


async def _project_full_day(
    db: AsyncSession,
    snapshot: object,
    access_state: object,
    background_tasks: BackgroundTasks,
    correlation_id: str | None,
    *,
    retry_requested: bool,
) -> tuple[TodayConvergencePayload, datetime | None]:
    lease_service = TodayNarrativeLeaseService(db)
    narrative = await lease_service.load(snapshot.id, settings.today_narrative_prompt_version)
    claim_or_skip: NarrativeLeaseClaim | NarrativeLeaseSkip | None = None
    if narrative is None or narrative.status != "ready":
        claim_or_skip = await lease_service.acquire(
            snapshot.id,
            settings.today_narrative_prompt_version,
            datetime.now(UTC),
            _NARRATIVE_LEASE_DURATION,
        )
        narrative = await lease_service.load(snapshot.id, settings.today_narrative_prompt_version)
        if isinstance(claim_or_skip, NarrativeLeaseClaim):
            background_tasks.add_task(
                _run_narrative_background,
                db,
                snapshot,
                claim_or_skip,
                correlation_id,
            )
    retry_at = None
    if (
        retry_requested
        and isinstance(claim_or_skip, NarrativeLeaseSkip)
        and claim_or_skip.status == "pending"
    ):
        retry_at = claim_or_skip.retry_at
    payload = project_snapshot_payload(snapshot, narrative, access_state)
    return payload, retry_at


async def _serve_day(
    date_str: str,
    request: Request,
    user: User,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    retry_requested: bool,
) -> tuple[TodayConvergencePayload, datetime | None]:
    # START_BLOCK: DAY_ORCHESTRATION
    target_date, timezone_name = _resolve_target_date(user, date_str)
    _ensure_onboarded(user)
    resolution, birth_time = _resolve_birth_time(user)
    access_state = await AccessService(db).can_access_day(user.id, target_date)

    if access_state.state == "locked":
        payload = project_empty_payload(
            target_date=target_date,
            timezone_name=timezone_name,
            birth_time=birth_time,
            access_state=access_state,
            unavailable=False,
        )
        _viewed_payload(payload, request)
        return payload, None

    profile_hash = compute_today_profile_hash(user.profile, resolution)
    snapshot_service = TodaySnapshotService(db)
    snapshot = await snapshot_service.load_current(user.id, target_date)
    if snapshot is None or snapshot.profile_hash != profile_hash:
        try:
            calculation = await calculate_today_convergence(user.profile, target_date)
        except Exception as exc:
            _log_day_event(
                "system.error",
                block="DAY_ORCHESTRATION",
                correlation_id=_request_correlation_id(request),
                error={"type": type(exc).__name__},
            )
            calculation = None
        if not isinstance(calculation, TodayConvergenceCalculationBuilt):
            payload = project_empty_payload(
                target_date=target_date,
                timezone_name=timezone_name,
                birth_time=birth_time,
                access_state=access_state,
                unavailable=True,
            )
            _viewed_payload(payload, request)
            return payload, None

        document = build_today_convergence_snapshot_document(user.profile, calculation)
        if snapshot is None:
            publication = await snapshot_service.publish_or_load(user.id, document)
        else:
            publication = await snapshot_service.publish_superseding(
                user.id,
                document,
                snapshot.id,
            )
        snapshot = publication.snapshot

    if access_state.state == "preview":
        payload = project_snapshot_payload(snapshot, None, access_state)
        _viewed_payload(payload, request)
        return payload, None

    payload, retry_at = await _project_full_day(
        db,
        snapshot,
        access_state,
        background_tasks,
        _request_correlation_id(request),
        retry_requested=retry_requested,
    )
    _viewed_payload(payload, request)
    return payload, retry_at
    # END_BLOCK: DAY_ORCHESTRATION


def _pending_retry_response(payload: TodayConvergencePayload, retry_at: datetime) -> Response:
    seconds = max(1, ceil((retry_at - datetime.now(UTC)).total_seconds()))
    return JSONResponse(
        status_code=202,
        headers={"Retry-After": str(seconds)},
        content=payload.model_dump(mode="json", by_alias=True),
    )


# START_BLOCK: ROUTE_DAY_GET
@router.get("/{date_str}", response_model=TodayConvergencePayload)
async def get_day(
    date_str: Annotated[str, Path(description="Date in YYYY-MM-DD format or 'today'")],
    request: Request,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks = None,
) -> TodayConvergencePayload:
    # START_FUNCTION_CONTRACT: F-M-API-DAY.get_day
    # purpose: Return one TodayConvergencePayload for a local target date.
    # inputs: date_str, request, background_tasks, authenticated user, and DB session.
    # returns: Strict envelope with locked, preview, unavailable, pending, or ready state.
    # side_effects: access read; optional runtime/sidecar call, snapshot publication,
    #   narrative lease, and leased background generation.
    # emitted_logs: day.snapshot_lookup_hit, day.snapshot_lookup_miss,
    #   day.snapshot_published, day.snapshot_conflict_reused, day.snapshot_superseded,
    #   day.narrative_lease_*, day.narrative_generation_*, day.viewed, system.error.
    # error_behavior: 401 from require_session; 422 for invalid date/timezone,
    #   onboarding, or birth-time state; calculation failure is HTTP 200 unavailable.
    # END_FUNCTION_CONTRACT: F-M-API-DAY.get_day
    payload, _ = await _serve_day(
        date_str,
        request,
        user,
        db,
        background_tasks or BackgroundTasks(),
        retry_requested=False,
    )
    return payload
# END_BLOCK: ROUTE_DAY_GET


# START_BLOCK: ROUTE_DAY_RETRY
@router.post(
    "/{date_str}/retry",
    response_model=TodayConvergencePayload,
    responses={202: {"description": "Narrative lease is still in flight", "model": TodayConvergencePayload}},
)
async def retry_day(
    date_str: Annotated[str, Path(description="Date in YYYY-MM-DD format or 'today'")],
    request: Request,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
    background_tasks: BackgroundTasks = None,
) -> TodayConvergencePayload | Response:
    # START_FUNCTION_CONTRACT: F-M-API-DAY.retry_day
    # purpose: Retry deterministic calculation or narrative generation idempotently.
    # inputs: date_str, request, background_tasks, authenticated user, and DB session.
    # returns: Strict envelope, or 202 with Retry-After for a live pending lease.
    # side_effects: same owner/access/snapshot/lease boundary as get_day.
    # emitted_logs: same day snapshot/narrative lifecycle events as get_day.
    # error_behavior: 401/422 use the GET boundary; live pending returns 202 without a second provider call.
    # END_FUNCTION_CONTRACT: F-M-API-DAY.retry_day
    payload, retry_at = await _serve_day(
        date_str,
        request,
        user,
        db,
        background_tasks or BackgroundTasks(),
        retry_requested=True,
    )
    if retry_at is not None:
        return _pending_retry_response(payload, retry_at)
    return payload
# END_BLOCK: ROUTE_DAY_RETRY


# START_BLOCK: ROUTE_FOCUS_EVENT_DRILLDOWN_GET
@router.get(
    "/{date_str}/focus-event/{event_id:path}",
    response_model=FocusEventDrilldown,
    summary="Get focus event drilldown details",
    description="Get deterministic drilldown for a calculated focus event from cached day payload.",
)
async def get_focus_event_drilldown(
    date_str: str,
    event_id: str = Path(..., description="Focus event ID string"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> FocusEventDrilldown:
    # START_FUNCTION_CONTRACT: F-M-DAY-SERVICE.api.get_focus_event_drilldown
    # purpose: Serve deterministic FocusEventDrilldown for a focus event from cached day payload (§34-50 of E1 TZ).
    # inputs: date_str (str), event_id (str), db (AsyncSession), user (User)
    # returns: FocusEventDrilldown
    # side_effects: reads TodayPayloadCache DB table
    # emitted_logs: none
    # error_behavior: 400 INVALID_DATE, 422 INVALID_USER_TIMEZONE,
    #   404 day_payload_not_cached, 404 event_not_found
    # END_FUNCTION_CONTRACT: F-M-DAY-SERVICE.api.get_focus_event_drilldown
    if date_str == "today":
        try:
            target_date = resolve_user_local_date(user, datetime.now(UTC))
        except UserLocalDateError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_USER_TIMEZONE", "reason": exc.code},
            ) from None
    else:
        try:
            target_date = Date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_DATE", "message": f"Invalid date format: {date_str}"},
            )

    # 1. Read cached payload from TodayPayloadCache table for user_id + target_date
    stmt = select(TodayPayloadCache).where(
        TodayPayloadCache.user_id == user.id,
        TodayPayloadCache.target_date == target_date,
    )
    result = await db.execute(stmt)
    cache_entry = result.scalar_one_or_none()

    if not cache_entry:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "day_payload_not_cached"},
        )

    try:
        payload_dict = json.loads(cache_entry.payload_json)
    except Exception:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "day_payload_not_cached"},
        )

    # 2. Extract focus.events[] from payload_dict
    focus_dict = payload_dict.get("focus") or {}
    events_list = focus_dict.get("events") or []

    # Find event by id == event_id
    matched_event = next((e for e in events_list if e.get("id") == event_id), None)
    if not matched_event:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "event_not_found"},
        )

    # 3. Extract v2.activationEvidence[] matching event's sourceActivationIds
    source_act_ids = set(matched_event.get("sourceActivationIds") or matched_event.get("source_activation_ids") or [])
    v2_dict = payload_dict.get("v2") or {}
    activation_evidence_list = v2_dict.get("activationEvidence") or v2_dict.get("activation_evidence") or []

    matched_evidence = [
        ev for ev in activation_evidence_list
        if (ev.get("id") or ev.get("activationId") or ev.get("activation_id")) in source_act_ids
    ]

    from app.services.focus_event_drilldown_builder import build_focus_event_drilldown
    return build_focus_event_drilldown(event=matched_event, evidence=matched_evidence)
# END_BLOCK: ROUTE_FOCUS_EVENT_DRILLDOWN_GET
