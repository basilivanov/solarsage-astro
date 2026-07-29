#!/usr/bin/env python3
"""W1 ablation — rich per-day factor dump for the product owner (basil_ivanov).

Reuses the deterministic TodayService wiring (same as /tmp/convergence_probe.py):
sidecar transits -> normalize_day -> DayDelta -> filter_day_scored_signals
-> sidecar activation layer -> ActivationLayerService.build -> build_factor_ledger
-> normalize_factors. Prod takes the build_factor_ledger fallback path
(DualRunResult has no factor_ledger attribute) — matched here.

For EVERY ledger factor stores semantic_key, temporal_role, technique(_family),
source planet, aspect_type, orb (from the matched activation, else from the
originating day signal, else null + coverage flag), strength, polarity,
target_type/key, theme_keys, STRICT product spheres (no ("work",) fallback),
exact_at. Output: analysis/factor_dump.json. Read-only DB, no LLM, no secrets.

Run: cd /opt/solarsage-astro/apps/api && .venv/bin/python \
  ../docs/work/2026-07-29_today-convergence-rewrite/analysis/dump_factors.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/solarsage-astro/apps/api")

import yaml  # noqa: E402
from sqlalchemy import and_, select  # noqa: E402

from app.clients.solarsage_client import get_solarsage_client  # noqa: E402
from app.db.models import NatalChartCache, User, UserProfile  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.day_factor_ledger import (  # noqa: E402
    ANGLES,
    LOTS,
    _normalize_target_type,
    build_factor_ledger,
)
from app.services.day_scoring_signals import filter_day_scored_signals  # noqa: E402
from app.services.natal_context_service import (  # noqa: E402
    CALCULATION_VERSION,
    ENGINE_VERSION,
    HOUSE_SYSTEM_DEFAULT,
    NatalContextService,
)
from app.services.normalization_service import NormalizationService  # noqa: E402
from app.services.today_focus_builder import (  # noqa: E402
    CANONICAL_PRODUCT_KEYS,
    PLANET_TO_PRODUCT_MAP,
    TECH_SPHERE_TO_PRODUCT_MAP,
    normalize_factors,
)

REPO = Path("/opt/solarsage-astro")
OUT = REPO / "docs/work/2026-07-29_today-convergence-rewrite/analysis/factor_dump.json"
CANON_PATH = REPO / "grace/canon/aspect_rules.v1.yml"
DATE_FROM = date(2026, 6, 1)
DATE_TO = date(2026, 8, 20)
OWNER_TG = "basil_ivanov"


def _g(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def act_sem_key(act) -> str | None:
    """Replicates normalize_factors._act_sem_key (nested fn, not importable)."""
    planet = strip_prefix(str(_g(act, "planet") or "")).upper()
    target = strip_prefix(str(_g(act, "target_planet") or "")).upper()
    aspect = str(_g(act, "aspect_type") or "").lower()
    if not (planet and target and aspect):
        return None
    tt_raw = str(_g(act, "target_type") or "").lower()
    if tt_raw in ("angle", "lot", "house"):
        tt = tt_raw
    elif target.upper() in {"ASC", "MC", "IC", "DESC", "DSC"}:
        tt = "angle"
    elif target.upper() in {"FORTUNE", "SPIRIT", "EROS", "SCIENCE", "MARRIAGE"}:
        tt = "lot"
    else:
        tt = "natal_planet"
    return f"aspect:{planet}:{aspect}:{tt}:{target}"


def strict_product_spheres(tech_spheres, source_key, target_key) -> list[str]:
    """Same maps as _map_to_product_spheres, WITHOUT the ("work",) fallback."""
    res: set[str] = set()
    for ts in tech_spheres or []:
        pk = TECH_SPHERE_TO_PRODUCT_MAP.get(str(ts).lower())
        if pk:
            res.add(pk)
    for k in (source_key, target_key):
        if k:
            mapped = PLANET_TO_PRODUCT_MAP.get(strip_prefix(str(k)).upper())
            if mapped:
                res.update(mapped)
    return [k for k in CANONICAL_PRODUCT_KEYS if k in res]


def signal_sem_key(sig) -> str | None:
    """Semantic key of a day signal, mirroring build_factor_ledger's day-signal branch."""
    sig_type = _g(sig, "type")
    planet = strip_prefix(str(_g(sig, "planet") or "")).strip().upper()
    if not planet:
        return None
    if sig_type == "aspect":
        target = strip_prefix(str(_g(sig, "target_planet") or "")).strip().upper()
        aspect = str(_g(sig, "aspect_type") or "").strip().lower()
        if not target or not aspect:
            return None
        tt = _normalize_target_type(None, target)
        return f"aspect:{planet}:{aspect}:{tt}:{target}"
    if sig_type == "planet_in_house":
        house = _g(sig, "house")
        if house is None:
            return None
        return f"house:{planet}:{house}"
    return None


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

    user_tz = profile.current_tz or profile.birth_tz or "Europe/Moscow"
    transit_tz = profile.current_tz or profile.birth_tz or "UTC"
    yesterday_tz = profile.birth_tz or "UTC"  # today_service quirk, replicated
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

    client = get_solarsage_client()
    norm = NormalizationService()
    transits_cache: dict[tuple[str, str], dict] = {}
    signals_cache: dict[tuple[str, str], list] = {}

    async def transits_for(d: date, tz: str) -> dict:
        key = (d.isoformat(), tz)
        if key not in transits_cache:
            transits_cache[key] = await client.get_transits(
                target_date=d.isoformat(), target_time="12:00", target_tz=tz
            )
        return transits_cache[key]

    async def signals_for(d: date, tz: str):
        key = (d.isoformat(), tz)
        if key not in signals_cache:
            signals_cache[key] = norm.normalize_day(natal, await transits_for(d, tz))
        return signals_cache[key]

    days_out: list[dict] = []
    sidecar_failures = 0
    d = DATE_FROM
    while d <= DATE_TO:
        dt0 = time.monotonic()
        rec: dict = {"date": d.isoformat(), "factors": []}
        try:
            signals_raw = await signals_for(d, transit_tz)
            try:
                y_signals = await signals_for(d - timedelta(days=1), yesterday_tz)
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
                transits=await transits_for(d, transit_tz),
                day_signals=day_signals,
                target_date=d,
                target_time="12:00",
                target_tz=transit_tz,
                house_system=house_system,
                sidecar_activation_layer=sidecar_layer,
            )
            ledger = build_factor_ledger(day_signals, al.activations if al else [])
            ledger_by_id = {f.factor_id: f for f in ledger.factors}

            # activation matching replicated from normalize_factors
            acts_by_sem: dict[str, list] = {}
            acts_by_id: dict[str, object] = {}
            for act in al.activations if al else []:
                act_id = _g(act, "id") or _g(act, "activation_id")
                if act_id:
                    acts_by_id[str(act_id)] = act
                sem = act_sem_key(act)
                if sem:
                    acts_by_sem.setdefault(sem, []).append(act)

            day_delta_dict = {
                "new_today": [
                    strip_prefix(getattr(s, "planet", ""))
                    for s in signals
                    if getattr(s, "delta_kind", None) == "new_today"
                ],
                "peak": [
                    strip_prefix(getattr(s, "planet", ""))
                    for s in signals
                    if getattr(s, "delta_kind", None) == "peak_today"
                ],
            }
            today_factors = normalize_factors(
                ledger=ledger,
                activation_layer=al,
                day_delta=day_delta_dict,
                target_date=d,
                tz_info=user_tz,
            )

            for f in today_factors:
                lf = ledger_by_id.get(f.factor_id)
                sem_key = lf.semantic_key if lf else f.factor_id
                # orb: matched activation first, then originating day signal
                orb, orb_source = None, "none"
                matched = acts_by_sem.get(sem_key) or []
                if not matched:
                    matched = [a for aid, a in acts_by_id.items() if aid and aid in f.factor_id]
                if matched:
                    orb = _g(matched[0], "orb")
                    if orb is not None:
                        orb_source = "activation"
                if orb is None and sem_key in sig_orb and sig_orb[sem_key] is not None:
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
                        "active_from": f.active_from.isoformat() if f.active_from else None,
                        "phase": f.phase,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["elapsed_s"] = round(time.monotonic() - dt0, 2)
        days_out.append(rec)
        print(f"[dump] {rec['date']} factors={len(rec['factors'])} ({rec['elapsed_s']}s)")
        d += timedelta(days=1)

    payload = {
        "meta": {
            "owner_tg": OWNER_TG,
            "user_tz": user_tz,
            "range": [DATE_FROM.isoformat(), DATE_TO.isoformat()],
            "sidecar_failures": sidecar_failures,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "canon_aspect_weights": canon.get("aspect_weights"),
            "canon_orb_profile_default": canon.get("orb_profile_default"),
            "canon_planet_velocity_class": canon.get("planet_velocity_class"),
        },
        "days": days_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False))
    ok = [x for x in days_out if "error" not in x]
    total_f = sum(len(x["factors"]) for x in ok)
    with_orb = sum(1 for x in ok for f in x["factors"] if f["orb"] is not None)
    print(
        f"[done] days={len(ok)}/{len(days_out)} factors={total_f} "
        f"orb_coverage={with_orb}/{total_f} ({100*with_orb/max(total_f,1):.1f}%) "
        f"sidecar_failures={sidecar_failures} -> {OUT}"
    )


if __name__ == "__main__":
    asyncio.run(main())
