# AI_HEADER: MODULE_API_PROMO
# ROLE: Session-authenticated HTTP surface for /api/promo/preview and /api/promo/redeem.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.promo_campaign_service, app.services.promo_rate_limiter
# GRACE_ANCHORS: [ROUTE_PROMO_PREVIEW, ROUTE_PROMO_REDEEM]
# WAVE: W-NAMED-PROMO-CAMPAIGN

# START_MODULE_CONTRACT: M-API-PROMO
# purpose: Expose POST /api/promo/preview and POST /api/promo/redeem endpoints with session auth, per-user rate limiting, safe 400 validation boundary, Cache-Control: no-store headers, and domain error mapping.
# owns:
#   - apps/api/app/api/promo.py
# inputs:
#   - PromoCodeRequest (token as SecretStr)
#   - require_session (authenticated User)
#   - DB session
# outputs:
#   - APIRouter with promo endpoints
# dependencies:
#   - M-PROMO-CAMPAIGN-SERVICE
#   - M-PROMO-RATE-LIMITER
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects: calls promo_rate_limiter, PromoCampaignService preview and redeem
# emitted_logs: promo.redemption_rejected (for rate-limited redeem)
# failure_policy: maps domain errors to 400/409/410/429 HTTP status codes with safe error codes; malformed requests map to safe 400 INVALID_CODE
# END_MODULE_CONTRACT: M-API-PROMO

# START_MODULE_MAP: M-API-PROMO
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_WRAPPER: SafePromoRoute APIRoute subclass for safe 400 validation handling and Cache-Control headers
#   - ROUTE_PROMO_PREVIEW: POST /api/promo/preview route
#   - ROUTE_PROMO_REDEEM: POST /api/promo/redeem route
# owned_tests:
#   - apps/api/tests/test_promo_api.py
#   - apps/api/tests/test_promo_rate_limiter.py
#   - apps/api/tests/test_public_surface_security.py
# END_MODULE_MAP: M-API-PROMO

from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.core.logging import log_block, log_event
from app.db.models import User
from app.db.session import get_session
from app.schemas.promo import (
    PromoCodeRequest,
    PromoGrantSummary,
    PromoOffer,
    PromoPreviewResponse,
    PromoRedeemResponse,
)
from app.services.promo_campaign_service import (
    PromoCampaignService,
    PromoDomainError,
    PromoErrorCode,
)
from app.services.promo_rate_limiter import promo_rate_limiter

DOMAIN_ERROR_STATUS: dict[PromoErrorCode, int] = {
    "INVALID_CODE": status.HTTP_400_BAD_REQUEST,
    "CAMPAIGN_EXPIRED": status.HTTP_410_GONE,
    "CAMPAIGN_FULL": status.HTTP_409_CONFLICT,
    "ALREADY_REDEEMED": status.HTTP_409_CONFLICT,
    "PROFILE_INCOMPLETE": status.HTTP_409_CONFLICT,
    "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
}


# START_BLOCK: ROUTE_WRAPPER
class SafePromoRoute(APIRoute):
    """Custom APIRoute to enforce safe validation error boundary, Retry-After headers, and Cache-Control: no-store headers."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                res = await original_route_handler(request)
                res.headers["Cache-Control"] = "no-store"
                return res
            except RequestValidationError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": {
                            "code": "INVALID_CODE",
                            "message": "Неверный промокод",
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )
            except HTTPException as exc:
                if isinstance(exc.detail, dict):
                    content = {"detail": exc.detail}
                else:
                    content = {
                        "detail": {
                            "code": "INVALID_CODE",
                            "message": str(exc.detail),
                        }
                    }
                headers = {"Cache-Control": "no-store"}
                if exc.headers:
                    headers.update(exc.headers)
                return JSONResponse(
                    status_code=exc.status_code,
                    content=content,
                    headers=headers,
                )

        return custom_route_handler
# END_BLOCK: ROUTE_WRAPPER


router = APIRouter(prefix="/api/promo", tags=["promo"], route_class=SafePromoRoute)


# START_BLOCK: ROUTE_PROMO_PREVIEW
@router.post("/preview", response_model=PromoPreviewResponse)
async def preview_promo(
    body: PromoCodeRequest,
    user: User = Depends(require_session),
    db: AsyncSession = Depends(get_session),
) -> PromoPreviewResponse:
    # START_FUNCTION_CONTRACT: F-M-API-PROMO.preview_promo
    # purpose: Authenticated endpoint to preview a promo campaign offer and check profile readiness.
    # inputs: body (PromoCodeRequest), user (User from require_session), db (AsyncSession)
    # returns: PromoPreviewResponse
    # side_effects: calls promo_rate_limiter, PromoCampaignService.preview
    # emitted_logs: none
    # error_behavior: maps domain/rate limit errors to 400/409/410/429 status codes
    # END_FUNCTION_CONTRACT: F-M-API-PROMO.preview_promo

    # Check per-user rate limit after session auth, before DB/hash lookup
    rate_res = promo_rate_limiter.check_and_record(user.id)
    if not rate_res.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(rate_res.retry_after_seconds)},
            detail={
                "code": "RATE_LIMITED",
                "message": "Слишком много попыток ввода промокода. Попробуйте позже.",
            },
        )

    service = PromoCampaignService(db)
    try:
        preview_data = await service.preview(
            user.id,
            body.token.get_secret_value(),
        )
    except PromoDomainError as err:
        status_code = DOMAIN_ERROR_STATUS.get(err.code, status.HTTP_400_BAD_REQUEST)
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": err.code,
                "message": err.safe_message,
            },
        )

    return PromoPreviewResponse(
        offer=PromoOffer(
            display_name=preview_data.offer.display_name,
            access_days=preview_data.offer.access_days,
            bonus_credits=preview_data.offer.bonus_credits,
            unlock_natal=preview_data.offer.unlock_natal,
        ),
        profile_complete=preview_data.profile_complete,
    )
# END_BLOCK: ROUTE_PROMO_PREVIEW


# START_BLOCK: ROUTE_PROMO_REDEEM
@router.post("/redeem", response_model=PromoRedeemResponse)
async def redeem_promo(
    body: PromoCodeRequest,
    user: User = Depends(require_session),
    db: AsyncSession = Depends(get_session),
) -> PromoRedeemResponse:
    # START_FUNCTION_CONTRACT: F-M-API-PROMO.redeem_promo
    # purpose: Authenticated endpoint to redeem a promo campaign and issue access/credit/natal grants.
    # inputs: body (PromoCodeRequest), user (User from require_session), db (AsyncSession)
    # returns: PromoRedeemResponse
    # side_effects: calls promo_rate_limiter, PromoCampaignService.redeem
    # emitted_logs: promo.redemption_rejected when rate limited
    # error_behavior: maps domain/rate limit errors to 400/409/410/429 status codes
    # END_FUNCTION_CONTRACT: F-M-API-PROMO.redeem_promo

    # Check per-user rate limit after session auth, before DB/hash lookup
    rate_res = promo_rate_limiter.check_and_record(user.id)
    if not rate_res.allowed:
        try:
            with log_block(slice="W-PROMO-CAMPAIGN", module="M-API-PROMO", block="REDEEM"):
                log_event(
                    "promo.redemption_rejected",
                    level="info",
                    msg="Promo redemption rejected due to rate limiting",
                    payload={"error_code": "RATE_LIMITED"},
                )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(rate_res.retry_after_seconds)},
            detail={
                "code": "RATE_LIMITED",
                "message": "Слишком много попыток ввода промокода. Попробуйте позже.",
            },
        )

    service = PromoCampaignService(db)
    try:
        redeem_data = await service.redeem(
            user.id,
            body.token.get_secret_value(),
        )
    except PromoDomainError as err:
        status_code = DOMAIN_ERROR_STATUS.get(err.code, status.HTTP_400_BAD_REQUEST)
        raise HTTPException(
            status_code=status_code,
            detail={
                "code": err.code,
                "message": err.safe_message,
            },
        )

    return PromoRedeemResponse(
        status="redeemed",
        offer=PromoOffer(
            display_name=redeem_data.offer.display_name,
            access_days=redeem_data.offer.access_days,
            bonus_credits=redeem_data.offer.bonus_credits,
            unlock_natal=redeem_data.offer.unlock_natal,
        ),
        grants=PromoGrantSummary(
            access_starts_at=redeem_data.grants.access_starts_at,
            access_until=redeem_data.grants.access_until,
            bonus_credits=redeem_data.grants.bonus_credits,
            bonus_credits_expires_at=redeem_data.grants.bonus_credits_expires_at,
            natal_unlocked=redeem_data.grants.natal_unlocked,
            natal_already_owned=redeem_data.grants.natal_already_owned,
        ),
    )
# END_BLOCK: ROUTE_PROMO_REDEEM
