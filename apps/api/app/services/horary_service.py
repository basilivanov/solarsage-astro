# AI_HEADER
# module: M-HORARY-SERVICE
# wave: W-HORARY
# purpose: Service layer for horary questions, answers, and quotas

from __future__ import annotations

import asyncio
import json
import logging
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.solarsage_client import get_solarsage_client
from app.db.models import HoraryAnswer, HoraryQuestion, UserProfile, HoraryCredit, HoraryCreditSpend
from app.db.session import SessionLocal
from app.schemas.horary import HoraryQuestionCreate
from app.services.horary_engine import HoraryEngine
from app.services.llm_service import LLMService
from app.services.normalization_service import NormalizationService
from app.services.horary_credit_service import HoraryCreditService

logger = logging.getLogger(__name__)


class HoraryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_question(self, user_id: uuid.UUID, data: HoraryQuestionCreate, now: datetime) -> tuple[HoraryQuestion, bool]:
        """
        Create question, validate idempotency, consume credit, and return the (question, created) tuple.
        Does NOT trigger the background generator task (must be triggered after transaction commits).
        """
        # 1. Idempotency validation
        payload_for_hash = {
            "text": data.text,
            "category": data.category,
            "client_timezone": data.client_timezone,
            "client_local_time": data.client_local_time,
            "question_lat": data.question_lat,
            "question_lon": data.question_lon,
            "question_location_name": data.question_location_name,
        }
        payload_json = json.dumps(payload_for_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        request_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        # Check if question with this idempotency key already exists for user
        result = await self.db.execute(
            select(HoraryQuestion)
            .options(selectinload(HoraryQuestion.answer))
            .where(
                and_(
                    HoraryQuestion.user_id == user_id,
                    HoraryQuestion.idempotency_key == data.idempotency_key,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.request_hash == request_hash:
                return existing, False
            else:
                # Same key, different hash -> conflict
                raise ValueError("IDEMPOTENCY_CONFLICT")

        # 2. Resolve/create current weekly-free if active access exists
        credit_service = HoraryCreditService(self.db)
        await credit_service.get_or_create_current_weekly_free(user_id, now)

        # 3. Create question row first, so we have its ID for the spend record
        question_id = uuid.uuid4()

        try:
            spend = await credit_service.spend_credit_for_question(
                user_id=user_id,
                question_id=question_id,
                idempotency_key=data.idempotency_key,
                now=now,
            )
        except ValueError as e:
            if "No spendable horary credits found" in str(e):
                raise ValueError("NO_HORARY_CREDITS")
            raise

        question = HoraryQuestion(
            id=question_id,
            user_id=user_id,
            text=data.text,
            category=data.category,
            status="processing",
            client_timezone=data.client_timezone,
            client_local_time=data.client_local_time,
            question_lat=Decimal(str(data.question_lat)) if data.question_lat is not None else None,
            question_lon=Decimal(str(data.question_lon)) if data.question_lon is not None else None,
            question_location_name=data.question_location_name,
            spent_credit_id=spend.credit_id,
            idempotency_key=data.idempotency_key,
            request_hash=request_hash,
            created_at=now,
        )
        self.db.add(question)
        await self.db.flush()

        return question, True

    async def get_question(self, user_id: uuid.UUID, question_id: uuid.UUID) -> HoraryQuestion | None:
        """Retrieve a question by ID. Ownership check enforced."""
        # Check lazy TTL timeout first
        await self._check_lazy_ttl(question_id)

        # Query
        question = (
            await self.db.execute(
                select(HoraryQuestion)
                .options(selectinload(HoraryQuestion.answer), selectinload(HoraryQuestion.spent_credit))
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
                .options(selectinload(HoraryQuestion.answer), selectinload(HoraryQuestion.spent_credit))
                .where(HoraryQuestion.user_id == user_id)
                .order_by(HoraryQuestion.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        return list(rows)

    async def _check_lazy_ttl(self, question_id: uuid.UUID) -> None:
        """If question is 'processing' for >5 minutes, mark as 'failed' (refund triggers)."""
        question = (
            await self.db.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
        ).scalar_one_or_none()

        if question and question.status == "processing":
            now = datetime.now(timezone.utc)
            created_at = question.created_at.replace(tzinfo=timezone.utc) if question.created_at.tzinfo is None else question.created_at
            if now - created_at > timedelta(minutes=5):
                # We must fail the question and refund it
                question.status = "failed"
                await self.db.flush()
                await self._refund_credit_for_failed_question(self.db, question_id, now)
                await self.db.flush()

    async def _refund_credit_for_failed_question(self, db: AsyncSession, question_id: uuid.UUID, now: datetime) -> None:
        """Refund the spent credit associated with the question if it qualifies."""
        result = await db.execute(
            select(HoraryCreditSpend).where(HoraryCreditSpend.question_id == question_id)
        )
        spend = result.scalar_one_or_none()
        if not spend:
            return

        credit = await db.get(HoraryCredit, spend.credit_id)
        if credit:
            should_refund = True
            if credit.source == "subscription_weekly_free":
                # subscription weekly free is refunded only if we are still inside that access week
                if credit.access_week_end and now >= credit.access_week_end.replace(tzinfo=timezone.utc):
                    should_refund = False

            if should_refund:
                credit.used_amount = max(0, credit.used_amount - 1)
                logger.info(f"[Horary Refund] Refunded credit {credit.id} for failed question {question_id}")
            else:
                logger.info(f"[Horary Refund] Weekly-free credit {credit.id} already expired. Not refunding for question {question_id}")

        # Remove the spend record since we refunded the credit
        await db.delete(spend)

    async def _generate_answer_task(self, question_id: uuid.UUID) -> None:
        """Background task running in a new session context to generate the horary answer."""
        async with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            try:
                # 1. Load entities with lock to prevent race conditions (fixes B3)
                stmt = select(HoraryQuestion).where(HoraryQuestion.id == question_id).with_for_update()
                question = (await db.execute(stmt)).scalar_one_or_none()
                
                if not question:
                    logger.error(f"[Horary Generator] Question {question_id} not found")
                    return

                if question.status != "processing":
                    logger.info(f"[Horary Generator] Question {question_id} is no longer processing (status={question.status}), skipping generation")
                    return

                profile = (
                    await db.execute(select(UserProfile).where(UserProfile.user_id == question.user_id))
                ).scalar_one_or_none()
                if not profile:
                    logger.error(f"[Horary Generator] Profile for user {question.user_id} not found")
                    question.status = "failed"
                    await self._refund_credit_for_failed_question(db, question_id, now)
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

                # 8. Re-lock and save Answer if still processing
                stmt = select(HoraryQuestion).where(HoraryQuestion.id == question_id).with_for_update()
                fresh_question = (await db.execute(stmt)).scalar_one_or_none()
                if not fresh_question or fresh_question.status != "processing":
                    logger.info(f"[Horary Generator] Question {question_id} is no longer processing at save boundary, rolling back and skipping save")
                    await db.rollback()
                    return

                answer = HoraryAnswer(
                    question_id=fresh_question.id,
                    verdict=verdict,
                    confidence=confidence,
                    blocks_json=json.dumps(llm_resp["blocks"], ensure_ascii=False),
                    planets_json=json.dumps(involved, ensure_ascii=False),
                )
                db.add(answer)
                fresh_question.status = "answered"
                await db.commit()
                logger.info(f"[Horary Generator] Successfully generated answer for question {question_id}")

            except Exception as e:
                logger.error(f"[Horary Generator] Error generating answer for question {question_id}: {e}", exc_info=True)
                try:
                    # Update status to failed and refund
                    question = (
                        await db.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
                    ).scalar_one_or_none()
                    if question:
                        question.status = "failed"
                        await db.flush()
                        await self._refund_credit_for_failed_question(db, question_id, now)
                        await db.commit()
                except Exception as rollback_err:
                    logger.error(f"[Horary Generator] Rollback state update failed: {rollback_err}")
