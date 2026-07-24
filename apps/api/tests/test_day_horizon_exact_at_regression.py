# ############################################################################
# AI_HEADER: TEST_DAY_HORIZON_EXACT_AT_REGRESSION — regression test for horizon exact_at selection gate.
# ROLE: Proves that date 2026-07-24 for profile 1990-01-01 12:00 Europe/Moscow returns 200 OK without 500 error,
#       and that selection=None pipeline calls return honest unavailable result without triggering preflight error.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-HORIZON-EXACT-AT-REGRESSION
# purpose: Prove regression fix for date-dependent medium_peak_missing 500 error.
# owns:
#   - apps/api/tests/test_day_horizon_exact_at_regression.py
# inputs: db_session, synthetic/real profile data
# outputs: pytest assertions
# END_MODULE_CONTRACT: M-TEST-DAY-HORIZON-EXACT-AT-REGRESSION

from datetime import UTC, date, time
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState
from app.schemas.activation import ActivationLayer
from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.natal import NatalContextData
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.today_horizons import TodayV2ProductSphereKey
from app.services.access_service import AccessService
from app.services.horizon_pipeline_service import HorizonPipelineService
from app.services.horizon_selection_service import HorizonSelectionResult
from app.services.profile_service import get_or_create_user, read_profile
from app.services.telegram_auth import TelegramUser
from app.services.today_selection_context import TodaySelectionContext, TodaySelectionSource
from app.services.today_service import TodayService


@pytest.mark.asyncio
async def test_day_horizon_exact_at_repro_date_2026_07_24(db_session: AsyncSession) -> None:
    # Setup profile 1990-01-01 12:00 Europe/Moscow
    tg = TelegramUser(id=19900101, username="repro_user", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    profile = await read_profile(db_session, user.id)
    profile.birthday = date(1990, 1, 1)
    profile.birth_time = time(12, 0)
    profile.birth_city = "Moscow"
    profile.birth_lat = Decimal("55.7558")
    profile.birth_lon = Decimal("37.6173")
    profile.birth_tz = "Europe/Moscow"
    profile.gender = "female"
    profile.is_onboarded = True
    await db_session.commit()

    access_svc = AccessService(db_session)
    real_access = await access_svc.can_access_day(user.id, date(2026, 7, 24))

    today_svc = TodayService(db_session)
    selection_ctx = TodaySelectionContext(force_v2=True, source=TodaySelectionSource.LOCAL_DEV_PREVIEW)

    # Must complete without throwing 500 HorizonGuidanceError: medium_peak_missing
    payload = await today_svc.get_today_payload(
        user_id=user.id,
        target_date=date(2026, 7, 24),
        access_state=real_access,
        selection_context=selection_ctx,
    )

    assert payload is not None
    assert payload.v2 is not None
    assert payload.v2.audit.horizon_pipeline.status in ("built", "unavailable")


def test_pipeline_honest_unavailable_when_selection_none() -> None:
    # Mock selection service that returns selection=None
    class MockSelectionNone:
        def select(self, *, activation_layer: object, scoring_result: object) -> HorizonSelectionResult:
            from app.schemas.horizon_selection import HorizonSelectionDiagnostics
            diag = HorizonSelectionDiagnostics(
                input_count=1,
                active_count=1,
                classified_count=1,
                candidate_count=2,
                per_horizon_pre_bound_counts={"long": 1, "medium": 0, "fast": 1},
                per_horizon_post_bound_counts={"long": 1, "medium": 0, "fast": 1},
                combinations_evaluated=0,
                excluded_counts_by_reason={"no_exact_hit_in_window": 1},
            )
            return HorizonSelectionResult(
                selection=None,
                reason="missing_medium",
                diagnostics=diag,
                warnings=["no_exact_hit_in_window"],
            )

    pipeline = HorizonPipelineService(selection_service=MockSelectionNone())  # type: ignore[arg-type]

    # Create dummy layer, scoring, natal, verdicts
    from ._horizon_selection_testkit import build_activation, build_layer, build_scoring
    act = build_activation(id="act1")
    layer = build_layer([act])
    scoring = build_scoring([act], {"act1": ("work_status_achievement", 1.0)})
    from .test_horizon_guidance_service import build_structure_natal
    natal = build_structure_natal()
    verdicts: dict[TodayV2ProductSphereKey, HorizonSphereVerdict] = {}

    result = pipeline.build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        sphere_verdicts=verdicts,
    )

    assert result.status == "unavailable"
    assert result.horizons is None
    assert result.selection_reason == "missing_medium"
