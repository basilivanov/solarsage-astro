# ############################################################################
# AI_HEADER: MODULE_SERVICES_ELECTION_SERVICE
# ROLE: High-level election service for search requests, credit spending, and background execution.
# DEPENDENCIES: sqlalchemy, app.db.models, app.services.election_engine, app.clients.solarsage_client
# GRACE_ANCHORS: [ELECTION_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-ELECTION-SERVICE
# purpose: Manage election search creation, credit consumption, execution, and queries.
# owns:
#   - apps/api/app/services/election_service.py
# inputs: AsyncSession
# outputs: ElectionRequest, ElectionResult
# dependencies:
#   - M-DB-MODELS (ElectionRequest, ElectionResult, ElectionCreditSpend)
#   - M-HORARY-CREDIT-SERVICE (HoraryCreditService)
#   - M-ELECTION-ENGINE (scan)
#   - M-SOLARSAGE-CLIENT (get_solarsage_client)
# side_effects:
#   - creates DB records, consumes credits, calls sidecar
# emitted_logs: election.search_created, election.search_succeeded, election.search_failed, election.credit_refunded
# failure_policy:
#   - raises ValueError / HTTPException on invalid input / no credits
# END_MODULE_CONTRACT: M-ELECTION-SERVICE

# START_MODULE_MAP: M-ELECTION-SERVICE
# public_entrypoints:
#   - ElectionService.create_search
#   - ElectionService.run_search_task
#   - ElectionService.get_quota
#   - ElectionService.list_searches
#   - ElectionService.get_search
# semantic_blocks:
#   - ELECTION_SERVICE: Business logic for election feature
# END_MODULE_MAP: M-ELECTION-SERVICE

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.solarsage_client import get_solarsage_client
from app.core.logging import log_event
from app.db.models import ElectionCreditSpend, ElectionRequest, ElectionResult, HoraryCredit
from app.db.session import SessionLocal
from app.schemas.horary import HoraryQuotaRead
from app.services import election_engine
from app.services.horary_credit_service import HoraryCreditService


class ElectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_search(
        self,
        user_id: uuid.UUID,
        event_type: str,
        window_from: date,
        window_to: date,
        idempotency_key: str,
        client_timezone: str | None = None,
    ) -> ElectionRequest:
        # START_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE.create_search
        # purpose: Validate request, check idempotency, consume 1 horary credit, and create ElectionRequest.
        # inputs: user_id, event_type, window_from, window_to, idempotency_key, client_timezone
        # returns: ElectionRequest
        # side_effects: inserts ElectionRequest, ElectionCreditSpend, updates HoraryCredit
        # error_behavior: 400 invalid date/event, 409 idempotency conflict, 402 no credits
        # END_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE.create_search
        try:
            election_engine.resolve_event(event_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_EVENT_TYPE", "message": str(exc)},
            ) from exc
        if window_to < window_from:
            raise HTTPException(status_code=400, detail="window_to must be >= window_from")

        if (window_to - window_from).days > 62:
            raise HTTPException(status_code=400, detail="Search window cannot exceed 62 days")

        request_hash = hashlib.sha256(
            f"{user_id}|{event_type}|{window_from.isoformat()}|{window_to.isoformat()}".encode("utf-8")
        ).hexdigest()

        # Idempotency check
        existing_stmt = select(ElectionRequest).where(
            and_(
                ElectionRequest.user_id == user_id,
                ElectionRequest.idempotency_key == idempotency_key,
            )
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            if existing.request_hash == request_hash:
                return existing
            raise HTTPException(
                status_code=409,
                detail={"code": "IDEMPOTENCY_CONFLICT", "message": "Idempotency key reused with different params"},
            )

        # Select spendable credit
        credit_service = HoraryCreditService(self.db)
        now_dt = datetime.now(UTC)
        credit = await credit_service.select_spendable_credit(user_id, now_dt)
        if credit is None:
            raise HTTPException(
                status_code=402,
                detail={"code": "NO_HORARY_CREDITS", "message": "No available credits to perform search"},
            )

        # Create request
        request = ElectionRequest(
            user_id=user_id,
            event_type=event_type,
            window_from=window_from,
            window_to=window_to,
            status="pending",
            client_timezone=client_timezone,
            spent_credit_id=credit.id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        self.db.add(request)
        await self.db.flush()

        # Deduct credit & record spend
        credit.used_amount += 1
        spend = ElectionCreditSpend(
            credit_id=credit.id,
            election_request_id=request.id,
            amount=1,
            idempotency_key=idempotency_key,
        )
        self.db.add(spend)
        await self.db.commit()

        log_event("election.search_created", payload={"event_type": event_type})
        return request

    async def run_search_task(self, request_id: uuid.UUID) -> None:
        # START_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE.run_search_task
        # purpose: Background execution wrapper: opens a FRESH session for the
        #   task (the request-scoped session is closed when POST returns —
        #   horary pattern: background tasks must own their session).
        # inputs: request_id (UUID)
        # returns: None
        # side_effects: updates ElectionRequest status, inserts ElectionResult, handles refunds on failure
        # END_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE.run_search_task
        async with SessionLocal() as session:
            self.db = session
            await self._run_search_task(request_id)

    async def _run_search_task(self, request_id: uuid.UUID) -> None:
        # START_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._run_search_task
        # purpose: Fetch sidecar lunar-window, run election_engine, save result.
        # inputs: request_id (UUID)
        # returns: None
        # side_effects: updates ElectionRequest status, inserts ElectionResult, handles refunds on failure
        # END_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._run_search_task
        stmt = select(ElectionRequest).where(ElectionRequest.id == request_id)
        request = (await self.db.execute(stmt)).scalar_one_or_none()
        if request is None or request.status in ("done", "failed", "refunded"):
            return

        request.status = "processing"
        await self.db.commit()

        try:
            client = get_solarsage_client()
            lunar_resp = await client.get_lunar_window(
                from_date=request.window_from.isoformat(),
                to_date=request.window_to.isoformat(),
            )
            lunar_days = lunar_resp.get("days", [])

            # Get user natal_moon_sign from profile / natal_context_service if profile exists
            natal_moon_sign: str | None = None
            try:
                user_stmt = select(User).options(selectinload(User.profile)).where(User.id == request.user_id)
                user_obj = (await self.db.execute(user_stmt)).scalar_one_or_none()
                if user_obj and user_obj.profile and user_obj.profile.is_onboarded:
                    from app.services.natal_context_service import get_or_build_natal_context
                    context_data = await get_or_build_natal_context(self.db, user_obj)
                    natal_moon_sign = (context_data.raw_chart.planets.get("MOON") or {}).get("sign", "").lower() or None
            except Exception as exc:
                log_event(
                    "system.error",
                    level="warn",
                    msg=f"natal moon lookup failed, narrative degraded: {type(exc).__name__}",
                )
                natal_moon_sign = None

            scan_res = await election_engine.scan(
                event_type=request.event_type,
                from_date=request.window_from,
                to_date=request.window_to,
                lunar_days=lunar_days,
                natal_moon_sign=natal_moon_sign,
            )

            # Generate LLM narrative
            from app.services.llm.election import generate_election_narrative
            event_label = (scan_res.get("facts") or {}).get("event", {}).get("label") or request.event_type
            narrative = await generate_election_narrative(
                event_label=event_label,
                best_days=scan_res.get("best_days", []),
                avoid_days=scan_res.get("avoid_days", []),
                personal_facts=(scan_res.get("facts") or {}).get("personal", {}),
            )
            scan_res["narrative"] = narrative

            # Check if result already exists (upsert)
            res_stmt = select(ElectionResult).where(ElectionResult.request_id == request.id)
            existing_res = (await self.db.execute(res_stmt)).scalar_one_or_none()
            payload_str = json.dumps(scan_res, ensure_ascii=False)

            if existing_res is None:
                new_res = ElectionResult(
                    request_id=request.id,
                    payload_json=payload_str,
                )
                self.db.add(new_res)
            else:
                existing_res.payload_json = payload_str

            request.status = "done"
            await self.db.commit()
            log_event("election.search_succeeded")

        except Exception as exc:
            # Handle failure & refund
            await self.db.rollback()

            req_stmt = select(ElectionRequest).where(ElectionRequest.id == request_id)
            request = (await self.db.execute(req_stmt)).scalar_one()

            request.status = "failed"
            request.failure_stage = "engine_execution"
            request.failure_code = type(exc).__name__
            request.failure_message = str(exc)[:500]
            request.public_error_code = "SEARCH_FAILED"
            request.public_error_message = "Failed to calculate election dates. Credit refunded."

            # Perform refund
            if request.spent_credit_id:
                spend_stmt = select(ElectionCreditSpend).where(ElectionCreditSpend.election_request_id == request.id)
                spend = (await self.db.execute(spend_stmt)).scalar_one_or_none()
                if spend:
                    credit_stmt = select(HoraryCredit).where(HoraryCredit.id == request.spent_credit_id)
                    credit = (await self.db.execute(credit_stmt)).scalar_one_or_none()
                    now_dt = datetime.now(UTC)

                    # Check refundability: weekly_free expired cannot be refunded
                    if credit and credit.source == "subscription_weekly_free" and credit.expires_at and credit.expires_at < now_dt:
                        request.refund_status = "not_refundable"
                    else:
                        if credit and credit.used_amount > 0:
                            credit.used_amount -= 1
                        await self.db.delete(spend)
                        request.refund_status = "refunded"
                        request.status = "refunded"
                        log_event("election.credit_refunded")

            await self.db.commit()
            log_event("election.search_failed", payload={"reason": type(exc).__name__})

    async def get_quota(self, user_id: uuid.UUID) -> HoraryQuotaRead:
        credit_service = HoraryCreditService(self.db)
        now_dt = datetime.now(UTC)
        return await credit_service.get_balance(user_id, now_dt)

    async def list_searches(
        self, user_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[ElectionRequest]:
        stmt = (
            select(ElectionRequest)
            .options(selectinload(ElectionRequest.result))
            .where(ElectionRequest.user_id == user_id)
            .order_by(desc(ElectionRequest.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_search(
        self, user_id: uuid.UUID, request_id: uuid.UUID
    ) -> ElectionRequest | None:
        await self._check_lazy_ttl(request_id)
        stmt = (
            select(ElectionRequest)
            .options(selectinload(ElectionRequest.result))
            .where(
                ElectionRequest.user_id == user_id,
                ElectionRequest.id == request_id,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _check_lazy_ttl(self, request_id: uuid.UUID) -> None:
        # START_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._check_lazy_ttl
        # purpose: Mark requests stuck in processing > 5 min as failed and
        #   refund their credit (mirrors horary lazy TTL).
        # inputs: request_id (UUID).
        # returns: none.
        # side_effects: may update request status/refund fields, delete spend
        #   row, decrement credit used_amount; commits.
        # error_behavior: no-ops for missing request or non-processing status.
        # END_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._check_lazy_ttl
        from datetime import timedelta
        request = (
            await self.db.execute(
                select(ElectionRequest).where(ElectionRequest.id == request_id)
            )
        ).scalar_one_or_none()
        if not request or request.status != "processing":
            return
        now = datetime.now(UTC)
        created_at = request.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if now - created_at <= timedelta(minutes=5):
            return
        request.status = "failed"
        request.failure_stage = "lazy_ttl"
        request.failure_code = "PROCESSING_TIMEOUT"
        request.failure_message = "Search stuck in processing over 5 minutes"
        request.public_error_code = "SEARCH_FAILED"
        request.public_error_message = "Failed to calculate election dates. Credit refunded."
        await self._refund_spend(request, now)
        await self.db.commit()

    async def _refund_spend(self, request: ElectionRequest, now: datetime) -> None:
        # START_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._refund_spend
        # purpose: Refund the credit spent by a failed/expired request
        #   (weekly_free expired is not refundable — same rule as run_search_task).
        # inputs: request (ElectionRequest), now (datetime UTC).
        # returns: none.
        # side_effects: deletes spend row, decrements credit used_amount,
        #   sets request.refund_status/status; emits election.credit_refunded.
        # END_FUNCTION_CONTRACT: F-M-ELECTION-SERVICE._refund_spend
        if not request.spent_credit_id:
            return
        spend_stmt = select(ElectionCreditSpend).where(
            ElectionCreditSpend.election_request_id == request.id
        )
        spend = (await self.db.execute(spend_stmt)).scalar_one_or_none()
        if not spend:
            return
        credit_stmt = select(HoraryCredit).where(HoraryCredit.id == request.spent_credit_id)
        credit = (await self.db.execute(credit_stmt)).scalar_one_or_none()
        if credit and credit.source == "subscription_weekly_free" and credit.expires_at and credit.expires_at < now:
            request.refund_status = "not_refundable"
            return
        if credit and credit.used_amount > 0:
            credit.used_amount -= 1
        await self.db.delete(spend)
        request.refund_status = "refunded"
        request.status = "refunded"
        log_event("election.credit_refunded")
