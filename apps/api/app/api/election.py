# ############################################################################
# AI_HEADER: MODULE_API_ELECTION
# ROLE: HTTP surface for /api/election (GET, POST).
# DEPENDENCIES: fastapi, sqlalchemy, app.services.election_service
# GRACE_ANCHORS: [ROUTE_ELECTION_QUOTA, ROUTE_ELECTION_SEARCHES]
# ############################################################################

# START_MODULE_CONTRACT: M-API-ELECTION
# purpose: GET /api/election/quota, POST /api/election/searches, GET /api/election/searches, GET /api/election/searches/{id}.
# owns:
#   - apps/api/app/api/election.py
# inputs:
#   - user_id from require_session
#   - DB session
# outputs:
#   - APIRouter with election endpoints
# dependencies:
#   - M-ELECTION-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects: creates searches, spends credits, triggers background task
# emitted_logs: none (handled by service)
# failure_policy: standard 400/401/402/404/409 HTTP exceptions
# END_MODULE_CONTRACT: M-API-ELECTION

# START_MODULE_MAP: M-API-ELECTION
# public_entrypoints:
#   - router
# END_MODULE_MAP: M-API-ELECTION

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import ElectionRequest, User
from app.db.session import get_session
from app.schemas.election import (
    ElectionSearchCreateRequest,
    ElectionSearchRead,
)
from app.schemas.horary import HoraryQuotaRead
from app.services.election_service import ElectionService

router = APIRouter(prefix="/api/election", tags=["election"])


def _to_read(request: ElectionRequest) -> ElectionSearchRead:
    result_dict = None
    if request.result and request.result.payload_json:
        try:
            result_dict = json.loads(request.result.payload_json)
        except Exception:
            result_dict = None

    return ElectionSearchRead(
        id=request.id,
        eventType=request.event_type,
        windowFrom=request.window_from,
        windowTo=request.window_to,
        status=request.status,
        createdAt=request.created_at,
        result=result_dict,
        publicErrorCode=request.public_error_code,
        publicErrorMessage=request.public_error_message,
    )


@router.get("/quota", response_model=HoraryQuotaRead)
async def get_election_quota(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> HoraryQuotaRead:
    service = ElectionService(db)
    return await service.get_quota(user.id)


@router.post("/searches", response_model=ElectionSearchRead, status_code=status.HTTP_201_CREATED)
async def create_election_search(
    body: ElectionSearchCreateRequest,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ElectionSearchRead:
    service = ElectionService(db)
    request_obj = await service.create_search(
        user_id=user.id,
        event_type=body.event_type,
        window_from=body.window_from,
        window_to=body.window_to,
        idempotency_key=body.idempotency_key,
        client_timezone=body.client_timezone,
    )

    # Refresh ORM object with relationship preloaded before sending response
    search_obj = await service.get_search(user.id, request_obj.id)
    target_obj = search_obj if search_obj is not None else request_obj

    # Spawn background task only if status is pending
    if request_obj.status == "pending":
        asyncio.create_task(service.run_search_task(request_obj.id))

    return _to_read(target_obj)


@router.get("/searches", response_model=list[ElectionSearchRead])
async def list_election_searches(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[ElectionSearchRead]:
    service = ElectionService(db)
    searches = await service.list_searches(user.id, limit=limit, offset=offset)
    return [_to_read(s) for s in searches]


@router.get("/searches/{search_id}", response_model=ElectionSearchRead)
async def get_election_search(
    search_id: uuid.UUID,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ElectionSearchRead:
    service = ElectionService(db)
    request_obj = await service.get_search(user.id, search_id)
    if request_obj is None:
        raise HTTPException(status_code=404, detail="Election search request not found")
    return _to_read(request_obj)
