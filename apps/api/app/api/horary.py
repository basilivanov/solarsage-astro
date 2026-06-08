# AI_HEADER
# module: M-API-HORARY
# wave: W-HORARY
# purpose: API router for horary questions

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
            blocks=blocks,
            planets=planets,
            generated_at=q.answer.generated_at.isoformat(),
        )

    spent_source = None
    if q.spent_credit:
        spent_source = q.spent_credit.source

    return HoraryQuestionRead(
        id=str(q.id),
        text=q.text,
        category=q.category,
        status=q.status,
        spent_credit_source=spent_source,
        client_timezone=q.client_timezone,
        client_local_time=q.client_local_time,
        created_at=q.created_at.isoformat(),
        answer=answer_read,
    )


@router.get("/horary/quota", response_model=HoraryQuotaRead)
async def get_horary_quota(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> HoraryQuotaRead:
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
    service = HoraryService(db)
    now = datetime.now(timezone.utc)

    try:
        # Atomic database transaction (commits separately in router)
        question = await service.create_question(user_id, body, now)
        await db.commit()
        
        # Enqueue background generation ONLY after commit (fixes B6)
        if question.status == "processing":
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
    service = HoraryService(db)
    question = await service.get_question(user_id, question_id)
    await db.commit()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    return _to_question_read(question)
