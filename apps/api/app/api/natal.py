# ############################################################################
# AI_HEADER: MODULE_API_NATAL
# ROLE: Natal reading endpoints — preview, generation, and report retrieval.
# DEPENDENCIES: fastapi, app.services.natal_service, app.services.natal_report_service
# GRACE_ANCHORS: [NATAL_PREVIEW, NATAL_GENERATE, NATAL_REPORT]
# WAVE: W-7.2, W-NATAL-FULL
# ############################################################################

# START_MODULE_CONTRACT: M-API-NATAL
# purpose: Expose natal reading endpoints.
#   GET /api/natal/preview — returns preview from cached NatalContext
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

# START_MODULE_MAP: M-API-NATAL
# public_entrypoints:
#   - get_natal_preview
#   - generate_natal_report
#   - get_natal_report_latest
#   - get_natal_report_by_id
#   - get_natal_report_section
# semantic_blocks:
#   - NATAL_PREVIEW: GET /api/natal/preview
#   - NATAL_GENERATE: POST /api/natal/generate
#   - NATAL_REPORT: GET /api/natal/report endpoints
# END_MODULE_MAP: M-API-NATAL

from app.core.logging import log_event, log_block
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


router = APIRouter()


# START_BLOCK: NATAL_PREVIEW

@router.get("/api/natal/preview", response_model=NatalPreviewRead)
async def get_natal_preview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalPreviewRead:
    # START_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_preview
    # purpose: Return natal preview from cached NatalContext.
    # inputs: db session, user_id from session
    # returns: NatalPreviewRead with highlights, spheres, planets, chapters
    # side_effects: reads from DB, may trigger sidecar call on cache miss
    # emitted_logs: natal.preview_succeeded, natal.preview_failed
    # error_behavior: 500 on unexpected errors
    # END_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_preview
    service = NatalService(db)
    try:
        return await service.get_preview(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        with log_block(slice="W-NATAL-FULL", module="M-API-NATAL", block="ROUTE_PREVIEW"):
            log_event(
                "natal.preview_failed",
                level="error",
                msg=f"Natal preview failed: {type(exc).__name__}",
                error={
                    "kind": type(exc).__name__,
                    "message": str(exc)[:200],
                }
            )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "NATAL_PREVIEW_FAILED",
                "message": "Не удалось построить натальную карту. Попробуй позже или проверь данные профиля.",
            },
        ) from exc


# END_BLOCK: NATAL_PREVIEW

# START_BLOCK: NATAL_GENERATE

@router.post("/api/natal/generate", response_model=NatalGenerateResponse)
async def generate_natal_report(
    request: NatalGenerateRequest = NatalGenerateRequest(),
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalGenerateResponse:
    # START_FUNCTION_CONTRACT: F-M-API-NATAL.generate_natal_report
    # purpose: Start or return full natal report generation (idempotent).
    # inputs: request (NatalGenerateRequest), db session, user_id from session
    # returns: NatalGenerateResponse with report_id, status, sections_available
    # side_effects: creates NatalReport rows, triggers LLM generation
    # emitted_logs: natal.report_generation_requested, natal.report_generation_succeeded, natal.report_generation_failed
    # error_behavior: 501 if FEATURE_DISABLED, 500 on generation failure
    # END_FUNCTION_CONTRACT: F-M-API-NATAL.generate_natal_report
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
        with log_block(slice="W-NATAL-FULL", module="M-API-NATAL", block="ROUTE_GENERATE"):
            log_event(
                "natal.report_generation_failed",
                level="error",
                msg=f"Natal report generation failed: {type(exc).__name__}",
                error={
                    "kind": type(exc).__name__,
                    "message": str(exc)[:200],
                }
            )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "NATAL_GENERATION_FAILED",
                "message": "Не удалось сгенерировать натальный отчёт. Попробуй позже.",
            },
        ) from exc


# END_BLOCK: NATAL_GENERATE

# START_BLOCK: NATAL_REPORT

@router.get("/api/natal/report", response_model=NatalReportRead)
async def get_natal_report_latest(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalReportRead:
    # START_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_latest
    # purpose: Get latest READY report for current user.
    # inputs: db session, user_id from session
    # returns: NatalReportRead with sections, meta, status
    # side_effects: reads from DB
    # emitted_logs: none
    # error_behavior: 501 if FEATURE_DISABLED, 404 if no READY report found
    # END_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_latest
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
    # START_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_by_id
    # purpose: Get specific natal report by report_id.
    # inputs: report_id (str), db session, user_id from session
    # returns: NatalReportRead with sections, meta, status
    # side_effects: reads from DB
    # emitted_logs: none
    # error_behavior: 501 if FEATURE_DISABLED, 404 if report not found
    # END_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_by_id
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
    # START_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_section
    # purpose: Get single section from a specific natal report.
    # inputs: report_id (str), section_id (str), db session, user_id from session
    # returns: NatalReportSectionRead with blocks for that section
    # side_effects: reads from DB
    # emitted_logs: none
    # error_behavior: 501 if FEATURE_DISABLED, 404 if report or section not found
    # END_FUNCTION_CONTRACT: F-M-API-NATAL.get_natal_report_section
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
# END_BLOCK: NATAL_REPORT
