#!/usr/bin/env python3
"""W1 ablation v2 — factor dump WITH DayDelta trigger sets (master v1.5 fixes).

Same deterministic wiring as dump_factors.py (sidecar transits -> normalize_day
-> DayDelta -> filter_day_scored_signals -> sidecar activation layer ->
ActivationLayerService.build -> build_factor_ledger -> normalize_factors),
plus per-day `delta_triggers`: the CORRECTED DayDelta contract data —
semantic keys (planet+aspect+target, same 4-part format as the ledger) of
signals annotated new_today / peak_today, so the harness can simulate the
fixed is_delta_trigger matching (prod matches bare planet names against full
factor_ids — dead code; W2 owns the prod-side fix).

Output: analysis/factor_dump_v2.json. Read-only DB, no LLM, no secrets.
Run: cd /opt/solarsage-astro/apps/api && .venv/bin/python \
  ../docs/work/2026-07-29_today-convergence-rewrite/analysis/dump_factors_v2.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/solarsage-astro/apps/api")
sys.path.insert(0, "/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")

import yaml  # noqa: E402
from sqlalchemy import and_, select  # noqa: E402

from app.clients.solarsage_client import get_solarsage_client  # noqa: E402
from app.db.models import NatalChartCache, User, UserProfile  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.day_factor_ledger import build_factor_ledger  # noqa: E402
from app.services.day_scoring_signals import filter_day_scored_signals  # noqa: E402
from app.services.natal_context_service import (  # noqa: E402
    CALCULATION_VERSION,
    ENGINE_VERSION,
    HOUSE_SYSTEM_DEFAULT,
    NatalContextService,
)
from app.services.normalization_service import NormalizationService  # noqa: E402
from app.services.today_focus_builder import normalize_factors  # noqa: E402

from dump_factors import act_sem_key, signal_sem_key, strict_product_spheres  # noqa: E402

REPO = Path("/opt/solarsage-astro")
OUT = REPO / "docs/work/2026-07-29_today-convergence-rewrite/analysis/factor_dump_v2.json"
CANON_PATH = REPO / "grace/canon/aspect_rules.v1.yml"
DATE_FROM = date(2026, 6, 1)
DATE_TO = date(2026, 8, 20)
OWNER_TG = "basil_ivanov"


def _g(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def main() -> None:
    t0 = time.monotonic()
    canon = yaml.safe_load(CANON_PATH.read_text())

    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_username == OWNER_TG))).scalar_one()
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        ).scalar_one()
        profile_hash = NatalContextService.compute_profile_hash(profile)
        cached = (
            await db.execute(
                select(NatalChartCache).where(
                    and_(
                        NatalChartCache.user_id == user.id,
                        NatalChartCache.profile_hash == profile_hash,
                        NatalChartCache.engine_version == ENGINE_VERSION,
                        NatalChartCache.calculation_version == CALCULATION_VERSION,
                        NatalChartCache.house_system == HOUSE_SYSTEM_DEFAULT,
                        NatalChartCache.invalidated_at.is_(None),
                    )
                )
            )
        ).scalar_one_or_none()
        if cached is None:
            raise RuntimeError("no active natal cache (read-only probe refuses to build)")
        natal = NatalContextService._deserialize_context(
            cached.normalized_context_json
        ).model_dump(by_alias=False)

    client = get_solarsage_client()
    norm = NormalizationService()
    transit_tz = profile.current_tz or profile.birth_tz or "UTC"
    user_tz = transit_tz
    house_system = natal.get("house_system", "PLACIDUS")
    current_location = None
    if (
        profile.current_lat is not None
        and profile.current_lon is not None
        and profile.current_tz is not None
    ):
        current_location = {
            "lat": float(profile.current_lat),
            "lon": float(profile.current_lon),
            "tz": profile.current_tz,
        }

    transits_cache: dict[str, dict] = {}
    signals_cache: dict[str, list] = {}

    async def transits_for(d: date) -> dict:
        if d.isoformat() not in transits_cache:
            transits_cache[d.isoformat()] = await client.get_transits(
                target_date=d.isoformat(), target_time="12:00", target_tz=transit_tz
            )
        return transits_cache[d.isoformat()]

    async def signals_for(d: date):
        if d.isoformat() not in signals_cache:
            signals_cache[d.isoformat()] = norm.normalize_day(natal, await transits_for(d))
        return signals_cache[d.isoformat()]

    days_out: list[dict] = []
    sidecar_failures = 0
    d = DATE_FROM
    while d <= DATE_TO:
        rec: dict = {"date": d.isoformat(), "factors": []}
        try:
            signals_raw = await signals_for(d)
            try:
                y_signals = await signals_for(d - timedelta(days=1))
            except Exception:
                y_signals = None
            signals = (
                DayDeltaService(y_signals, signals_raw).compute_deltas()
                if y_signals
                else signals_raw
            )
            day_signals = filter_day_scored_signals(signals)
            sig_orb = {}
            for s in day_signals:
                k = signal_sem_key(s)
                if k:
                    sig_orb.setdefault(k, _g(s, "orb"))

            # CORRECTED DayDelta contract: semantic identity of triggered signals
            trig_new, trig_peak = set(), set()
            for s in signals:
                dk = getattr(s, "delta_kind", None)
                if dk not in ("new_today", "peak_today"):
                    continue
                k = signal_sem_key(s)
                if not k:
                    continue
                (trig_new if dk == "new_today" else trig_peak).add(k)
            rec["delta_triggers"] = {
                "new_today": sorted(trig_new),
                "peak": sorted(trig_peak),
                "raw_planet_names_new_today": sorted({
                    strip_prefix(getattr(s, "planet", ""))
                    for s in signals
                    if getattr(s, "delta_kind", None) == "new_today"
                }),
            }

            sidecar_layer = None
            try:
                sidecar_layer = await client.get_activation_layer(
                    birth_date=profile.birthday.isoformat(),
                    birth_time=profile.birth_time.strftime("%H:%M") if profile.birth_time else "12:00",
                    birth_lat=float(profile.birth_lat),
                    birth_lon=float(profile.birth_lon),
                    birth_tz=profile.birth_tz,
                    target_date=d.isoformat(),
                    target_time="12:00",
                    target_tz=transit_tz,
                    house_system=house_system,
                    current_location=current_location,
                )
            except Exception:
                sidecar_failures += 1

            al = ActivationLayerService().build(
                natal_context=natal,
                transits=await transits_for(d),
                day_signals=day_signals,
                target_date=d,
                target_time="12:00",
                target_tz=transit_tz,
                house_system=house_system,
                sidecar_activation_layer=sidecar_layer,
            )
            ledger = build_factor_ledger(day_signals, al.activations if al else [])
            ledger_by_id = {f.factor_id: f for f in ledger.factors}

            acts_by_sem: dict[str, list] = {}
            acts_by_id: dict[str, object] = {}
            for act in al.activations if al else []:
                act_id = _g(act, "id") or _g(act, "activation_id")
                if act_id:
                    acts_by_id[str(act_id)] = act
                sem = act_sem_key(act)
                if sem:
                    acts_by_sem.setdefault(sem, []).append(act)

            today_factors = normalize_factors(
                ledger=ledger,
                activation_layer=al,
                day_delta=None,  # roles via exact_at only; triggers simulated in harness
                target_date=d,
                tz_info=user_tz,
            )

            for f in today_factors:
                lf = ledger_by_id.get(f.factor_id)
                sem_key = lf.semantic_key if lf else f.factor_id
                orb, orb_source = None, "none"
                matched = acts_by_sem.get(sem_key) or []
                if not matched:
                    matched = [a for aid, a in acts_by_id.items() if aid and aid in f.factor_id]
                if matched:
                    orb = _g(matched[0], "orb")
                    if orb is not None:
                        orb_source = "activation"
                if orb is None and sig_orb.get(sem_key) is not None:
                    orb = sig_orb[sem_key]
                    orb_source = "day_signal"
                rec["factors"].append(
                    {
                        "semantic_key": sem_key,
                        "factor_id": f.factor_id,
                        "source": lf.source if lf else None,
                        "temporal_role": f.temporal_role,
                        "technique": f.technique,
                        "technique_family": f.technique_family,
                        "source_planet": f.source_key,
                        "aspect_type": f.aspect_type,
                        "orb": orb,
                        "orb_source": orb_source,
                        "strength": f.strength,
                        "polarity": f.polarity,
                        "target_type": f.target_type,
                        "target_key": f.target_key,
                        "theme_keys": list(f.theme_keys or ()),
                        "spheres": strict_product_spheres(
                            lf.technical_spheres if lf else [], f.source_key, f.target_key
                        ),
                        "exact_at": f.exact_at.isoformat() if f.exact_at else None,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        days_out.append(rec)
        d += timedelta(days=1)

    payload = {
        "meta": {
            "owner_tg": OWNER_TG,
            "range": [DATE_FROM.isoformat(), DATE_TO.isoformat()],
            "sidecar_failures": sidecar_failures,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "delta_contract": "corrected semantic keys (new_today/peak); raw planet names kept for reference",
            "canon_aspect_weights": canon.get("aspect_weights"),
            "canon_orb_profile_default": canon.get("orb_profile_default"),
        },
        "days": days_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False))
    ok = [x for x in days_out if "error" not in x]
    n_trig = sum(len(x["delta_triggers"]["new_today"]) + len(x["delta_triggers"]["peak"]) for x in ok)
    print(
        f"[done] days={len(ok)}/{len(days_out)} factors={sum(len(x['factors']) for x in ok)} "
        f"trigger_sem_keys_total={n_trig} sidecar_failures={sidecar_failures} "
        f"elapsed={time.monotonic()-t0:.0f}s -> {OUT}"
    )


if __name__ == "__main__":
    asyncio.run(main())
