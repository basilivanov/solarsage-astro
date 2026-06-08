# AI_HEADER
# module: M-HORARY-SERVICE
# wave: W-HORARY
# purpose: Service layer for horary questions, answers, and quotas

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.solarsage_client import get_solarsage_client
from app.db.models import HoraryAnswer, HoraryQuestion, HoraryQuota, UserProfile
from app.db.session import SessionLocal
from app.schemas.horary import HoraryQuestionCreate
from app.services.horary_engine import HoraryEngine
from app.services.llm_service import LLMService
from app.services.normalization_service import NormalizationService

logger = logging.getLogger(__name__)


class HoraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_quota(self, user_id: uuid.UUID) -> HoraryQuota:
        """Get or create quota for user (3 free questions initially)."""
        row = (
            await self.db.execute(select(HoraryQuota).where(HoraryQuota.user_id == user_id))
        ).scalar_one_or_none()

        if row is None:
            # First time user: 3 limits, resets in 7 days
            reset_at = datetime.now(timezone.utc) + timedelta(days=7)
            row = HoraryQuota(
                user_id=user_id,
                questions_used=0,
                questions_limit=3,
                reset_at=reset_at,
            )
            self.db.add(row)
            await self.db.flush()
        else:
            # Check for automatic reset
            now = datetime.now(timezone.utc)
            reset_at = row.reset_at
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)
            if now >= reset_at:
                # Add 1 question limit every 7 days (or reset questions_used)
                # Spec: +1 question limit every 7 days, reset_at shifted by +7 days
                row.questions_limit += 1
                row.reset_at = now + timedelta(days=7)
                await self.db.flush()

        return row

    async def check_quota(self, user_id: uuid.UUID) -> bool:
        """Check if user has available questions left."""
        quota = await self.get_or_create_quota(user_id)
        return quota.questions_used < quota.questions_limit

    async def create_question(self, user_id: uuid.UUID, data: HoraryQuestionCreate) -> HoraryQuestion:
        """Create question, consume quota, trigger background answer generation."""
        # 1. Check and fetch quota
        quota = await self.get_or_create_quota(user_id)
        if quota.questions_used >= quota.questions_limit:
            raise ValueError("Horary quota exceeded")

        # 2. Save question
        question = HoraryQuestion(
            user_id=user_id,
            text=data.text,
            category=data.category,
            status="processing",
            client_timezone=data.client_timezone,
            client_local_time=data.client_local_time,
            question_lat=Decimal(str(data.question_lat)) if data.question_lat is not None else None,
            question_lon=Decimal(str(data.question_lon)) if data.question_lon is not None else None,
        )
        self.db.add(question)
        
        # Increment used questions
        quota.questions_used += 1
        await self.db.flush()

        # 3. Trigger background generation
        question_id = question.id
        asyncio.create_task(self._generate_answer_task(question_id))

        return question

    async def get_question(self, user_id: uuid.UUID, question_id: uuid.UUID) -> HoraryQuestion | None:
        """Retrieve a question by ID. Ownership check enforced."""
        # Check lazy TTL timeout first
        await self._check_lazy_ttl(question_id)

        # Query
        question = (
            await self.db.execute(
                select(HoraryQuestion)
                .options(selectinload(HoraryQuestion.answer))
                .where(HoraryQuestion.id == question_id, HoraryQuestion.user_id == user_id)
            )
        ).scalar_one_or_none()

        return question

    async def list_questions(self, user_id: uuid.UUID, limit: int = 20, offset: int = 0) -> list[HoraryQuestion]:
        """List user's questions, newest first."""
        # First check lazy TTLs on all processing questions for this user
        processing_ids = (
            await self.db.execute(
                select(HoraryQuestion.id)
                .where(HoraryQuestion.user_id == user_id, HoraryQuestion.status == "processing")
            )
        ).scalars().all()
        for pid in processing_ids:
            await self._check_lazy_ttl(pid)

        # Now query list
        rows = (
            await self.db.execute(
                select(HoraryQuestion)
                .options(selectinload(HoraryQuestion.answer))
                .where(HoraryQuestion.user_id == user_id)
                .order_by(HoraryQuestion.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        return list(rows)

    async def increase_limit(self, user_id: uuid.UUID, additional: int) -> None:
        """Increase the user's limit of questions (used post purchase)."""
        quota = await self.get_or_create_quota(user_id)
        quota.questions_limit += additional
        await self.db.flush()

    async def _check_lazy_ttl(self, question_id: uuid.UUID) -> None:
        """If question is 'processing' for >5 minutes, mark as 'expired'."""
        question = (
            await self.db.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
        ).scalar_one_or_none()

        if question and question.status == "processing":
            now = datetime.now(timezone.utc)
            created_at = question.created_at.replace(tzinfo=timezone.utc) if question.created_at.tzinfo is None else question.created_at
            if now - created_at > timedelta(minutes=5):
                question.status = "expired"
                await self.db.flush()

    async def _generate_answer_task(self, question_id: uuid.UUID) -> None:
        """Background task running in a new session context to generate the horary answer."""
        async with SessionLocal() as db:
            try:
                # 1. Load entities
                question = (
                    await db.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
                ).scalar_one_or_none()
                if not question:
                    logger.error(f"[Horary Generator] Question {question_id} not found")
                    return

                profile = (
                    await db.execute(select(UserProfile).where(UserProfile.user_id == question.user_id))
                ).scalar_one_or_none()
                if not profile:
                    logger.error(f"[Horary Generator] Profile for user {question.user_id} not found")
                    question.status = "expired"
                    await db.commit()
                    return

                # 2. Resolve coords
                lat = float(question.question_lat) if question.question_lat is not None else float(profile.current_lat or profile.birth_lat or 0.0)
                lon = float(question.question_lon) if question.question_lon is not None else float(profile.current_lon or profile.birth_lon or 0.0)

                # 3. Parse local time
                if question.client_local_time:
                    try:
                        dt = datetime.fromisoformat(question.client_local_time)
                    except ValueError:
                        dt = datetime.now(timezone.utc)
                else:
                    dt = datetime.now(timezone.utc)

                date_str = dt.date().isoformat()
                time_str = dt.time().strftime("%H:%M")

                # 4. Fetch natal + transits from sidecar
                client = get_solarsage_client()
                horary_chart = await client.get_natal(
                    birth_date=date_str,
                    birth_time=time_str,
                    birth_lat=lat,
                    birth_lon=lon,
                    birth_tz=question.client_timezone,
                )

                transits = await client.get_transits(
                    target_date=date_str,
                    target_time=time_str,
                    target_tz=question.client_timezone,
                )

                # 5. Normalize
                normalization_service = NormalizationService()
                signals = normalization_service.normalize(horary_chart, transits)

                # 6. Compute verdict
                verdict, confidence, involved = HoraryEngine.compute_verdict(
                    horary_chart, signals, question.category
                )

                # 7. LLM narration
                llm_service = LLMService()
                
                # Resolve Ascendant and Ruler to pass to LLM
                special_points = horary_chart.get("special_points", [])
                asc_point = next((sp for sp in special_points if sp["name"] == "ASC"), None)
                asc_lon = asc_point["longitude"] if asc_point else 0.0
                from app.services.horary_engine import SIGNS, SIGN_RULERS
                asc_sign = SIGNS[int(asc_lon / 30) % 12]
                asc_ruler = SIGN_RULERS.get(asc_sign, "MARS").title()
                significator = HoraryEngine.get_significator(question.category)

                llm_resp = await llm_service.generate_horary_answer(
                    question_text=question.text,
                    category=question.category,
                    verdict=verdict,
                    confidence=confidence,
                    involved_planets=involved,
                    asc_ruler=asc_ruler,
                    significator=significator,
                )

                # 8. Save Answer
                answer = HoraryAnswer(
                    question_id=question.id,
                    verdict=verdict,
                    confidence=confidence,
                    blocks_json=json.dumps(llm_resp["blocks"], ensure_ascii=False),
                    planets_json=json.dumps(involved, ensure_ascii=False),
                )
                db.add(answer)
                question.status = "answered"
                await db.commit()
                logger.info(f"[Horary Generator] Successfully generated answer for question {question_id}")

            except Exception as e:
                logger.error(f"[Horary Generator] Error generating answer for question {question_id}: {e}", exc_info=True)
                try:
                    # Update status to expired on failure
                    question = (
                        await db.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
                    ).scalar_one_or_none()
                    if question:
                        question.status = "expired"
                        await db.commit()
                except Exception as rollback_err:
                    logger.error(f"[Horary Generator] Rollback state update failed: {rollback_err}")
