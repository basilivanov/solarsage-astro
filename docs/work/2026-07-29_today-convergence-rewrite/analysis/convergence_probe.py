#!/usr/bin/env python3
"""Empirical probe: sphere-convergence day coverage for the product owner.

Replicates the DETERMINISTIC part of TodayService.get_today_payload wiring
(apps/api/app/services/today_service.py lines ~287-526):
  transits -> normalize_day -> DayDelta -> filter_day_scored_signals
  -> ActivationLayerService.build -> build_factor_ledger -> normalize_factors
  -> build_today_focus (OLD state)
Then classifies each day under the NEW strict sphere-eligibility rules
(no ("work",) fallback; unmapped factors excluded).

NO LLM calls. Read-only DB access (natal context loaded from NatalChartCache
via the same key logic as NatalContextService._find_active_cache).

Usage: cd /opt/solarsage-astro/apps/api && .venv/bin/python /tmp/convergence_probe.py
Writes per-day JSON to /tmp/convergence_probe_results.json and prints summary.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/solarsage-astro/apps/api")

from sqlalchemy import and_, func, select  # noqa: E402

from app.clients.solarsage_client import get_solarsage_client  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.models import (  # noqa: E402
    DayFeedback,
    EveningCheckin,
    NatalChartCache,
    User,
    UserProfile,
)
from app.db.session import SessionLocal  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.astro_utils import strip_prefix  # noqa: E402
from app.services.day_delta_service import DayDeltaService  # noqa: E402
from app.services.day_factor_ledger import build_factor_ledger  # noqa: E402
from app.services.day_scoring_runtime_service import should_compute_v2  # noqa: E402
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
    build_today_focus,
    normalize_factors,
)

DATE_FROM = date(2026, 6, 1)
DATE_TO = date(2026, 8, 20)
RESULTS_PATH = Path("/tmp/convergence_probe_results.json")


def _parse_args() -> None:
    global DATE_FROM, DATE_TO, RESULTS_PATH
    args = sys.argv[1:]
    if "--from" in args:
        DATE_FROM = date.fromisoformat(args[args.index("--from") + 1])
    if "--to" in args:
        DATE_TO = date.fromisoformat(args[args.index("--to") + 1])
    if "--out" in args:
        RESULTS_PATH = Path(args[args.index("--out") + 1])


_parse_args()


# ---------------------------------------------------------------------------
# NEW rules: strict sphere mapping — same maps as _map_to_product_spheres,
# but WITHOUT the ("work",) fallback. Empty result => factor excluded.
# ---------------------------------------------------------------------------
def strict_product_spheres(
    tech_spheres: list[str] | tuple[str, ...],
    source_key: str | None,
    target_key: str | None,
) -> tuple[str, ...]:
    res: set[str] = set()
    for ts in tech_spheres:
        pk = TECH_SPHERE_TO_PRODUCT_MAP.get(str(ts).lower())
        if pk:
            res.add(pk)
    for k in (source_key, target_key):
        if k:
            mapped = PLANET_TO_PRODUCT_MAP.get(strip_prefix(str(k)).upper())
            if mapped:
                res.update(mapped)
    return tuple(k for k in CANONICAL_PRODUCT_KEYS if k in res)


def classify_new_rules(factors: list, ledger_by_id: dict) -> dict:
    """Classify one day under the NEW strict eligibility rules.

    factors: TodayFactor list from normalize_factors.
    ledger_by_id: factor_id -> DayValenceFactor (semantic_key/technical_spheres).
    """
    enriched = []
    excluded_unmapped = 0
    for f in factors:
        lf = ledger_by_id.get(f.factor_id)
        sem_key = lf.semantic_key if lf else f.factor_id
        tech_spheres = lf.technical_spheres if lf else []
        spheres = strict_product_spheres(tech_spheres, f.source_key, f.target_key)
        if not spheres:
            excluded_unmapped += 1
            continue
        enriched.append(
            {
                "factor_id": f.factor_id,
                "semantic_key": sem_key,
                "role": f.temporal_role,
                "spheres": spheres,
                "target_key": f.target_key,
                "theme_keys": tuple(f.theme_keys or ()),
                "strength": f.strength,
                "technique_family": f.technique_family,
                "polarity": f.polarity,
            }
        )

    anchors_all = [f for f in factors if f.temporal_role == "anchor_today"]
    anchors_mapped = [e for e in enriched if e["role"] == "anchor_today"]

    def connected(a: dict, b: dict) -> bool:
        same_target = a["target_key"] is not None and a["target_key"] == b["target_key"]
        common_theme = bool(set(a["theme_keys"]) & set(b["theme_keys"]))
        return same_target or common_theme

    # Per-sphere grouping: connected components inside each product sphere.
    valid_groups: list[dict] = []
    per_sphere_sizes: dict[str, list[int]] = {}
    for sphere in CANONICAL_PRODUCT_KEYS:
        members = [e for e in enriched if sphere in e["spheres"]]
        if not members:
            continue
        parent = list(range(len(members)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if connected(members[i], members[j]):
                    union(i, j)

        comps: dict[int, list[dict]] = {}
        for i, m in enumerate(members):
            comps.setdefault(find(i), []).append(m)

        for comp in comps.values():
            distinct_sem = {m["semantic_key"] for m in comp}
            has_anchor = any(m["role"] == "anchor_today" for m in comp)
            if len(distinct_sem) >= 2 and has_anchor:
                anchor0 = next(m for m in comp if m["role"] == "anchor_today")
                conn = (
                    "shared_target"
                    if any(
                        m["target_key"] is not None and m["target_key"] == anchor0["target_key"]
                        for m in comp
                        if m["factor_id"] != anchor0["factor_id"]
                    )
                    else "theme_intersection"
                )
                valid_groups.append(
                    {
                        "sphere": sphere,
                        "size_semantic_keys": len(distinct_sem),
                        "connection": conn,
                        "members": [
                            {
                                "semantic_key": m["semantic_key"],
                                "role": m["role"],
                                "target_key": m["target_key"],
                                "technique_family": m["technique_family"],
                                "polarity": m["polarity"],
                                "theme_keys": list(m["theme_keys"]),
                            }
                            for m in sorted(comp, key=lambda x: (-x["strength"], x["factor_id"]))
                        ],
                    }
                )
                per_sphere_sizes.setdefault(sphere, []).append(len(distinct_sem))

    if valid_groups:
        state = "convergence"
    elif anchors_mapped:
        state = "single_impulse"
    else:
        state = "no_signal"

    return {
        "new_state": state,
        "valid_groups": valid_groups,
        "per_sphere_group_sizes": {k: sorted(v, reverse=True) for k, v in per_sphere_sizes.items()},
        "anchors_total": len(anchors_all),
        "anchors_mapped": len(anchors_mapped),
        "excluded_unmapped": excluded_unmapped,
        "mapped_factor_count": len(enriched),
        "anchor_sem_keys_mapped": sorted({a["semantic_key"] for a in anchors_mapped}),
        "roles_total": {
            role: sum(1 for f in factors if f.temporal_role == role)
            for role in ("anchor_today", "supporting", "background", "unrelated")
        },
    }


async def pick_owner(db):
    chk = (
        select(User.id, User.tg_username, func.count(EveningCheckin.id).label("n"))
        .join(EveningCheckin, EveningCheckin.user_id == User.id)
        .group_by(User.id, User.tg_username)
    )
    fb = select(DayFeedback.user_id, func.count(DayFeedback.id).label("n")).group_by(DayFeedback.user_id)
    chk_rows = {r.id: (r.tg_username, r.n) for r in (await db.execute(chk)).all()}
    fb_rows = {r.user_id: r.n for r in (await db.execute(fb)).all()}
    all_ids = set(chk_rows) | set(fb_rows)
    ranked = sorted(
        all_ids,
        key=lambda u: (chk_rows.get(u, (None, 0))[1], fb_rows.get(u, 0)),
        reverse=True,
    )
    if not ranked:
        raise RuntimeError("no users with check-ins or feedback found")
    table = [
        {
            "user_id": str(u)[:8],
            "tg_username": chk_rows.get(u, (None, 0))[0],
            "checkins": chk_rows.get(u, (None, 0))[1],
            "feedback": fb_rows.get(u, 0),
        }
        for u in ranked[:5]
    ]
    owner_id = ranked[0]
    user = (await db.execute(select(User).where(User.id == owner_id))).scalar_one()
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == owner_id))
    ).scalar_one()
    return user, profile, table


async def load_natal_context_readonly(db, user_id, profile) -> dict:
    """Same key logic as NatalContextService._find_active_cache, but read-only."""
    profile_hash = NatalContextService.compute_profile_hash(profile)
    cached = (
        await db.execute(
            select(NatalChartCache).where(
                and_(
                    NatalChartCache.user_id == user_id,
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
        raise RuntimeError("no active natal cache for owner; refusing to write (read-only probe)")
    ctx = NatalContextService._deserialize_context(cached.normalized_context_json)
    return ctx.model_dump(by_alias=False)


async def main() -> None:
    t0 = time.monotonic()
    compute_v2 = should_compute_v2()
    print(
        f"[flags] should_compute_v2={compute_v2} "
        f"solarsage_v2_enabled={getattr(settings, 'solarsage_v2_enabled', None)} "
        f"dual_run={getattr(settings, 'solarsage_v2_dual_run', None)} "
        f"valence_enabled={getattr(settings, 'today_valence_v1_enabled', None)}"
    )

    async with SessionLocal() as db:
        user, profile, table = await pick_owner(db)
        print(
            f"[owner] id={str(user.id)[:8]} tg_username={user.tg_username} "
            f"tz(current/birth)={profile.current_tz}/{profile.birth_tz}"
        )
        print(f"[owner] candidates: {json.dumps(table, ensure_ascii=False)}")
        natal_context_dict = await load_natal_context_readonly(db, user.id, profile)
        print("[natal] context loaded from NatalChartCache (read-only cache hit)")

    user_tz = profile.current_tz or profile.birth_tz or "Europe/Moscow"
    transit_tz = profile.current_tz or profile.birth_tz or "UTC"
    yesterday_tz = profile.birth_tz or "UTC"  # today_service._get_yesterday_signals quirk
    house_system = natal_context_dict.get("house_system", "PLACIDUS")
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
    normalization = NormalizationService()

    # Cache: normalize_day(natal, transits) is pure; today vs yesterday differ
    # only by tz argument, so key both caches by (date, tz).
    transits_cache: dict[tuple[str, str], dict] = {}
    signals_cache: dict[tuple[str, str], list] = {}

    async def transits_for(d: date, tz: str) -> dict:
        key = (d.isoformat(), tz)
        if key not in transits_cache:
            transits_cache[key] = await client.get_transits(
                target_date=d.isoformat(), target_time="12:00", target_tz=tz
            )
        return transits_cache[key]

    async def normalized_signals_for(d: date, tz: str):
        key = (d.isoformat(), tz)
        if key not in signals_cache:
            signals_cache[key] = normalization.normalize_day(
                natal_context_dict, await transits_for(d, tz)
            )
        return signals_cache[key]

    results: list[dict] = []
    sidecar_layer_failures = 0
    days = (DATE_TO - DATE_FROM).days + 1

    d = DATE_FROM
    while d <= DATE_TO:
        dt0 = time.monotonic()
        rec: dict = {"date": d.isoformat()}
        try:
            signals_raw = await normalized_signals_for(d, transit_tz)
            yesterday = d - timedelta(days=1)
            try:
                y_signals = await normalized_signals_for(yesterday, yesterday_tz)
            except Exception:
                y_signals = None
            if y_signals:
                signals = DayDeltaService(y_signals, signals_raw).compute_deltas()
            else:
                signals = signals_raw

            day_signals = filter_day_scored_signals(signals)

            sidecar_layer = None
            if compute_v2:
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
                except Exception as exc:  # fail-open like shadow mode
                    sidecar_layer_failures += 1
                    rec["sidecar_layer_error"] = type(exc).__name__

            activation_layer = ActivationLayerService().build(
                natal_context=natal_context_dict,
                transits=await transits_for(d, transit_tz),
                day_signals=day_signals,
                target_date=d,
                target_time="12:00",
                target_tz=transit_tz,
                house_system=house_system,
                sidecar_activation_layer=sidecar_layer,
            )

            ledger = build_factor_ledger(
                day_signals, activation_layer.activations if activation_layer else []
            )
            ledger_by_id = {f.factor_id: f for f in ledger.factors}

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
                activation_layer=activation_layer,
                day_delta=day_delta_dict,
                target_date=d,
                tz_info=user_tz,
            )

            # OLD state: exact existing focus builder (valence_assessments only
            # affect featured-sphere ranking, never the state).
            focus_res = build_today_focus(
                factors=today_factors,
                valence_assessments=None,
                tz_name=user_tz,
                target_date=d,
            )

            new = classify_new_rules(today_factors, ledger_by_id)

            rec.update(
                {
                    "old_state": focus_res.state,
                    "n_ledger_factors": len(ledger.factors),
                    "n_activations": len(activation_layer.activations) if activation_layer else 0,
                    "ledger_duplicates": ledger.duplicate_count,
                    "ledger_invalid": ledger.invalid_count,
                    **new,
                }
            )
        except Exception as exc:  # noqa: BLE001
            rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["elapsed_s"] = round(time.monotonic() - dt0, 2)
        results.append(rec)
        print(
            f"[day] {rec['date']} old={rec.get('old_state','ERR')} new={rec.get('new_state','ERR')} "
            f"factors={rec.get('n_ledger_factors','-')} anchors={rec.get('anchors_total','-')} "
            f"excl_unmapped={rec.get('excluded_unmapped','-')} ({rec['elapsed_s']}s)"
        )
        d += timedelta(days=1)

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    total = time.monotonic() - t0

    ok = [r for r in results if "error" not in r]
    print("\n==== SUMMARY ====")
    print(f"days covered: {len(ok)}/{len(results)} ({DATE_FROM}..{DATE_TO}), total {total:.0f}s, "
          f"avg {sum(r['elapsed_s'] for r in ok)/max(len(ok),1):.2f}s/day, "
          f"sidecar_layer_failures={sidecar_layer_failures}")
    for label, key in (("OLD", "old_state"), ("NEW", "new_state")):
        dist: dict[str, int] = {}
        for r in ok:
            dist[r[key]] = dist.get(r[key], 0) + 1
        pct = {k: f"{v} ({v/len(ok)*100:.0f}%)" for k, v in sorted(dist.items())}
        print(f"{label} distribution: {pct}")
    errs = [r for r in results if "error" in r]
    if errs:
        print(f"errors on {len(errs)} days: {[ (r['date'], r['error']) for r in errs ]}")
    print(f"results written to {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
