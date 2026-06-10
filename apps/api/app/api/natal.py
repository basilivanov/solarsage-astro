# ############################################################################
# AI_HEADER: MODULE_API_NATAL
# ROLE: Natal reading endpoints — preview, generation, and report retrieval.
# DEPENDENCIES: fastapi, app.services.natal_service, app.services.natal_report_service
# GRACE_ANCHORS: [NATAL_OVERVIEW, NATAL_SECTION, NATAL_GENERATE, NATAL_REPORT]
# WAVE: W-7.2, W-NATAL-FULL
# ############################################################################

# START_MODULE_CONTRACT: M-API-NATAL
# purpose: Expose natal reading endpoints.
#   GET /api/natal/overview — returns overview + section list (legacy)
#   GET /api/natal/preview — returns preview from cached NatalContext
#   GET /api/natal/section/{section_id} — returns section with blocks (legacy)
#   POST /api/natal/generate — starts full report generation
#   GET /api/natal/report — returns latest READY report
#   GET /api/natal/report/{report_id} — returns specific report
#   GET /api/natal/report/{report_id}/section/{section_id} — returns single section
# owns:
#   - apps/api/app/api/natal.py
# inputs:
#   - user_id from session (via require_session / current_user_id)
#   - section_id, report_id path parameters
# outputs:
#   - NatalPreviewRead, NatalGenerateResponse, NatalReportRead, NatalReportSectionRead
# dependencies:
#   - M-NATAL-SERVICE
#   - M-NATAL-REPORT-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - POST /api/natal/generate may trigger LLM calls and DB writes
# invariants:
#   - requires authenticated session
#   - returns 404 for non-existent section/report
#   - generate is idempotent
# failure_policy:
#   - 401 if not authenticated
#   - 404 if section/report not found
#   - 409 if profile incomplete
#   - 502 if sidecar unavailable
# non_goals:
#   - no payment integration yet
# END_MODULE_CONTRACT: M-API-NATAL

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id, require_session
from app.core.config import settings
from app.db.session import get_session
from app.schemas.natal import (
    NatalGenerateRequest,
    NatalGenerateResponse,
    NatalPreviewRead,
    NatalReportRead,
    NatalReportSectionRead,
)
from app.services.natal_service import NatalService
from app.services.natal_report_service import NatalReportService

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Preview ───────────────────────────────────────────────────────

@router.get("/api/natal/overview")
async def get_natal_overview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    service = NatalService(db)
    reading = await service.get_natal_reading(user_id)

    return {
        "meta": reading.meta.model_dump(by_alias=True),
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "iconName": s.icon_name,
            }
            for s in reading.sections
        ],
    }


@router.get("/api/natal/preview", response_model=NatalPreviewRead)
async def get_natal_preview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalPreviewRead:
    service = NatalService(db)
    try:
        return await service.get_preview(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Natal preview failed for user {user_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "NATAL_PREVIEW_FAILED",
                "message": "Не удалось построить натальную карту. Попробуй позже или проверь данные профиля.",
            },
        ) from exc


@router.get("/api/natal/section/{section_id}")
async def get_natal_section(
    section_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    service = NatalService(db)
    reading = await service.get_natal_reading(user_id)

    section = next((s for s in reading.sections if s.id == section_id), None)

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return section.model_dump(by_alias=True)


# ── Full report generation ────────────────────────────────────────

@router.post("/api/natal/generate", response_model=NatalGenerateResponse)
async def generate_natal_report(
    request: NatalGenerateRequest = NatalGenerateRequest(),
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalGenerateResponse:
    """Start or return full natal report generation.

    Idempotent: returns existing READY/GENERATING report unless force_regenerate=True.
    Wave 4 feature — gated by NATAL_REPORT_ENABLED flag.
    """
    if not settings.natal_report_enabled:
        raise HTTPException(
            status_code=501,
            detail={"code": "FEATURE_DISABLED", "message": "Генерация натального отчёта пока недоступна."},
        )
    service = NatalReportService(db)
    try:
        return await service.generate_report(user_id, force_regenerate=request.force_regenerate)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Natal report generation failed for user {user_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "NATAL_GENERATION_FAILED",
                "message": "Не удалось сгенерировать натальный отчёт. Попробуй позже.",
            },
        ) from exc


# ── Report retrieval ──────────────────────────────────────────────

@router.get("/api/natal/report", response_model=NatalReportRead)
async def get_natal_report_latest(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalReportRead:
    """Get latest READY report for current user.
    Wave 4 feature — gated by NATAL_REPORT_ENABLED flag.
    """
    if not settings.natal_report_enabled:
        raise HTTPException(
            status_code=501,
            detail={"code": "FEATURE_DISABLED", "message": "Генерация натального отчёта пока недоступна."},
        )
    service = NatalReportService(db)
    return await service.get_report(user_id)


@router.get("/api/natal/report/{report_id}", response_model=NatalReportRead)
async def get_natal_report_by_id(
    report_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalReportRead:
    """Get specific report by id.
    Wave 4 feature — gated by NATAL_REPORT_ENABLED flag.
    """
    if not settings.natal_report_enabled:
        raise HTTPException(
            status_code=501,
            detail={"code": "FEATURE_DISABLED", "message": "Генерация натального отчёта пока недоступна."},
        )
    service = NatalReportService(db)
    return await service.get_report(user_id, report_id)


@router.get("/api/natal/report/{report_id}/section/{section_id}", response_model=NatalReportSectionRead)
async def get_natal_report_section(
    report_id: str,
    section_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalReportSectionRead:
    """Get single section from a report.
    Wave 4 feature — gated by NATAL_REPORT_ENABLED flag.
    """
    if not settings.natal_report_enabled:
        raise HTTPException(
            status_code=501,
            detail={"code": "FEATURE_DISABLED", "message": "Генерация натального отчёта пока недоступна."},
        )
    service = NatalReportService(db)
    return await service.get_report_section(user_id, report_id, section_id)
