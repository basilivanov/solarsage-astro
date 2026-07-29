#!/usr/bin/env python3
"""W1 ablation v2 — birth-time strata factor dump WITH DayDelta triggers (master v1.5).

For the owner (basil_ivanov) and 2026-06-01..2026-08-20 recomputes the same
deterministic factor set as dump_factors.py, but at multiple CONTROL TIMES
inside each birth-time range (natal chart moves with birth time -> sidecar
get_natal + get_activation_layer recomputed per control time, exactly as prod
does for one time):

  buckets (local birth tz): night 00-06, morning 06-12, day 12-18, evening 18-24
    -> edges+middle: [start, mid, end-1min]  (3 points)
  unknown -> every 4h: 00,04,08,12,16,20     (6 points)
  shifted -> per bucket [start+1h, mid(reused), end-1h]  (fixture 9 resample)

DayDelta is skipped: it is provably content-neutral for the stored fields
(compute_deltas only annotates delta_kind/daily_salience/phase on signals;
ledger strength prefers sig.strength; roles come from activation exact_at;
the day_delta trigger path is dead code — see ablation_report.md §7).

Output: analysis/factor_dump_birthtime.json — merged per (stratum, day):
each distinct factor identity (semantic_key, polarity, spheres) stored once
with per-control-time presence / roles / orbs / strengths vectors.
Read-only DB, no LLM, no secrets. Run from apps/api venv:
  cd /opt/solarsage-astro/apps/api && .venv/bin/python \
    ../docs/work/2026-07-29_today-convergence-rewrite/analysis/dump_birthtime.py
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

from sqlalchemy import and_, select  # noqa: E402

from app.clients.solarsage_client import get_solarsage_client  # noqa: E402
from app.db.models import NatalChartCache, User, UserProfile  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.schemas.natal import SolarSageNatalResponse  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_factor_ledger import build_factor_ledger  # noqa: E402
from app.services.day_scoring_signals import filter_day_scored_signals  # noqa: E402
from app.services.natal_context_service import (  # noqa: E402
    CALCULATION_VERSION,
    ENGINE_VERSION,
    HOUSE_SYSTEM_DEFAULT,
    NatalContextService,
)
from app.services.normalization_service import NormalizationService  # noqa: E402
from app.services.scoring_service import ScoringService  # noqa: E402
from app.services.today_focus_builder import normalize_factors  # noqa: E402

from dump_factors import act_sem_key, signal_sem_key, strict_product_spheres  # noqa: E402

REPO = Path("/opt/solarsage-astro")
OUT = REPO / "docs/work/2026-07-29_today-convergence-rewrite/analysis/factor_dump_birthtime_v2.json"
DATE_FROM = date(2026, 6, 1)
DATE_TO = date(2026, 8, 20)
OWNER_TG = "basil_ivanov"

_args = sys.argv[1:]
if "--from" in _args:
    DATE_FROM = date.fromisoformat(_args[_args.index("--from") + 1])
if "--to" in _args:
    DATE_TO = date.fromisoformat(_args[_args.index("--to") + 1])
if "--out" in _args:
    OUT = Path(_args[_args.index("--out") + 1])

# Control times per stratum (local birth tz). "shifted" = fixture-9 resample.
STRATA: dict[str, list[str]] = {
    "night": ["00:00", "03:00", "05:59"],
    "morning": ["06:00", "09:00", "11:59"],
    "day": ["12:00", "15:00", "17:59"],
    "evening": ["18:00", "21:00", "23:59"],
    "unknown": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
}
SHIFTED: dict[str, list[str]] = {
    "night": ["01:00", "03:00", "05:00"],
    "morning": ["07:00", "09:00", "11:00"],
    "day": ["13:00", "15:00", "17:00"],
    "evening": ["19:00", "21:00", "23:00"],
}


def _g(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def main() -> None:
    t0 = time.monotonic()
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_username == OWNER_TG))).scalar_one()
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        ).scalar_one()

    client = get_solarsage_client()
    norm = NormalizationService()
    scoring = ScoringService()
    transit_tz = profile.current_tz or profile.birth_tz or "UTC"
    user_tz = transit_tz
    # Same as today_service / dump_factors.py: relocate only when all three are set.
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

    # ---- control times universe ----
    all_times = sorted({t for ts in STRATA.values() for t in ts} | {t for ts in SHIFTED.values() for t in ts})
    print(f"[setup] distinct control times: {len(all_times)}: {all_times}")

    # ---- natal context per control time (replicates _build_natal_context, no persist) ----
    natal_by_time: dict[str, dict] = {}
    house_system = "PLACIDUS"
    for t in all_times:
        tn0 = time.monotonic()
        chart = await client.get_natal(
            birth_date=profile.birthday.isoformat(),
            birth_time=t,
            birth_lat=float(profile.birth_lat),
            birth_lon=float(profile.birth_lon),
            birth_tz=profile.birth_tz or "UTC",
        )
        validated = SolarSageNatalResponse.model_validate(chart)
        natal_signals = norm.normalize_natal_only(chart)
        natal_scores = scoring.score_natal(natal_signals)
        ctx = NatalContextService._build_context_data(validated, natal_scores)
        natal_by_time[t] = ctx.model_dump(by_alias=False)
        house_system = ctx.house_system or house_system
        print(f"[natal] {t} built ({time.monotonic()-tn0:.2f}s)")

    # ---- transits cache (birth-independent) ----
    transits_cache: dict[str, dict] = {}

    async def transits_for(d: date) -> dict:
        if d.isoformat() not in transits_cache:
            transits_cache[d.isoformat()] = await client.get_transits(
                target_date=d.isoformat(), target_time="12:00", target_tz=transit_tz
            )
        return transits_cache[d.isoformat()]

    # raw normalized signals per (control time, date) — CPU cache for DayDelta
    raw_signals_cache: dict[tuple[str, str], list] = {}

    async def raw_signals_for(t: str, d: date):
        key = (t, d.isoformat())
        if key not in raw_signals_cache:
            raw_signals_cache[key] = norm.normalize_day(natal_by_time[t], await transits_for(d))
        return raw_signals_cache[key]

    # ---- per (control time, day): activation layer + factor records ----
    # act_layer_cache[(time, date)] = factor records list
    factor_records: dict[tuple[str, str], list[dict]] = {}
    calls = 0
    for t in all_times:
        natal = natal_by_time[t]
        tt0 = time.monotonic()
        d = DATE_FROM
        while d <= DATE_TO:
            rec_key = (t, d.isoformat())
            try:
                transits = await transits_for(d)
                signals_raw = await raw_signals_for(t, d)
                try:
                    y_signals = await raw_signals_for(t, d - timedelta(days=1))
                    signals = DayDeltaService(y_signals, signals_raw).compute_deltas()
                except Exception:
                    signals = signals_raw
                day_signals = filter_day_scored_signals(signals)
                sig_orb = {}
                for s in day_signals:
                    k = signal_sem_key(s)
                    if k:
                        sig_orb.setdefault(k, _g(s, "orb"))
                trig_keys = sorted({
                    k for s in signals
                    if getattr(s, "delta_kind", None) in ("new_today", "peak_today")
                    for k in [signal_sem_key(s)]
                    if k
                })
                sidecar_layer = await client.get_activation_layer(
                    birth_date=profile.birthday.isoformat(),
                    birth_time=t,
                    birth_lat=float(profile.birth_lat),
                    birth_lon=float(profile.birth_lon),
                    birth_tz=profile.birth_tz,
                    target_date=d.isoformat(),
                    target_time="12:00",
                    target_tz=transit_tz,
                    house_system=house_system,
                    current_location=current_location,
                )
                calls += 1
                al = ActivationLayerService().build(
                    natal_context=natal,
                    transits=transits,
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
                    day_delta=None,
                    target_date=d,
                    tz_info=user_tz,
                )
                recs = []
                for f in today_factors:
                    lf = ledger_by_id.get(f.factor_id)
                    sem_key = lf.semantic_key if lf else f.factor_id
                    orb = None
                    matched = acts_by_sem.get(sem_key) or []
                    if not matched:
                        matched = [a for aid, a in acts_by_id.items() if aid and aid in f.factor_id]
                    if matched:
                        orb = _g(matched[0], "orb")
                    if orb is None and sig_orb.get(sem_key) is not None:
                        orb = sig_orb[sem_key]
                    recs.append(
                        {
                            "semantic_key": sem_key,
                            "source": lf.source if lf else None,
                            "temporal_role": f.temporal_role,
                            "technique": f.technique,
                            "technique_family": f.technique_family,
                            "source_planet": f.source_key,
                            "aspect_type": f.aspect_type,
                            "orb": orb,
                            "strength": f.strength,
                            "polarity": f.polarity,
                            "target_type": f.target_type,
                            "target_key": f.target_key,
                            "theme_keys": list(f.theme_keys or ()),
                            "spheres": strict_product_spheres(
                                lf.technical_spheres if lf else [], f.source_key, f.target_key
                            ),
                        }
                    )
                factor_records[rec_key] = {"factors": recs, "trigger_keys": trig_keys}
            except Exception as exc:  # noqa: BLE001
                factor_records[rec_key] = {"error": f"{type(exc).__name__}: {exc}"}
            d += timedelta(days=1)
        n_days = (DATE_TO - DATE_FROM).days + 1
        print(f"[time {t}] {n_days} days done, cumulative act-layer calls={calls} "
              f"({time.monotonic()-tt0:.0f}s this time)")

    # ---- merge into per-(stratum, day) identity records ----
    def merge_stratum(times: list[str]) -> list[dict]:
        days_out = []
        d = DATE_FROM
        while d <= DATE_TO:
            per_time = [factor_records.get((t, d.isoformat())) for t in times]
            if any(isinstance(pt, dict) and "error" in pt for pt in per_time):
                days_out.append({"date": d.isoformat(), "error": "control-time failure"})
                d += timedelta(days=1)
                continue
            merged: dict[tuple, dict] = {}
            order: list[tuple] = []
            for ti, pt in enumerate(per_time):
                recs = pt["factors"]
                for r in recs:
                    ident = (r["semantic_key"], r["polarity"], tuple(r["spheres"]))
                    if ident not in merged:
                        m = {k: v for k, v in r.items()
                             if k not in ("temporal_role", "orb", "strength")}
                        m["presence"] = [False] * len(times)
                        m["roles"] = [None] * len(times)
                        m["orbs"] = [None] * len(times)
                        m["strengths"] = [None] * len(times)
                        merged[ident] = m
                        order.append(ident)
                    m = merged[ident]
                    m["presence"][ti] = True
                    m["roles"][ti] = r["temporal_role"]
                    m["orbs"][ti] = r["orb"]
                    m["strengths"][ti] = r["strength"]
            days_out.append({
                "date": d.isoformat(),
                "factors": [merged[k] for k in order],
                "per_time_counts": [len(pt["factors"]) for pt in per_time],
                "trigger_keys_per_time": [pt["trigger_keys"] for pt in per_time],
            })
            d += timedelta(days=1)
        return days_out

    strata_out: dict[str, dict] = {}
    for name, times in {**STRATA, **{f"shifted_{k}": v for k, v in SHIFTED.items()}}.items():
        strata_out[name] = {"control_times": times, "days": merge_stratum(times)}
        print(f"[merge] stratum {name} done")

    payload = {
        "meta": {
            "owner_tg": OWNER_TG,
            "range": [DATE_FROM.isoformat(), DATE_TO.isoformat()],
            "strata": {k: v["control_times"] for k, v in strata_out.items()},
            "day_delta": "computed per control time; corrected trigger keys stored per time",
            "current_location_passed": current_location is not None,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "act_layer_calls": calls,
            "natal_calls": len(all_times),
            "transit_calls": len(transits_cache),
        },
        "strata": strata_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"[done] {OUT} written, total {time.monotonic()-t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
