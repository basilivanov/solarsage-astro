# ############################################################################
# AI_HEADER: MODULE_API_HORARY
# ROLE: HTTP surface for /api/horary (GET, POST). Owns UC-HORARY-ASK.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.horary_service
# GRACE_ANCHORS: [ROUTE_QUOTA, ROUTE_LIST, ROUTE_CREATE, ROUTE_GET]
# ############################################################################

# START_MODULE_CONTRACT: M-API-HORARY
# purpose: GET /api/horary/quota, GET /api/horary/questions, POST /api/horary/questions, GET /api/horary/questions/{id}.
# owns:
#   - apps/api/app/api/horary.py
# inputs:
#   - user_id from current_user_id dep
#   - DB session
#   - request body conforms to HoraryQuestionCreate
# outputs:
#   - APIRouter with horary endpoints
# invariants:
#   - all endpoints require session auth.
#   - duplicates under same idempotencyKey are idempotent without double spend.
# END_MODULE_CONTRACT: M-API-HORARY

# START_MODULE_MAP: M-API-HORARY
# public_entrypoints:
#   - router
# END_MODULE_MAP: M-API-HORARY

from __future__ import annotations

import uuid
import math
import asyncio
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id
from app.db.session import get_session
from app.schemas.horary import (
    HoraryAnswerRead,
    HoraryQuestionCreate,
    HoraryQuestionRead,
    HoraryQuotaRead,
)
from app.services.horary_service import HoraryService
from app.services.horary_credit_service import HoraryCreditService

router = APIRouter(prefix="/api", tags=["horary"])


def _to_question_read(q) -> HoraryQuestionRead:
    answer_read = None
    if q.status == "answered" and q.answer:
        import json
        try:
            blocks = json.loads(q.answer.blocks_json)
        except Exception:
            blocks = []
        try:
            planets = json.loads(q.answer.planets_json)
        except Exception:
            planets = []

        answer_read = HoraryAnswerRead(
            verdict=q.answer.verdict,
            confidence=q.answer.confidence,
            confidence_label=getattr(q.answer, "confidence_label", None) or "medium",
            confidence_explanation=getattr(q.answer, "confidence_explanation", None) or "",
            blocks=blocks,
            planets=planets,
            generated_at=q.answer.generated_at.isoformat(),
        )

    spent_source = None
    if q.spent_credit:
        spent_source = q.spent_credit.source

    credit_refunded = getattr(q, "refund_status", None) == "refunded"

    return HoraryQuestionRead(
        id=str(q.id),
        text=q.text,
        category=q.category,
        status=q.status,
        spent_credit_source=spent_source,
        credit_refunded=credit_refunded,
        client_timezone=q.client_timezone,
        client_local_time=q.client_local_time,
        question_location_name=q.question_location_name,
        failure_stage=getattr(q, "failure_stage", None),
        public_error_code=getattr(q, "public_error_code", None),
        public_error_message=getattr(q, "public_error_message", None),
        created_at=q.created_at.isoformat(),
        answer=answer_read,
    )


@router.get("/horary/quota", response_model=HoraryQuotaRead)
async def get_horary_quota(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> HoraryQuotaRead:
    # START_FUNCTION_CONTRACT: M-API-HORARY.get_horary_quota
    # purpose: Fetch user's remaining horary credits and next weekly-free details.
    # inputs: user_id (UUID), db (AsyncSession)
    # returns: HoraryQuotaRead
    # side_effects: queries database (HoraryCredit)
    # emitted_logs: none
    # error_behavior: propagates database exceptions
    # END_FUNCTION_CONTRACT: M-API-HORARY.get_horary_quota
    
    credit_service = HoraryCreditService(db)
    now = datetime.now(timezone.utc)
    quota = await credit_service.get_balance(user_id, now)
    await db.commit()
    return quota


@router.get("/horary/questions", response_model=List[HoraryQuestionRead])
async def list_horary_questions(
    limit: int = 20,
    offset: int = 0,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> List[HoraryQuestionRead]:
    # START_FUNCTION_CONTRACT: M-API-HORARY.list_questions
    # purpose: Retrieve a list of the user's past horary questions, newest first.
    # inputs: limit (int), offset (int), user_id (UUID), db (AsyncSession)
    # returns: List[HoraryQuestionRead]
    # side_effects: queries database (HoraryQuestion)
    # emitted_logs: none
    # error_behavior: propagates database exceptions
    # END_FUNCTION_CONTRACT: M-API-HORARY.list_questions
    
    service = HoraryService(db)
    questions = await service.list_questions(user_id, limit=limit, offset=offset)
    await db.commit()
    return [_to_question_read(q) for q in questions]


@router.post(
    "/horary/questions",
    response_model=HoraryQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_horary_question(
    body: HoraryQuestionCreate,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> HoraryQuestionRead:
    # START_FUNCTION_CONTRACT: M-API-HORARY.create_horary_question
    # purpose: Atomically spends a credit and creates a new question; starts background generator.
    # inputs: body (HoraryQuestionCreate), user_id (UUID), db (AsyncSession)
    # returns: HoraryQuestionRead
    # side_effects: inserts question, updates credits, spawns background task
    # emitted_logs: none
    # error_behavior: raises 402 on no credits, 409 on idempotency conflict, propagates DB errors
    # END_FUNCTION_CONTRACT: M-API-HORARY.create_horary_question
    
    service = HoraryService(db)
    now = datetime.now(timezone.utc)

    try:
        # Atomic database transaction (commits separately in router)
        question, created = await service.create_question(user_id, body, now)
        await db.commit()
        
        # Enqueue background generation ONLY after commit (fixes B6)
        if created and question.status == "processing":
            asyncio.create_task(service._generate_answer_task(question.id))

        return _to_question_read(question)

    except ValueError as e:
        err_msg = str(e)
        if err_msg == "NO_HORARY_CREDITS":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="NO_HORARY_CREDITS",
            )
        elif err_msg == "IDEMPOTENCY_CONFLICT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="IDEMPOTENCY_CONFLICT",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )


@router.get("/horary/questions/{question_id}", response_model=HoraryQuestionRead)
async def get_horary_question(
    question_id: uuid.UUID,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> HoraryQuestionRead:
    # START_FUNCTION_CONTRACT: M-API-HORARY.get_horary_question
    # purpose: Retrieve detail context for a single horary question + answer.
    # inputs: question_id (UUID), user_id (UUID), db (AsyncSession)
    # returns: HoraryQuestionRead
    # side_effects: queries database (HoraryQuestion)
    # emitted_logs: none
    # error_behavior: raises 404 if not found / not owned, propagates DB errors
    # END_FUNCTION_CONTRACT: M-API-HORARY.get_horary_question
    
    service = HoraryService(db)
    question = await service.get_question(user_id, question_id)
    await db.commit()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    return _to_question_read(question)
