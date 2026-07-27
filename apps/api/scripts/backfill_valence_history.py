# ############################################################################
# AI_HEADER: SCRIPT_BACKFILL_VALENCE_HISTORY — rebuild day_score_history in valence scale
# ROLE: One-off migration tool (W2-VALENCE) for the personal baseline scale cutover.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPT-BACKFILL-VALENCE-HISTORY
# purpose: Recompute support/tension for recent days with the day-valence engine
#   (ledger + signed formula) and upsert day_score_history, replacing legacy
#   scoring-2.0-scale rows so the relative-status baseline is one consistent scale.
# owns:
#   - apps/api/scripts/backfill_valence_history.py
# inputs: --tg-id (telegram id), --days N (default 14, ending today)
# outputs: upserted day_score_history rows (valence scale), printed table
# dependencies: today pipeline services (natal context, sidecar, normalization,
#   activation layer), day_factor_ledger, day_valence_service
# side_effects: sidecar HTTP calls (transits + activation layer), DB delete+insert
# emitted_logs: none (stdout prints)
# failure_policy: per-day failure is printed and skipped, script continues
# END_MODULE_CONTRACT

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.db.models import DayScoreHistory, User, UserProfile
from app.clients.solarsage_client import get_solarsage_client
from app.services.natal_context_service import NatalContextService
from app.services.normalization_service import NormalizationService
from app.services.activation_layer_service import ActivationLayerService
from app.services.day_factor_ledger import build_factor_ledger
from app.services.day_valence_service import DayValenceService
from app.services.today_service import filter_day_scored_signals


async def backfill(user: User, days: int) -> None:
    async with SessionLocal() as db:
        profile = await db.get(UserProfile, user.id)
        assert profile is not None, "profile missing"
        assert profile.birthday is not None and profile.birth_tz is not None, "birth identity missing"

        context_service = NatalContextService(db)
        natal_context = await context_service.get_or_build_natal_context(user.id)
        natal_context_dict = natal_context.model_dump(by_alias=False)
        house_system = natal_context_dict.get("house_system", "PLACIDUS")

        current_location = None
        if (profile.current_lat is not None and profile.current_lon is not None
                and profile.current_tz is not None):
            current_location = {
                "lat": float(profile.current_lat),
                "lon": float(profile.current_lon),
                "tz": profile.current_tz,
            }

        client = get_solarsage_client()
        normalizer = NormalizationService()
        valence = DayValenceService()
        target_tz = profile.current_tz or profile.birth_tz or "UTC"
        today = date.today()

        await db.execute(delete(DayScoreHistory).where(DayScoreHistory.user_id == user.id))

        for offset in range(days - 1, -1, -1):
            target = today - timedelta(days=offset)
            try:
                transits = await client.get_transits(
                    target_date=target.isoformat(), target_time="12:00", target_tz=target_tz,
                )
                signals = normalizer.normalize_day(natal_context_dict, transits)
                day_signals = filter_day_scored_signals(signals)

                sidecar_layer = None
                try:
                    sidecar_layer = await client.get_activation_layer(
                        birth_date=profile.birthday.isoformat(),
                        birth_time=profile.birth_time.strftime("%H:%M") if profile.birth_time else "12:00",
                        birth_lat=float(profile.birth_lat),
                        birth_lon=float(profile.birth_lon),
                        birth_tz=profile.birth_tz,
                        target_date=target.isoformat(),
                        target_time="12:00",
                        target_tz=target_tz,
                        house_system=house_system,
                        current_location=current_location,
                    )
                except Exception:
                    sidecar_layer = None

                activation_layer = ActivationLayerService().build(
                    natal_context=natal_context_dict,
                    transits=transits,
                    day_signals=day_signals,
                    target_date=target,
                    target_time="12:00",
                    target_tz=target_tz,
                    house_system=house_system,
                    sidecar_activation_layer=sidecar_layer,
                )

                ledger = build_factor_ledger(day_signals=day_signals, activations=activation_layer.activations)
                _, breakdown, _ = valence.compute(ledger, sphere_scores_v2=None)

                db.add(DayScoreHistory(
                    user_id=user.id,
                    target_date=target,
                    support_score=float(breakdown.support_score),
                    tension_score=float(breakdown.tension_score),
                ))
                print(f"{target}: support={breakdown.support_score:.3f} tension={breakdown.tension_score:.3f}")
            except Exception as exc:  # noqa: BLE001
                print(f"{target}: FAILED {type(exc).__name__}: {exc}")

        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tg-id", type=int, required=True)
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    async def run() -> None:
        async with SessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_user_id == args.tg_id))).scalar_one()
        await backfill(user, args.days)

    asyncio.run(run())


if __name__ == "__main__":
    main()
