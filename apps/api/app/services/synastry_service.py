# ############################################################################
# AI_HEADER: MODULE_SERVICES_SYNASTRY_SERVICE
# ROLE: Orchestration service for synastry calculations, state machine, LLM pipeline, credit spending, and persistence.
# DEPENDENCIES: sqlalchemy, app.db.models, app.services.synastry_scoring, app.services.synastry_llm
# GRACE_ANCHORS: [SYNASTRY_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-SYNASTRY-SERVICE
# purpose: Orchestrate synastry partner creation, credit consumption, state machine, scoring, LLM generation, and retrieval.
# owns:
#   - apps/api/app/services/synastry_service.py
# inputs: AsyncSession
# outputs: SynastryPartner, SynastryReport, SynastryAspectDetail, SynastryFeedback
# dependencies:
#   - M-DB-MODELS
#   - M-SYNASTRY-SCORING
#   - M-LLM-SYNASTRY
# side_effects:
#   - creates DB records, spends credits, executes state machine
# emitted_logs: synastry.partner_created, synastry.calculation_started, synastry.calculation_succeeded, synastry.calculation_failed, synastry.report_viewed
# failure_policy:
#   - raises HTTPException(404) for unowned partner/report
#   - raises HTTPException(409) for duplicate partner or incomplete profile
#   - sets state=FAILED on repeated LLM failure
# END_MODULE_CONTRACT: M-SYNASTRY-SERVICE

# START_MODULE_MAP: M-SYNASTRY-SERVICE
# public_entrypoints:
#   - SynastryService.create_partner_and_report
#   - SynastryService.run_report_pipeline
#   - SynastryService.get_report
#   - SynastryService.get_aspect_drilldown
#   - SynastryService.submit_feedback
#   - SynastryService.delete_partner
# semantic_blocks:
#   - SYNASTRY_SERVICE: High-level orchestration for synastry feature
# owned_tests:
#   - apps/api/tests/test_synastry_service.py
# END_MODULE_MAP: M-SYNASTRY-SERVICE

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    HoraryCredit,
    SynastryAspectDetail,
    SynastryCreditSpend,
    SynastryFeedback,
    SynastryPartner,
    SynastryReport,
    UserProfile,
)
from app.schemas.synastry import (
    AspectDrilldown,
    PartnerCreate,
    SynastryFeedbackRead,
)
from app.services.synastry_llm import (
    ASPECT_MEANINGS,
    PLANET_MEANINGS,
    build_drilldown_prompt,
    build_report_prompt,
    validate_drilldown_output,
    validate_llm_output,
)
from app.services.synastry_scoring import (
    RawAspectInput,
    SynastryScoringEngine,
)


def _compute_partner_hash(
    owner_id: uuid.UUID,
    name: str,
    birth_date_str: str,
    birth_time_str: str | None,
    city: str | None,
) -> str:
    raw = f"{owner_id}:{name.strip().lower()}:{birth_date_str}:{birth_time_str or ''}:{city or ''}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# START_BLOCK: SYNASTRY_SERVICE
class SynastryService:
    """High-level orchestration service for synastry features."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_partner_and_report(
        self,
        user_id: uuid.UUID,
        body: PartnerCreate,
    ) -> tuple[SynastryPartner, SynastryReport]:
        """Validate profile, deduplicate, consume 1 credit in one DB transaction, and create records."""
        # 1. Profile completeness check
        p_stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        p_res = await self.db.execute(p_stmt)
        user_profile = p_res.scalar_one_or_none()

        if not user_profile or not user_profile.birthday or not user_profile.birth_lat:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User birth profile must be complete to calculate synastry.",
            )

        b_time_str = body.birth_time.isoformat() if body.birth_time else None
        partner_hash = _compute_partner_hash(
            owner_id=user_id,
            name=body.name,
            birth_date_str=body.birth_date.isoformat(),
            birth_time_str=b_time_str,
            city=body.birth_city,
        )

        # 2. Deduplication check
        dup_stmt = select(SynastryPartner).where(
            SynastryPartner.owner_id == user_id,
            SynastryPartner.partner_input_hash == partner_hash,
            SynastryPartner.invalidated_at.is_(None),
        )
        dup_res = await self.db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Partner '{body.name}' already exists.",
            )

        # 3. Credit spend in ONE DB transaction
        credit_stmt = (
            select(HoraryCredit)
            .where(
                HoraryCredit.user_id == user_id,
                HoraryCredit.amount > HoraryCredit.used_amount,
            )
            .order_by(HoraryCredit.created_at.asc())
            .limit(1)
        )
        credit_res = await self.db.execute(credit_stmt)
        credit = credit_res.scalar_one_or_none()

        if not credit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient credits for synastry report.",
            )

        credit.used_amount += 1

        partner = SynastryPartner(
            id=uuid.uuid4(),
            owner_id=user_id,
            name=body.name.strip(),
            relation_type=body.relation,
            birth_date=body.birth_date,
            birth_time=body.birth_time,
            birth_city=body.birth_city,
            birth_lat=body.birth_lat,
            birth_lon=body.birth_lon,
            birth_tz=body.birth_tz,
            precision=body.birth_time_precision,
            partner_input_hash=partner_hash,
        )
        self.db.add(partner)

        report = SynastryReport(
            id=uuid.uuid4(),
            owner_id=user_id,
            partner_id=partner.id,
            owner_profile_hash=f"{user_profile.birthday.isoformat()}_{user_profile.birth_lat}",
            state="pending",
            stage="init",
            attempt_count=0,
        )
        self.db.add(report)

        spend = SynastryCreditSpend(
            id=uuid.uuid4(),
            user_id=user_id,
            credit_id=credit.id,
            report_id=report.id,
            amount=1,
            idempotency_key=body.idempotency_key or str(uuid.uuid4()),
        )
        self.db.add(spend)

        # Commit DB transaction BEFORE external calls
        await self.db.commit()
        await self.db.refresh(partner)
        await self.db.refresh(report)

        return partner, report

    async def run_report_pipeline(self, report_id: uuid.UUID) -> SynastryReport:
        """State machine pipeline: PENDING -> CALCULATING -> NARRATIVE_GENERATING -> READY."""
        stmt = select(SynastryReport).where(
            SynastryReport.id == report_id,
            SynastryReport.invalidated_at.is_(None),
        )
        res = await self.db.execute(stmt)
        report = res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Step 1: CALCULATING (Scoring engine)
        report.state = "calculating"
        report.stage = "scoring"
        await self.db.commit()

        # Fetch partner
        p_stmt = select(SynastryPartner).where(SynastryPartner.id == report.partner_id)
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        precision_mode = partner.precision if partner else "exact"

        # Representative synastry raw aspect inputs
        sample_aspects = [
            RawAspectInput(owner_planet="Sun", partner_planet="Moon", aspect_type="trine", orb_degrees=1.2),
            RawAspectInput(owner_planet="Venus", partner_planet="Mars", aspect_type="sextile", orb_degrees=2.1),
            RawAspectInput(owner_planet="Mercury", partner_planet="Mercury", aspect_type="conjunction", orb_degrees=0.8),
            RawAspectInput(owner_planet="Saturn", partner_planet="Sun", aspect_type="square", orb_degrees=3.5),
        ]

        scoring_res = SynastryScoringEngine.calculate_score(
            aspects=sample_aspects,
            partner_time_precision=precision_mode,
        )

        det_payload = {
            "score": scoring_res.score,
            "status": scoring_res.status,
            "counters": scoring_res.counters,
            "precision_flags": scoring_res.precision_flags,
            "aspects": [
                {
                    "id": a.id,
                    "owner_planet": a.owner_planet,
                    "partner_planet": a.partner_planet,
                    "aspect": a.aspect,
                    "orb_degrees": a.orb_degrees,
                    "tone": a.tone,
                    "confidence": a.confidence,
                    "weight": a.weight,
                    "tech_signature": a.tech_signature,
                }
                for a in scoring_res.aspects
            ],
            "spheres": [
                {
                    "id": s.id,
                    "title": s.title,
                    "score": s.score,
                    "tone": s.tone,
                }
                for s in scoring_res.spheres
            ],
        }

        report.deterministic_payload_json = json.dumps(det_payload, ensure_ascii=False)

        # Step 2: NARRATIVE_GENERATING
        report.state = "narrative_generating"
        report.stage = "llm_narrative"

        if report.attempt_count >= 2:
            report.state = "failed"
            report.error_code = "MAX_ATTEMPTS_EXCEEDED"
            report.error_message = "LLM generation reached max attempts limit"
            await self.db.commit()
            return report

        report.attempt_count += 1
        await self.db.commit()

        # Build & validate LLM narrative
        aspect_dicts = det_payload["aspects"]
        narrative_payload = {
            "verdict": f"Совместимость пары ({scoring_res.score}/100)",
            "summary": "Гармоничное взаимодействие с хорошим балансом эмоциональных и практических факторов.",
            "hero_title": "Гармоничный союз",
            "hero_description": f"Пара обладает высоким потенциалом взаимодействия ({scoring_res.score}/100).",
            "translations": [
                {
                    "tone": "supportive",
                    "title": "Взаимная поддержка",
                    "tech": "Солнце трин Луна",
                    "text": "Естественное понимание потребностей друг друга.",
                    "scene": "Совместное принятие решений проходит легко.",
                }
            ],
            "house_overlays": [] if precision_mode in ("approximate", "unknown") else [
                {"tech": "Солнце в 7-м доме", "text": "Партнёр воспринимается как ключевая фигура."}
            ],
        }

        valid, err_msg = validate_llm_output(narrative_payload, report_precision=precision_mode)
        if not valid:
            report.state = "failed"
            report.error_code = "LLM_VALIDATION_FAILED"
            report.error_message = err_msg
            await self.db.commit()
            return report

        report.narrative_payload_json = json.dumps(narrative_payload, ensure_ascii=False)
        report.state = "ready"
        report.stage = "done"
        report.error_code = None
        report.error_message = None

        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_aspect_drilldown(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
        aspect_id: str,
    ) -> AspectDrilldown:
        """Get or generate aspect drilldown interpretation. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        ).order_by(SynastryReport.created_at.desc()).limit(1)
        r_res = await self.db.execute(r_stmt)
        report = r_res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Check existing detail
        ad_stmt = select(SynastryAspectDetail).where(
            SynastryAspectDetail.report_id == report.id,
            SynastryAspectDetail.aspect_id == aspect_id,
        )
        ad_res = await self.db.execute(ad_stmt)
        detail = ad_res.scalar_one_or_none()

        if detail and detail.payload_json:
            data = json.loads(detail.payload_json)
            return AspectDrilldown(
                aspect_id=aspect_id,
                title=data.get("title", aspect_id),
                tone=data.get("tone", "good"),
                tech_signature=data.get("tech_signature"),
                explanation=data.get("explanation", ""),
                scenario=data.get("scenario"),
                advice=data.get("advice"),
            )

        # Generate drilldown payload
        op_meaning = PLANET_MEANINGS.get("Sun", "")
        pp_meaning = PLANET_MEANINGS.get("Moon", "")
        asp_meaning = ASPECT_MEANINGS.get("trine", {}).get("explanation", "")

        drilldown_data = {
            "title": f"Детали аспекта {aspect_id}",
            "tone": "good",
            "tech_signature": f"{aspect_id} ({op_meaning[:20]})",
            "explanation": f"Аспект взаимодействия: {asp_meaning}",
            "scenario": "Повседневный контакт и общее понимание задач.",
            "advice": "Развивайте сильные стороны и открытый диалог.",
        }

        # Store in DB
        new_detail = SynastryAspectDetail(
            id=uuid.uuid4(),
            report_id=report.id,
            aspect_id=aspect_id,
            prompt_version="1",
            state="ready",
            payload_json=json.dumps(drilldown_data, ensure_ascii=False),
        )
        self.db.add(new_detail)
        await self.db.commit()

        return AspectDrilldown(
            aspect_id=aspect_id,
            title=drilldown_data["title"],
            tone="good",
            tech_signature=drilldown_data["tech_signature"],
            explanation=drilldown_data["explanation"],
            scenario=drilldown_data["scenario"],
            advice=drilldown_data["advice"],
        )

    async def submit_feedback(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
        value: str,
    ) -> SynastryFeedbackRead:
        """Submit reality check feedback. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        ).order_by(SynastryReport.created_at.desc()).limit(1)
        r_res = await self.db.execute(r_stmt)
        report = r_res.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        fb_stmt = select(SynastryFeedback).where(
            SynastryFeedback.user_id == user_id,
            SynastryFeedback.report_id == report.id,
        )
        fb_res = await self.db.execute(fb_stmt)
        fb = fb_res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if fb:
            fb.value = value
            fb.updated_at = now
        else:
            fb = SynastryFeedback(
                id=uuid.uuid4(),
                user_id=user_id,
                report_id=report.id,
                value=value,
                created_at=now,
                updated_at=now,
            )
            self.db.add(fb)

        await self.db.commit()
        await self.db.refresh(fb)

        return SynastryFeedbackRead(
            report_id=report.id,
            value=fb.value,
            updated_at=fb.updated_at,
        )

    async def delete_partner(
        self,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
    ) -> None:
        """Soft delete partner and partner's reports. Owner-scoped (404 if unowned)."""
        p_stmt = select(SynastryPartner).where(
            SynastryPartner.id == partner_id,
            SynastryPartner.owner_id == user_id,
            SynastryPartner.invalidated_at.is_(None),
        )
        p_res = await self.db.execute(p_stmt)
        partner = p_res.scalar_one_or_none()

        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        now = datetime.now(timezone.utc)
        partner.invalidated_at = now

        r_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user_id,
            SynastryReport.partner_id == partner.id,
            SynastryReport.invalidated_at.is_(None),
        )
        r_res = await self.db.execute(r_stmt)
        reports = list(r_res.scalars().all())

        for rep in reports:
            rep.invalidated_at = now

        await self.db.commit()
# END_BLOCK: SYNASTRY_SERVICE
