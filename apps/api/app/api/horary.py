# AI_HEADER
# module: M-API-HORARY
# wave: W-HORARY
# purpose: API router for horary questions

from __future__ import annotations

import uuid
import math
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

    return HoraryQuestionRead(
        id=str(q.id),
        text=q.text,
        category=q.category,
        status=q.status,
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
    service = HoraryService(db)
    quota = await service.get_or_create_quota(user_id)
    await db.commit()

    left = max(0, quota.questions_limit - quota.questions_used)
    
    # Calculate next_in_days
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    reset_at = quota.reset_at.replace(tzinfo=timezone.utc) if quota.reset_at.tzinfo is None else quota.reset_at
    delta = reset_at - now
    next_in_days = max(1, int(math.ceil(delta.total_seconds() / 86400)))

    return HoraryQuotaRead(
        left=left,
        next_in_days=next_in_days,
        can_purchase=True,
    )


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
    
    try:
        question = await service.create_question(user_id, body)
        await db.commit()
        return _to_question_read(question)
    except ValueError as e:
        if str(e) == "Horary quota exceeded":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Horary quota exceeded",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
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
