# ############################################################################
# AI_HEADER: MODULE_API_SYNASTRY
# ROLE: HTTP API routes for synastry feature (/api/synastry/capabilities, /quota, /, /partners, /{partner_id}, etc.)
# DEPENDENCIES: fastapi, sqlalchemy, app.core.dependencies, app.db.models, app.schemas.synastry
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-API-SYNASTRY
# purpose: HTTP surface for synastry management and reports.
# owns:
#   - apps/api/app/api/synastry.py
# inputs:
#   - user_id from require_session
#   - DB session
# outputs:
#   - APIRouter with synastry endpoints
# dependencies:
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
#   - M-SCHEMAS-SYNASTRY
# side_effects: creates partner records, updates feedback, invalidates partners
# emitted_logs: none
# failure_policy: standard HTTP exceptions (400, 401, 404, 409, 500)
# END_MODULE_CONTRACT: M-API-SYNASTRY

# START_MODULE_MAP: M-API-SYNASTRY
# public_entrypoints:
#   - router
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_synastry_api.py
# END_MODULE_MAP: M-API-SYNASTRY

from __future__ import annotations

import asyncio
import json

from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.core.logging import log_event
from app.db.models import (
    HoraryCredit,
    SynastryAspectDetail,
    SynastryFeedback,
    SynastryPartner,
    SynastryReport,
    User,
)
from app.db.session import SessionLocal, get_session
from app.schemas.horary import HoraryQuotaRead
from app.schemas.synastry import (
    AspectDrilldown,
    PartnerCreate,
    SynastryAspect,
    SynastryCapabilitiesRead,
    SynastryFeedbackRead,
    SynastryFeedbackWrite,
    SynastryGenerationRead,
    SynastryPartnerItem,
    SynastryListRead,
    SynastryReport as SynastryReportSchema,
    SynastrySphere,
)
from app.services.synastry_service import SynastryService

router = APIRouter(prefix="/api/synastry", tags=["synastry"])


# STATIC ROUTES FIRST!

@router.get("/capabilities", response_model=SynastryCapabilitiesRead)
async def get_synastry_capabilities(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryCapabilitiesRead:
    """Return user capabilities and partner counts for synastry."""
    stmt = select(SynastryPartner).where(
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    result = await db.execute(stmt)
    partners = list(result.scalars().all())

    # Get credit balance
    c_stmt = select(HoraryCredit).where(HoraryCredit.user_id == user.id)
    c_result = await db.execute(c_stmt)
    credits_list = list(c_result.scalars().all())
    balance = sum(c.amount - c.used_amount for c in credits_list if c.amount > c.used_amount)

    return SynastryCapabilitiesRead(
        can_calculate=True,
        active_partner_count=len(partners),
        max_partners=20,
        has_unlocked_access=True,
        credit_balance=balance,
    )


@router.get("/quota", response_model=HoraryQuotaRead)
async def get_synastry_quota(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> HoraryQuotaRead:
    """Return shared credit balance / quota for synastry."""
    c_stmt = select(HoraryCredit).where(HoraryCredit.user_id == user.id)
    c_result = await db.execute(c_stmt)
    credits_list = list(c_result.scalars().all())

    weekly = [c for c in credits_list if c.source == "subscription_weekly_free"]
    weekly_avail = any(c.amount > c.used_amount for c in weekly)
    bonus = sum(c.amount - c.used_amount for c in credits_list if c.source in ("referral_bonus", "gift"))
    paid = sum(c.amount - c.used_amount for c in credits_list if c.source in ("paid", "adjustment"))

    return HoraryQuotaRead(
        weeklyFreeAvailable=weekly_avail,
        weeklyFreeExpiresAt=weekly[0].expires_at.isoformat() if weekly and weekly[0].expires_at else None,
        nextWeeklyFreeAt=None,
        bonusCredits=max(0, bonus),
        paidCredits=max(0, paid),
        canPurchase=True,
    )


@router.get("", response_model=SynastryListRead)
async def list_synastry_partners(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryListRead:
    """List active partners for current user."""
    stmt = select(SynastryPartner).where(
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    ).order_by(SynastryPartner.created_at.desc())
    result = await db.execute(stmt)
    partners = list(result.scalars().all())

    items: list[SynastryPartnerItem] = []
    for p in partners:
        # Get latest report if exists
        rep_stmt = select(SynastryReport).where(
            SynastryReport.owner_id == user.id,
            SynastryReport.partner_id == p.id,
            SynastryReport.invalidated_at.is_(None),
        ).order_by(SynastryReport.created_at.desc()).limit(1)
        rep_res = await db.execute(rep_stmt)
        report = rep_res.scalar_one_or_none()

        score = None
        status_val = None
        summary_val = None

        counters_val = None
        report_state_val = report.state if report else None

        if report and report.deterministic_payload_json:
            try:
                det = json.loads(report.deterministic_payload_json)
                score = det.get("score")
                status_val = det.get("status")
                counters_val = det.get("counters")
            except Exception:
                pass

        if report and report.narrative_payload_json:
            try:
                nar = json.loads(report.narrative_payload_json)
                summary_val = nar.get("summary")
            except Exception:
                pass

        items.append(
            SynastryPartnerItem(
                id=p.id,
                name=p.name,
                relation_type=p.relation_type,
                birth_date=p.birth_date,
                precision=p.precision,
                score=score,
                status=status_val, # type: ignore[arg-type]
                summary=summary_val,
                counters=counters_val,
                report_state=report_state_val,
                created_at=p.created_at,
            )
        )

    return SynastryListRead(partners=items)


async def _run_synastry_pipeline_task(report_id: uuid.UUID) -> None:
    try:
        async with SessionLocal() as db:
            service = SynastryService(db)
            await service.run_report_pipeline(report_id)
    except Exception as exc:
        log_event(
            "system.error",
            level="error",
            msg=f"[Synastry] Background calculation failed for report {report_id}: {type(exc).__name__}",
            payload={"report_id": str(report_id), "error_type": type(exc).__name__},
        )


@router.post("/partners", response_model=SynastryGenerationRead, status_code=status.HTTP_202_ACCEPTED)
async def create_synastry_partner(
    body: PartnerCreate,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryGenerationRead:
    """Add a new synastry partner, spend credit, and initiate background report calculation."""
    service = SynastryService(db)
    partner, report = await service.create_partner_and_report(user.id, body)

    # Launch background task ONLY after successful commit
    asyncio.create_task(_run_synastry_pipeline_task(report.id))

    return SynastryGenerationRead(
        report_id=report.id,
        partner_id=partner.id,
        state=report.state,  # type: ignore[arg-type]
        stage=report.stage,
        attempt_count=report.attempt_count,
    )


# DYNAMIC ROUTE ({partner_id}) BELOW STATIC ROUTES!

@router.get("/{partner_id}", response_model=SynastryReportSchema)
async def get_synastry_report(
    partner_id: uuid.UUID,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryReportSchema:
    """Get full synastry report for specified partner. Owner-scoped (404 if not found/unauthorized)."""
    p_stmt = select(SynastryPartner).where(
        SynastryPartner.id == partner_id,
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    p_res = await db.execute(p_stmt)
    partner = p_res.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    r_stmt = select(SynastryReport).where(
        SynastryReport.owner_id == user.id,
        SynastryReport.partner_id == partner.id,
        SynastryReport.invalidated_at.is_(None),
    ).order_by(SynastryReport.created_at.desc()).limit(1)
    r_res = await db.execute(r_stmt)
    report = r_res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Synastry report not found for partner",
        )

    # Parse payloads or provide defaults
    det = {}
    if report.deterministic_payload_json:
        try:
            det = json.loads(report.deterministic_payload_json)
        except Exception:
            det = {}

    nar = {}
    if report.narrative_payload_json:
        try:
            nar = json.loads(report.narrative_payload_json)
        except Exception:
            nar = {}

    aspects_list = []
    for a in det.get("aspects", []):
        aspects_list.append(
            SynastryAspect(
                id=a.get("id", "asp"),
                title=a.get("tech_signature", "Aspect"),
                tone=a.get("tone", "good"),
                score=a.get("score"),
                description=a.get("description"),
                tech_signature=a.get("tech_signature"),
            )
        )

    spheres_list = []
    for s in det.get("spheres", []):
        spheres_list.append(
            SynastrySphere(
                id=s.get("id", "sphere"),
                title=s.get("title", "Сфера"),
                score=s.get("score", 50),
                description=s.get("description"),
            )
        )

    # Get feedback if exists
    fb_stmt = select(SynastryFeedback).where(
        SynastryFeedback.user_id == user.id,
        SynastryFeedback.report_id == report.id,
    )
    fb_res = await db.execute(fb_stmt)
    fb = fb_res.scalar_one_or_none()

    return SynastryReportSchema(
        id=report.id,
        owner_id=user.id,
        partner_id=partner.id,
        partner_name=partner.name,
        relation_type=partner.relation_type,
        precision=partner.precision,
        score=det.get("score", 50),
        status=det.get("status", "mid"),
        verdict=nar.get("verdict", "Анализ совместимости пара"),
        summary=nar.get("summary", "Отчёт формируется."),
        hero_title=nar.get("hero_title"),
        hero_description=nar.get("hero_description"),
        counters=det.get("counters", {"good": 0, "mid": 0, "bad": 0}),
        aspects=aspects_list,
        house_overlays=nar.get("house_overlays", []),
        spheres=spheres_list,
        translations=nar.get("translations", []),
        user_feedback=fb.value if fb else None,
        created_at=report.created_at,
    )


@router.get("/{partner_id}/status", response_model=SynastryGenerationRead)
async def get_synastry_status(
    partner_id: uuid.UUID,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryGenerationRead:
    """Get report generation status. Owner-scoped (404 if not found/unauthorized)."""
    p_stmt = select(SynastryPartner).where(
        SynastryPartner.id == partner_id,
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    p_res = await db.execute(p_stmt)
    partner = p_res.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    r_stmt = select(SynastryReport).where(
        SynastryReport.owner_id == user.id,
        SynastryReport.partner_id == partner.id,
        SynastryReport.invalidated_at.is_(None),
    ).order_by(SynastryReport.created_at.desc()).limit(1)
    r_res = await db.execute(r_stmt)
    report = r_res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found for partner",
        )

    return SynastryGenerationRead(
        report_id=report.id,
        partner_id=partner.id,
        state=report.state, # type: ignore[arg-type]
        stage=report.stage,
        attempt_count=report.attempt_count,
        error_code=report.error_code,
        error_message=report.error_message,
    )


@router.get("/{partner_id}/aspect/{aspect_id}", response_model=AspectDrilldown)
async def get_aspect_drilldown(
    partner_id: uuid.UUID,
    aspect_id: str,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AspectDrilldown:
    """Get aspect drilldown interpretation. Owner-scoped (404 if not found/unauthorized)."""
    p_stmt = select(SynastryPartner).where(
        SynastryPartner.id == partner_id,
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    p_res = await db.execute(p_stmt)
    partner = p_res.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    r_stmt = select(SynastryReport).where(
        SynastryReport.owner_id == user.id,
        SynastryReport.partner_id == partner.id,
        SynastryReport.invalidated_at.is_(None),
    ).order_by(SynastryReport.created_at.desc()).limit(1)
    r_res = await db.execute(r_stmt)
    report = r_res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    a_stmt = select(SynastryAspectDetail).where(
        SynastryAspectDetail.report_id == report.id,
        SynastryAspectDetail.aspect_id == aspect_id,
    )
    a_res = await db.execute(a_stmt)
    detail = a_res.scalar_one_or_none()

    if not detail or not detail.payload_json:
        # Provide fallback drilldown
        return AspectDrilldown(
            aspect_id=aspect_id,
            title=aspect_id.replace("_", " ").title(),
            tone="good",
            tech_signature=aspect_id,
            explanation="Взаимодействие двух энергий в натальных картах.",
            scenario="Повседневный контакт двух личностей.",
            advice="Сохраняйте взаимное уважение и диалог.",
        )

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


@router.post("/{partner_id}/feedback", response_model=SynastryFeedbackRead)
async def submit_synastry_feedback(
    partner_id: uuid.UUID,
    body: SynastryFeedbackWrite,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SynastryFeedbackRead:
    """Submit reality check feedback for a synastry report. Owner-scoped (404 if not found)."""
    p_stmt = select(SynastryPartner).where(
        SynastryPartner.id == partner_id,
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    p_res = await db.execute(p_stmt)
    partner = p_res.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    r_stmt = select(SynastryReport).where(
        SynastryReport.owner_id == user.id,
        SynastryReport.partner_id == partner.id,
        SynastryReport.invalidated_at.is_(None),
    ).order_by(SynastryReport.created_at.desc()).limit(1)
    r_res = await db.execute(r_stmt)
    report = r_res.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    fb_stmt = select(SynastryFeedback).where(
        SynastryFeedback.user_id == user.id,
        SynastryFeedback.report_id == report.id,
    )
    fb_res = await db.execute(fb_stmt)
    fb = fb_res.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if fb:
        fb.value = body.value
        fb.updated_at = now
    else:
        fb = SynastryFeedback(
            id=uuid.uuid4(),
            user_id=user.id,
            report_id=report.id,
            value=body.value,
            created_at=now,
            updated_at=now,
        )
        db.add(fb)

    await db.commit()
    await db.refresh(fb)

    return SynastryFeedbackRead(
        report_id=report.id,
        value=fb.value,
        updated_at=fb.updated_at,
    )


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_synastry_partner(
    partner_id: uuid.UUID,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Soft-delete / invalidate a partner. Owner-scoped (404 if not found)."""
    p_stmt = select(SynastryPartner).where(
        SynastryPartner.id == partner_id,
        SynastryPartner.owner_id == user.id,
        SynastryPartner.invalidated_at.is_(None),
    )
    p_res = await db.execute(p_stmt)
    partner = p_res.scalar_one_or_none()

    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found",
        )

    now = datetime.now(timezone.utc)
    partner.invalidated_at = now

    # Also invalidate reports
    r_stmt = select(SynastryReport).where(
        SynastryReport.owner_id == user.id,
        SynastryReport.partner_id == partner.id,
        SynastryReport.invalidated_at.is_(None),
    )
    r_res = await db.execute(r_stmt)
    reports = list(r_res.scalars().all())

    for rep in reports:
        rep.invalidated_at = now

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
