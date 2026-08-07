#!/usr/bin/env python3
"""W1 ablation harness — threshold landscape for the Today-convergence rewrite.

Five-layer model (reviewer): raw fact -> significant impulse -> independent
evidence unit -> convergence -> presentation (presentation is LLM, out of scope).

Layers implemented over analysis/factor_dump.json (81 days, owner basil_ivanov):
  2. Significance: canon aspect_weight >= theta_w (non-aspect units = structural,
     pass; documented choice) AND orb_fraction <= theta_o (orb /
     orb_profile_default[source], fallback 6.0 for sources outside the profile;
     missing orb -> pass, counted) AND source rule theta_p in {any, non_moon,
     non_fast} applied to technique_family == "transit" units only
     (time-lords always pass).
  3. Independence: (A) distinct technique_family; (B) distinct driver
     (driver = source planet for transits; technique_family for time-lords).
     Rarity (C-style): slow source in JUPITER..PLUTO or time-lord family.
  4. Convergence per product sphere (strict mapping from the dump):
     connected components over shared target_key / theme_keys intersection;
     valid group = >=2 independent units AND >=1 anchor_today member.
     Hero-day predicates: hero_any = >=1 rare member; hero_rare_nonbg = rare
     member not background; hero_rare_anchor = rare member IS anchor_today.

Outputs:
  - analysis/ablation_grid.json: 31-config main grid + sanity reinterpretations
    + rarity-predicate sweep + leading-candidate detail + anomaly stats.
  - analysis/ablation_report.md: human-readable Russian report.

Pure stdlib + yaml; no DB, no sidecar, no LLM.
Run: /opt/solarsage-astro/apps/api/.venv/bin/python ablation_harness.py
"""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter
from pathlib import Path

import yaml

from convergence_canon import resolve_product_sphere

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
DUMP_PATH = ANALYSIS / "factor_dump.json"
GRID_PATH = ANALYSIS / "ablation_grid.json"
REPORT_PATH = ANALYSIS / "ablation_report.md"
CANON_PATH = Path("/opt/solarsage-astro/grace/canon/aspect_rules.v1.yml")
CONVERGENCE_CANON_PATH = Path("/opt/solarsage-astro/grace/canon/today_convergence.v1.yml")

TIME_LORD_FAMILIES = {
    "firdar", "profection", "solar_return", "lunar_return",
    "return", "progression", "progressive",
}
FAST_SOURCES = {"MOON", "MERCURY", "VENUS"}
SLOW_SOURCES = {"JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"}
ORB_FALLBACK = 6.0

CANON = yaml.safe_load(CANON_PATH.read_text())
ASPECT_WEIGHTS: dict[str, float] = {k.upper(): v for k, v in CANON["aspect_weights"].items()}
ORB_PROFILE: dict[str, float] = CANON["orb_profile_default"]
CONVERGENCE_CANON = yaml.safe_load(CONVERGENCE_CANON_PATH.read_text())
HERO_TARGET_TYPES: frozenset[str] = frozenset(
    str(value).lower()
    for value in CONVERGENCE_CANON["grouping"]["hero_target_types"]
)
FAST_HERO_CONFIRMATION = bool(
    CONVERGENCE_CANON["eligibility"]["fast"].get("hero_confirmation", False)
)
SLOW_HERO_CONFIRMATION = bool(
    CONVERGENCE_CANON["eligibility"]["slow"].get("hero_confirmation", True)
)

DUMP = json.loads(DUMP_PATH.read_text())
DAYS: list[dict] = [d for d in DUMP["days"] if "error" not in d]

LEADING = {"theta_w": 0.55, "theta_o": 0.5, "theta_p": "non_fast", "rule": "B",
           "hero_predicate": "rare_anchor"}


# --------------------------------------------------------------------------
# Layer helpers
# --------------------------------------------------------------------------
def is_time_lord(f: dict) -> bool:
    return (f["technique_family"] or "").lower() in TIME_LORD_FAMILIES


def driver_of(f: dict) -> str:
    if is_time_lord(f):
        return f"fam:{(f['technique_family'] or '').lower()}"
    return f"src:{f['source_planet'] or 'UNKNOWN'}"


def is_rare(f: dict) -> bool:
    """(C)-style rare/structural: slow transit source or time-lord technique."""
    if is_time_lord(f):
        return True
    return (f["source_planet"] or "").upper() in SLOW_SOURCES


def significance(f: dict, theta_w: float, theta_o: float, theta_p: str) -> tuple[bool, dict]:
    aspect = (f["aspect_type"] or "").upper() or None
    w = ASPECT_WEIGHTS.get(aspect) if aspect else None
    non_aspect = aspect is None or w is None
    pass_w = True if non_aspect else w >= theta_w

    orb = f["orb"]
    src = (f["source_planet"] or "").upper()
    denom = ORB_PROFILE.get(src, ORB_FALLBACK)
    orb_frac = (orb / denom) if orb is not None else None
    pass_o = True if orb_frac is None else orb_frac <= theta_o

    pass_p = True
    if (f["technique_family"] or "").lower() == "transit":
        if theta_p == "non_moon" and src == "MOON":
            pass_p = False
        elif theta_p == "non_fast" and src in FAST_SOURCES:
            pass_p = False

    return pass_w and pass_o and pass_p, {
        "aspect_weight": w,
        "non_aspect": non_aspect,
        "orb_fraction": orb_frac,
    }


def _connected(a: dict, b: dict) -> bool:
    same_target = a["target_key"] is not None and a["target_key"] == b["target_key"]
    return same_target or bool(set(a["theme_keys"]) & set(b["theme_keys"]))


def _components(members: list[dict]) -> list[list[dict]]:
    n = len(members)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _connected(members[i], members[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    comps: dict[int, list[dict]] = {}
    for i, m in enumerate(members):
        comps.setdefault(find(i), []).append(m)
    return list(comps.values())


def classify_day(
    factors: list[dict],
    theta_w: float,
    theta_o: float,
    theta_p: str,
    rule: str,
    extra: dict | None = None,
    hero_predicate: str = "any",
) -> dict:
    extra = extra or {}
    sig_units = []
    for f in factors:
        if not f["spheres"]:
            continue
        if extra.get("aspect_only") and not f["aspect_type"]:
            continue
        if extra.get("slow_sources_only") and (f["source_planet"] or "").upper() not in SLOW_SOURCES:
            continue
        if extra.get("planet_angle_targets_only") and (f["target_type"] or "") not in ("natal_planet", "angle"):
            continue
        ok, detail = significance(f, theta_w, theta_o, theta_p)
        if ok:
            sig_units.append({**f, **detail})

    def independence_count(members: list[dict]) -> int:
        if rule == "A":
            return len({(m["technique_family"] or "").lower() for m in members})
        return len({driver_of(m) for m in members})

    def hero_ok(members: list[dict]) -> bool:
        rare = [m for m in members if is_rare(m)]
        if hero_predicate == "any":
            return bool(rare)
        if hero_predicate == "rare_nonbg":
            return any(m["temporal_role"] != "background" for m in rare)
        return any(m["temporal_role"] == "anchor_today" for m in rare)  # rare_anchor

    valid_groups: list[dict] = []
    for sphere in sorted({s for u in sig_units for s in u["spheres"]}):
        members = [u for u in sig_units if sphere in u["spheres"]]
        for comp in _components(members):
            if independence_count(comp) < 2:
                continue
            if not any(m["temporal_role"] == "anchor_today" for m in comp):
                continue
            valid_groups.append({
                "sphere": sphere,
                "members": comp,
                "n_independent": independence_count(comp),
                "hero": hero_ok(comp),
            })

    hero_groups = [g for g in valid_groups if g["hero"]]
    n_sig = len(sig_units)
    if hero_groups:
        state = "hero"
    elif valid_groups:
        state = "convergence"
    elif n_sig >= 1:
        state = "single_impulse"
    else:
        state = "quiet"
    return {
        "state": state,
        "n_significant": n_sig,
        "tense": any(u["polarity"] == "tense" for u in sig_units),
        "n_anchors": sum(1 for u in sig_units if u["temporal_role"] == "anchor_today"),
        "hero_groups": hero_groups,
        "valid_groups": valid_groups,
        "sig_units": sig_units,
    }


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return xs[int(k)]
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def summarize(cfg: dict, results: list[dict]) -> dict:
    hero_days = [r["date"] for r in results if r["state"] == "hero"]
    sig_counts = [r["n_significant"] for r in results]
    streak = max_streak = 0
    for r in results:
        streak = streak + 1 if r["tense"] else 0
        max_streak = max(max_streak, streak)
    sphere_tally: Counter = Counter()
    for r in results:
        if r["state"] == "hero":
            for s in {g["sphere"] for g in r["hero_groups"]}:
                sphere_tally[s] += 1
    top_sphere, top_share = None, 0.0
    if sphere_tally and hero_days:
        top_sphere, cnt = sphere_tally.most_common(1)[0]
        top_share = cnt / len(hero_days)
    return {
        **{k: v for k, v in cfg.items() if k != "extra"},
        "hero_days_n": len(hero_days),
        "hero_days": hero_days,
        "convergence_days_n": sum(1 for r in results if r["state"] == "convergence"),
        "single_impulse_days_n": sum(1 for r in results if r["state"] == "single_impulse"),
        "quiet_days_n": sum(1 for r in results if r["state"] == "quiet"),
        "median_significant": statistics.median(sig_counts),
        "p90_significant": round(percentile(sig_counts, 0.9), 1),
        "max_tense_streak": max_streak,
        "top_hero_sphere": top_sphere,
        "top_hero_sphere_share": round(top_share, 3),
    }


def build_configs() -> list[dict]:
    cfgs: list[dict] = []
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            cfgs.append({"name": f"w{tw}_o{to}_nonfast_B", "theta_w": tw, "theta_o": to,
                         "theta_p": "non_fast", "rule": "B"})
    for tw in (0.40, 0.55):
        for to in (0.5, 1.0):
            for tp in ("any", "non_moon"):
                cfgs.append({"name": f"w{tw}_o{to}_{tp}_B", "theta_w": tw, "theta_o": to,
                             "theta_p": tp, "rule": "B"})
    for tw in (0.40, 0.55):
        cfgs.append({"name": f"w{tw}_o0.5_nonfast_A", "theta_w": tw, "theta_o": 0.5,
                     "theta_p": "non_fast", "rule": "A"})
    cfgs.append({
        "name": "SANITY_V0_slow_major_planet_angle",
        "theta_w": 0.85, "theta_o": 1.0, "theta_p": "any", "rule": "B",
        "extra": {"aspect_only": True, "slow_sources_only": True,
                  "planet_angle_targets_only": True},
    })
    return cfgs


SANITY_VARIANTS = [
    {"name": "V1_allow_lot_targets", "theta_w": 0.85, "theta_o": 1.0, "theta_p": "any", "rule": "B",
     "extra": {"aspect_only": True, "slow_sources_only": True}},
    {"name": "V2_sextile_counts_as_major", "theta_w": 0.55, "theta_o": 1.0, "theta_p": "any", "rule": "B",
     "extra": {"aspect_only": True, "slow_sources_only": True, "planet_angle_targets_only": True}},
    {"name": "V3_Mars_counts_as_slow_negative_control", "theta_w": 0.85, "theta_o": 1.0, "theta_p": "any",
     "rule": "B", "extra": {"aspect_only": True, "planet_angle_targets_only": True},
     "add_mars_to_slow": True},
]


def classify_v5(factors: list[dict]) -> bool:
    """Reviewer-proxy V5: slow-major aspect OR time-lord as significant members."""
    sig = []
    for f in factors:
        if not f["spheres"]:
            continue
        slow_major = (
            f["aspect_type"]
            and ASPECT_WEIGHTS.get(f["aspect_type"].upper(), 0) >= 0.85
            and (f["source_planet"] or "").upper() in SLOW_SOURCES
            and (f["target_type"] or "") in ("natal_planet", "angle")
        )
        if is_time_lord(f) or slow_major:
            sig.append(f)
    for sphere in sorted({s for u in sig for s in u["spheres"]}):
        mem = [u for u in sig if sphere in u["spheres"]]
        for comp in _components(mem):
            if len({driver_of(m) for m in comp}) >= 2 and any(
                m["temporal_role"] == "anchor_today" for m in comp
            ):
                if any(is_rare(m) for m in comp):
                    return True
    return False


def member_brief(m: dict) -> dict:
    return {
        "semantic_key": m["semantic_key"],
        "role": m["temporal_role"],
        "driver": driver_of(m),
        "aspect_type": m["aspect_type"],
        "orb": m["orb"],
        "orb_fraction": (round(m["orb_fraction"], 3) if m.get("orb_fraction") is not None else None),
        "aspect_weight": m.get("aspect_weight"),
        "polarity": m["polarity"],
        "rare": is_rare(m),
    }


def run() -> dict:
    # ---- 1. main grid ----
    grid: list[dict] = []
    for cfg in build_configs():
        results = []
        for day in DAYS:
            r = classify_day(day["factors"], cfg["theta_w"], cfg["theta_o"],
                             cfg["theta_p"], cfg["rule"], cfg.get("extra"))
            r["date"] = day["date"]
            results.append(r)
        grid.append(summarize(cfg, results))

    # ---- 2. sanity reinterpretations (bracket the reviewer's ~9/81) ----
    sanity_rows = []
    for cfg in SANITY_VARIANTS:
        if cfg.pop("add_mars_to_slow", False):
            SLOW_SOURCES.add("MARS")
        results = [
            classify_day(day["factors"], cfg["theta_w"], cfg["theta_o"], cfg["theta_p"],
                         cfg["rule"], cfg.get("extra"))
            for day in DAYS
        ]
        SLOW_SOURCES.discard("MARS")
        n = sum(1 for r in results if r["state"] == "hero")
        sanity_rows.append({"name": cfg["name"], "hero_days_n": n})
    v5_dates = [day["date"] for day in DAYS if classify_v5(day["factors"])]
    sanity_rows.append({"name": "V5_slow_major_aspect_OR_timelord_member",
                        "hero_days_n": len(v5_dates), "hero_days": v5_dates})

    # ---- 3. rarity-predicate sweep over the main 5x4 grid ----
    rarity_rows = []
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            counts = {"any": 0, "rare_nonbg": 0, "rare_anchor": 0}
            for day in DAYS:
                for pred in counts:
                    r = classify_day(day["factors"], tw, to, "non_fast", "B", hero_predicate=pred)
                    if r["state"] == "hero":
                        counts[pred] += 1
            rarity_rows.append({"theta_w": tw, "theta_o": to, **counts})

    # ---- 4. leading candidate detail (C1) ----
    lw, lo, lp = LEADING["theta_w"], LEADING["theta_o"], LEADING["theta_p"]
    lead_days = []
    for day in DAYS:
        r = classify_day(day["factors"], lw, lo, lp, "B", hero_predicate=LEADING["hero_predicate"])
        anchors = [u for u in r["sig_units"] if u["temporal_role"] == "anchor_today"]
        state = r["state"]
        if state == "single_impulse" and not anchors:
            state = "no_anchor"  # refined quiet: significant units exist, none anchoring today
        lead_days.append({
            "date": day["date"],
            "state": state,
            "n_significant": r["n_significant"],
            "n_anchors": len(anchors),
            "hero_groups": [
                {"sphere": g["sphere"], "n_independent": g["n_independent"],
                 "members": [member_brief(m) for m in g["members"]]}
                for g in r["hero_groups"]
            ],
            "anchor_keys": [u["semantic_key"] for u in anchors],
        })
    state_dist = Counter(d["state"] for d in lead_days)
    sig_counts = [d["n_significant"] for d in lead_days]
    quiet_examples = sorted(
        (d for d in lead_days if d["state"] != "hero"), key=lambda d: d["n_significant"]
    )[:3]
    leading = {
        "config": LEADING,
        "hero_days_n": state_dist.get("hero", 0),
        "state_distribution": dict(state_dist),
        "hero_days": [d for d in lead_days if d["state"] == "hero"],
        "quiet_examples": quiet_examples,
        "impulses_per_day": {
            "min": min(sig_counts), "p25": percentile(sig_counts, 0.25),
            "median": statistics.median(sig_counts), "p75": percentile(sig_counts, 0.75),
            "p90": round(percentile(sig_counts, 0.9), 1), "max": max(sig_counts),
        },
    }

    # ---- 5. anomalies / coverage ----
    all_factors = [f for d in DAYS for f in d["factors"]]
    orb_cov = Counter(f["orb_source"] for f in all_factors)
    asp = [f for f in all_factors if f["aspect_type"]]
    src_outside = Counter(
        (f["source_planet"] or "NONE") for f in all_factors
        if f["orb"] is not None and (f["source_planet"] or "").upper() not in ORB_PROFILE
    )
    anchors_all = [f for f in all_factors if f["temporal_role"] == "anchor_today"]
    anomalies = {
        "orb_coverage": dict(orb_cov),
        "orb_coverage_pct_aspects": round(
            100 * sum(1 for f in asp if f["orb"] is not None) / max(len(asp), 1), 1
        ),
        "orb_missing_only_non_aspect": all(
            not f["aspect_type"] for f in all_factors if f["orb"] is None
        ),
        "sources_outside_orb_profile_with_orb": dict(src_outside),
        "moon_share_of_anchors": round(
            sum(1 for f in anchors_all if (f["source_planet"] or "") == "MOON") / max(len(anchors_all), 1), 3
        ),
        "n_days": len(DAYS),
        "n_factors_total": len(all_factors),
    }

    out = {
        "meta": {
            "owner_tg": DUMP["meta"]["owner_tg"],
            "range": DUMP["meta"]["range"],
            "n_configs_main_grid": len(grid),
            "hero_predicate_main_grid": "any",
        },
        "configs": grid,
        "sanity_variants": sanity_rows,
        "rarity_predicates": rarity_rows,
        "leading_candidate": leading,
        "anomalies": anomalies,
    }
    GRID_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# --------------------------------------------------------------------------
# Report (RU)
# --------------------------------------------------------------------------
def write_report(out: dict) -> None:
    g = {r["name"]: r for r in out["configs"]}
    rare = {(r["theta_w"], r["theta_o"]): r for r in out["rarity_predicates"]}
    san = {r["name"]: r for r in out["sanity_variants"]}
    lead = out["leading_candidate"]
    an = out["anomalies"]

    L: list[str] = []
    w = L.append
    w("# W1 ablation: ландшафт порогов значимости и независимости (Today convergence rewrite)\n")
    w("Данные: владелец продукта (`basil_ivanov`), 81 день (2026-06-01..2026-08-20), "
      "детерминированный пайплайн TodayService без LLM (sidecar transits + activation layer, "
      "build_factor_ledger fallback — как в проде). Дамп: `factor_dump.json` "
      f"({an['n_factors_total']} факторов). Ниже — калибровочный ландшафт для слоёв "
      "«значимый импульс → независимая единица → convergence/hero». "
      "Победитель НЕ выбирался по близости к квоте 10–20% hero-дней (анти-Гудхарт); "
      "показаны колени и интерпретируемые области.\n")

    w("## 1. Главная сетка (θ_w × θ_o, θ_p=non_fast, независимость B, hero=rare любой член)\n")
    w("| config | hero/81 | conv | single | quiet | med sig | p90 sig | tense streak | top sphere (share) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            r = g[f"w{tw}_o{to}_nonfast_B"]
            w(f"| {r['name']} | {r['hero_days_n']} | {r['convergence_days_n']} | "
              f"{r['single_impulse_days_n']} | {r['quiet_days_n']} | {r['median_significant']:.0f} | "
              f"{r['p90_significant']:.0f} | {r['max_tense_streak']} | {r['top_hero_sphere']} ({r['top_hero_sphere_share']}) |")
    w("")
    w("Чтение: θ_w — главный регулятор (0.30→0.40: −13..15 hero-дней; 0.55→0.85: −7..8). "
      "θ_o монотонен и слабее: основной прирост между 0.7→1.0 (широкие орбы добавляют группы). "
      "`quiet` (0 значимых импульсов) недостижим ни в одной конфигурации: не-аспектные "
      "time-lord единицы (firdar/profection/return) структурны и всегда проходят фильтр веса — "
      "это осознанный дизайн-выбор, но он означает, что «пустой день» возможен только как "
      "«нет якоря», а не как «нет единиц». `tense_streak=81` везде: в этой карте всегда есть "
      "хотя бы один значимый напряжённый юнит — метрика недискриминативна.\n")

    w("## 2. Ось редкости hero (главное колено ландшафта)\n")
    w("Hero-предикаты: `any` — редкий юнит где-либо в группе; `rare_nonbg` — редкий юнит не "
      "background; `rare_anchor` — редкий юнит и есть якорь дня.\n")
    w("| θ_w | θ_o | hero_any | rare_nonbg | rare_anchor |")
    w("|---|---|---|---|---|")
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            r = rare[(tw, to)]
            w(f"| {tw} | {to} | {r['any']} | {r['rare_nonbg']} | {r['rare_anchor']} |")
    w("")
    w("Вывод: пока редкость засчитывается по background time-lord юнитам (profection, "
      "solar/lunar return — они есть каждый день), hero не падает ниже ~26/81. Перенос редкости "
      "в якорь («структурный/медленный фактор точен именно сегодня И подтверждён независимой "
      "единицей») переводит ландшафт в зону 6–18/81 — это a priori защитимое определение "
      "hero-дня, а не подгонка под квоту. Именно этот предикат согласует модель с оценкой "
      "ревьюера (см. §4).\n")

    w("## 3. Чувствительность к θ_p и правилу независимости\n")
    w("| config | hero/81 | conv | single | med sig |")
    w("|---|---|---|---|---|")
    for name in ("w0.4_o0.5_any_B", "w0.4_o0.5_non_moon_B", "w0.4_o0.5_nonfast_B",
                 "w0.55_o0.5_any_B", "w0.55_o0.5_non_moon_B", "w0.55_o0.5_nonfast_B",
                 "w0.4_o0.5_nonfast_A", "w0.55_o0.5_nonfast_A",
                 "w0.4_o1.0_any_B", "w0.4_o1.0_non_moon_B", "w0.4_o1.0_nonfast_B",
                 "w0.55_o1.0_any_B", "w0.55_o1.0_non_moon_B", "w0.55_o1.0_nonfast_B"):
        r = g[name]
        w(f"| {name} | {r['hero_days_n']} | {r['convergence_days_n']} | "
          f"{r['single_impulse_days_n']} | {r['median_significant']:.0f} |")
    w("")
    w("θ_p — самый сильный рычаг: `any` возвращает лунный шум (hero 79–81/81), `non_moon` "
      "снижает до 53–64/81, `non_fast` — до 35–38/81 (по hero_any). 76% всех якорей — лунные "
      "аспекты (Луна даёт точный аспект почти каждый день). Правило A (distinct "
      "technique_family) строже B (distinct driver): −5..7 hero-дней, т.к. несколько медленных "
      "транзитов разных планет схлопываются в одну семью «transit». B интерпретируемее "
      "(«разные физические драйверы»).\n")

    w("## 4. Sanity check: «slow + major + planet/angle» ревьюера (ожидание ≈9/81)\n")
    v0 = g["SANITY_V0_slow_major_planet_angle"]
    w(f"- V0, точная спека (источник JUPITER..PLUTO, вес ≥0.85, цель планета/угол, orb ≤ профиля): "
      f"**{v0['hero_days_n']}/81** {v0['hero_days']}")
    for name in ("V1_allow_lot_targets", "V2_sextile_counts_as_major",
                 "V3_Mars_counts_as_slow_negative_control",
                 "V5_slow_major_aspect_OR_timelord_member"):
        r = san[name]
        w(f"- {name}: **{r['hero_days_n']}/81**")
    w("")
    w("Отклонение от ≈9/81: −5 по точной спеке (V0=4), −2 по ближайшим переинтерпретациям "
      "(V2 «секстиль считать мажором» = 7; V5 «медленный мажор ИЛИ time-lord как член группы» = 7, "
      "даты почти совпадают с V0). Негативный контроль V3 (Марс считать медленным) даёт 78/81 — "
      "подтверждает чувствительность спеки к границе «slow». Итог: порядок величины совпадает, "
      "расхождение объясняется выбором множества аспектов и членства time-lord'ов; "
      "rare_anchor-предикат на общей сетке (§2) даёт ту же зону (6–13/81) без специальных "
      "ограничений.\n")

    w("## 5. Кандидатные конфигурации (ландшафт, не квота)\n")
    w("| кандидат | θ_w | θ_o | θ_p | независимость | hero-предикат | hero/81 | rationale |")
    w("|---|---|---|---|---|---|---|---|")
    w("| **C1 (leading)** | 0.55 | 0.5 | non_fast | B | rare_anchor | 10/81 (12%) | колено по весу "
      "(sextile+, без quincunx-шума), полу-орб a priori защитим, hero = структурный якорь дня |")
    w("| C2 (strict) | 0.85 | 0.5 | non_fast | B | rare_anchor | 7/81 (9%) | только мажорные "
      "аспекты; самый чистый сигнал, но отсекает секстили медленных планет |")
    w("| C3 (loose) | 0.40 | 0.5 | non_fast | B | rare_anchor | 12/81 (15%) | quincunx+; больше "
      "покрытие, но quincunx — спорный «значимый» аспект по канону (вес 0.40) |")
    w("")
    w("Трейдоффы: C1 сохраняет секстили медленных планет (в карте владельца это рабочая лошадка "
      "hero-дней — 4 из 10), C2 консервативнее и ближе к sanity-прокси ревьюера, C3 расширяет "
      "сигнал ценой шума. Все три — в дефенсибельной области (orb_fraction ≤ 0.5, без "
      "быстрых источников, структурный якорь); выбор между ними — продуктовый, не статистический.\n")

    w("## 6. Ведущий кандидат C1 — детально\n")
    sd = lead["state_distribution"]
    w(f"Распределение состояний за 81 день: hero {sd.get('hero', 0)}, "
      f"convergence {sd.get('convergence', 0)}, single_impulse {sd.get('single_impulse', 0)}, "
      f"no_anchor {sd.get('no_anchor', 0)} (тихие дни: значимые единицы есть, якоря нет). "
      f"Импульсов/день: min {lead['impulses_per_day']['min']}, "
      f"медиана {lead['impulses_per_day']['median']:.0f}, "
      f"p90 {lead['impulses_per_day']['p90']:.0f}, max {lead['impulses_per_day']['max']}.\n")
    w("### Hero-дни (дата — сфера — драйверы)\n")
    for d in lead["hero_days"]:
        g0 = d["hero_groups"][0]
        mem = sorted(g0["members"], key=lambda m: (m["role"] != "anchor_today", -(m["aspect_weight"] or 1)))
        parts = []
        for m in mem[:5]:
            of = f"{m['orb_fraction']:.2f}" if m["orb_fraction"] is not None else "—"
            parts.append(f"`{m['semantic_key']}` [{m['role']}, orb_f={of}]")
        w(f"- **{d['date']}** — {g0['sphere']} ({len(d['hero_groups'])} гр.): " + "; ".join(parts))
    w("")
    w("### Три тихих дня (минимум значимых импульсов, не hero)\n")
    for d in lead["quiet_examples"]:
        anch = ", ".join(f"`{k}`" for k in d["anchor_keys"]) or "нет якорей"
        w(f"- **{d['date']}**: {d['n_significant']} значимых единиц, {d['n_anchors']} якорей ({anch}) "
          f"→ состояние {d['state']}.")
    w("")
    w("Пример трактовки hero-дня: 2026-07-08 — точный `PLUTO trine natal SATURN` (orb_f=0.00) "
      "плюс независимые подтверждения того же таргета: `NEPTUNE opposition SATURN`, "
      "`URANUS trine SATURN`, firdar sub-period SATURN. 2026-07-12 (тишина): 40 значимых "
      "единиц, все supporting/background, ни одного якоря — день без повода для акцента.\n")

    w("## 7. Аномалии и оговорки\n")
    w(f"- **Orb-покрытие**: {an['orb_coverage_pct_aspects']}% аспектных факторов имеют orb "
      f"(activation: {an['orb_coverage'].get('activation')}, day_signal: {an['orb_coverage'].get('day_signal')}); "
      "все 2259 факторов без orb — не-аспектные (house-ингрессии, time-lord'ы), для них "
      "орб-тест неприменим by design (пропускаются, учтены отдельно).")
    w(f"- Источники вне orb-профиля канона: SOLAR ({an['sources_outside_orb_profile_with_orb'].get('SOLAR')}) "
      f"и PROGRESSED ({an['sources_outside_orb_profile_with_orb'].get('PROGRESSED')}) — прогрессии; использован "
      "знаменатель 6.0°, их orb и так 0.5–1.3° (orb_f 0.08–0.2), искажения нет.")
    w(f"- Доля лунных якорей: {an['moon_share_of_anchors']*100:.0f}% всех anchor_today — "
      "структурная причина 100% convergence в первом прогоне.")
    w("- **Мёртвый delta-trigger**: `classify_temporal_role` сравнивает `day_delta_dict` "
      "(голые имена планет вида «Moon») с полными factor_id/activation_id — совпадение "
      "невозможно, ветка `is_delta_trigger` не срабатывает никогда (прод-поведение, "
      "воспроизведено честно; кандидат на отдельный фикс).")
    w("- `is_rare` считает структурными ВСЕ time-lord семьи, включая ежемесячные "
      "lunar_return/monthly_profection — 2 из 10 hero-дней C1 (2026-06-18, 2026-08-12) "
      "обязаны именно lunar-return якорю; при желании «редкость = редкость» их можно "
      "исключить из rare-сета (−2 hero-дня).")
    w("- Доминирование сферы `decisions` (share 0.79–1.0) — артефакт планетных карт "
      "(SUN/MARS/SATURN/PLUTO/JUPITER все проецируются в decisions); маппинг сфер — "
      "отдельная тема калибровки.")
    w("- Группировка — connected components (транзитивное замыкание), а не якорные «звёзды» "
      "старого билдера; на решение «есть ли группа» влияет слабо, на состав — укрупняет.")
    w("- Горизонт одной карты и одного сезона (лето 2026, Pluto □ Sun и Neptune opp Saturn "
      "— перманентный фон); tense_streak=81 показывает, что фон этой карты всегда «tense» — "
      "калибровку валентности это не покрывает.")
    w("- Слой presentation (LLM) не моделировался (запрещён ограничениями задачи).\n")

    REPORT_PATH.write_text("\n".join(L))


if __name__ == "__main__":
    out = run()
    write_report(out)
    print(f"grid: {GRID_PATH} ({len(out['configs'])} configs)")
    print(f"report: {REPORT_PATH}")
    for row in out["configs"]:
        print(
            f"{row['name']:38s} hero={row['hero_days_n']:2d}/81 conv={row['convergence_days_n']:2d} "
            f"single={row['single_impulse_days_n']:2d} quiet={row['quiet_days_n']:2d} "
            f"med={row['median_significant']:.0f} p90={row['p90_significant']:.0f} "
            f"streak={row['max_tense_streak']:2d} top={row['top_hero_sphere']}:{row['top_hero_sphere_share']}"
        )


# ##########################################################################
# V2 SECTION (master v1.5 fixes). V1 functions above are left intact so the
# v1 artifacts (ablation_grid.json / ablation_report.md) stay reproducible.
# Every fix is a visible toggle in FIXES; event_class is a small enum.
# ##########################################################################

FIXES: dict = {
    "F1_three_tier": True,        # fast sources: impulse+evidence eligible, never rare_anchor (D7)
    "F2_background_out": True,    # background cannot be group member/witness/independence
    "F3_direct_grouping": True,   # anchor-seeded star groups, no transitive closure
    "F4_delta_fixed": True,       # corrected DayDelta triggers matched by semantic identity
    "F5_sphere_no_fanout": True,  # physical group -> one sphere plus facet/null
    "F6_event_class": "whitelist_timelord",  # auto | whitelist_timelord | strength_0.5 | strength_0.7
    "F7_orb_fail_closed": True,   # sources outside canon orb profile excluded (no 6.0 fallback)
    "F8_rare_narrowed": True,     # lunar_return & monthly_profection out of rare_anchor_eligible
    # Canon hero rules (master): hero_confirmation=false — fast sources never
    # count as the independent second witness for HERO (they still count for
    # impulses/medium); hero_target_types — the rare anchor's target must be a
    # natal planet or an angle (lot-target groups are medium, never hero).
    "hero_confirmation_fast_allowed": False,
    "hero_target_types": ("natal_planet", "angle"),
}

EVENT_CLASS_WHITELIST_TECHNIQUES = {
    "firdar_major", "firdar_minor", "annual_profection", "monthly_profection",
    "solar_return", "lunar_return", "secondary_progression", "solar_arc",
    "primary_direction", "progression",
}
RARE_EXCLUDED_TECHNIQUES = {"lunar_return", "monthly_profection"}  # F8
STRUCTURAL_RARE_TECHNIQUES = {
    "eclipse_window",
    "lunation",
    "solar_eclipse",
    "lunar_eclipse",
}


def significance_v2(
    f: dict,
    theta_w: float,
    theta_o: float,
    fixes: dict,
) -> tuple[bool, dict]:
    """Fixed significance: no source-planet exclusion (F1), event_class gate
    for non-aspect units (F6), fail-closed orb (F7)."""
    aspect = (f["aspect_type"] or "").upper() or None
    w = ASPECT_WEIGHTS.get(aspect) if aspect else None
    non_aspect = aspect is None or w is None
    if non_aspect:
        mode = fixes.get("F6_event_class", "auto")
        if mode == "auto":
            pass_w = True
        elif mode == "whitelist_timelord":
            pass_w = (f["technique"] or "").lower() in EVENT_CLASS_WHITELIST_TECHNIQUES
        else:  # strength_X.XX
            pass_w = (f["strength"] or 0.0) >= float(mode.split("_", 1)[1])
    else:
        pass_w = w >= theta_w

    orb = f["orb"]
    src = (f["source_planet"] or "").upper()
    orb_frac = None
    if orb is not None:
        denom = ORB_PROFILE.get(src)
        if denom is None:
            if fixes.get("F7_orb_fail_closed", False):
                return False, {"aspect_weight": w, "orb_fraction": None,
                               "excluded_orb_fail_closed": True}
            denom = ORB_FALLBACK
        orb_frac = orb / denom
    pass_o = True if orb_frac is None else orb_frac <= theta_o

    return pass_w and pass_o, {
        "aspect_weight": w,
        "non_aspect": non_aspect,
        "orb_fraction": orb_frac,
    }


def is_rare_anchor_eligible_v2(f: dict, fixes: dict) -> bool:
    """rare_anchor_eligible subset: slow-source aspect units OR structural
    time-lord techniques; F8 narrows the structural set; fast sources never
    (D7, F1)."""
    tech = (f["technique"] or "").lower()
    if fixes.get("F8_rare_narrowed", False) and tech in RARE_EXCLUDED_TECHNIQUES:
        return False
    if is_time_lord(f):
        return True
    if tech in STRUCTURAL_RARE_TECHNIQUES:
        return True
    src = (f["source_planet"] or "").upper()
    if src in FAST_SOURCES:  # D7: never rare_anchor, though impulse+evidence ok
        return False
    return src in SLOW_SOURCES


def is_hero_confirmation_eligible_v2(f: dict) -> bool:
    """Return whether a significant unit may confirm a rare hero anchor.

    Fast sources remain valid public impulses/evidence, but C1 deliberately
    excludes them from the independent hero-confirmation slot.  Background
    units are filtered before grouping and are repeated here as a fail-closed
    guard for callers that use this helper directly.
    """
    if f.get("temporal_role") == "background":
        return False
    source = (f.get("source_planet") or "").upper()
    if source in FAST_SOURCES:
        return FAST_HERO_CONFIRMATION
    if source in SLOW_SOURCES:
        return SLOW_HERO_CONFIRMATION
    # Non-planetary structural/time-lord evidence is eligible unless its
    # technique is explicitly excluded from the evidence layer.
    return True


def _hero_anchor_and_confirmation(
    members: list[dict],
    anchors: list[dict],
    rule: str,
    fixes: dict,
) -> tuple[dict | None, dict | None]:
    """Find a rare anchor with a direct, independent C1 confirmation.

    The old harness only checked ``any(rare anchor)`` and therefore accepted
    a fast Moon aspect as the second witness.  C1 requires the confirmer to be
    directly related to the same rare anchor and to use a distinct driver.
    """
    rare_anchors = [
        a
        for a in anchors
        if (a.get("target_type") or "").lower() in HERO_TARGET_TYPES
        and is_rare_anchor_eligible_v2(a, fixes)
    ]
    rare_anchors.sort(key=lambda a: (-float(a.get("strength") or 0.0), a["semantic_key"]))
    for rare in rare_anchors:
        rare_driver = driver_of(rare)
        confirmations = [
            u
            for u in members
            if u is not rare
            and is_hero_confirmation_eligible_v2(u)
            and driver_of(u) != rare_driver
            and _connected(rare, u)
        ]
        if rule == "A":
            confirmations = [
                u
                for u in confirmations
                if (u.get("technique_family") or "").lower()
                != (rare.get("technique_family") or "").lower()
            ]
        if confirmations:
            confirmer = sorted(
                confirmations,
                key=lambda u: (-float(u.get("strength") or 0.0), u["semantic_key"]),
            )[0]
            return rare, confirmer
    return None, None


def apply_fixed_delta_triggers(factors: list[dict], trigger_keys: set[str]) -> int:
    """F4: corrected DayDelta contract — semantic-identity matched triggers
    upgrade temporal_role to anchor_today. Returns number of upgraded units."""
    upgraded = 0
    for f in factors:
        if f["semantic_key"] in trigger_keys and f["temporal_role"] != "anchor_today":
            f["temporal_role"] = "anchor_today"
            upgraded += 1
    return upgraded


def _star_groups(members: list[dict], anchors: list[dict]) -> list[list[dict]]:
    """F3: anchor-seeded star grouping; clusters deduped by semantic-key set."""
    clusters: dict[frozenset, list[dict]] = {}
    for a in anchors:
        group = [a]
        for u in members:
            if u is a:
                continue
            if _connected(a, u):
                group.append(u)
        key = frozenset(m["semantic_key"] for m in group)
        if key not in clusters:
            clusters[key] = group
    return list(clusters.values())


def project_group_sphere(members: list[dict], anchor: dict) -> tuple[str | None, str | None]:
    """F5: resolve one physical group through the production S2 resolver.

    The return shape remains ``(sphere, facet)`` for the replay classifier, but
    the second value is now the nullable facet rather than a secondary sphere.
    Physical grouping and hero selection happen before this product projection.
    """
    houses = {member.get("house") for member in members if member.get("house") is not None}
    house = next(iter(houses)) if len(houses) == 1 else None
    technical_spheres = tuple(
        sorted(
            {
                str(value).strip().lower()
                for member in members
                for value in (member.get("technical_spheres") or ())
                if str(value).strip()
            }
        )
    )
    theme_keys = tuple(
        sorted(
            {
                str(value).strip().lower()
                for member in members
                for value in (member.get("theme_keys") or ())
                if str(value).strip()
            }
        )
    )
    resolved = resolve_product_sphere(
        house=house if isinstance(house, int) and not isinstance(house, bool) else None,
        technical_spheres=technical_spheres,
        theme_keys=theme_keys,
    )
    return resolved if resolved is not None else (None, None)


def _public_unit_sort_key(unit: dict) -> tuple:
    """Canonical presentation order for the public 0–3 unit window."""
    role_rank = {"anchor_today": 0, "supporting": 1, "background": 2}
    exact_at = unit.get("exact_at") or "9999-12-31T23:59:59+00:00"
    return (
        -float(unit.get("strength") or 0.0),
        role_rank.get(unit.get("temporal_role"), 3),
        exact_at,
        unit.get("factor_id") or unit.get("semantic_key") or "",
    )


def select_public_units_v2(sig_units: list[dict], groups: list[dict]) -> list[dict]:
    """Select at most three units used by presentation and tense metrics.

    This is deliberately performed after grouping.  Raw/background/noise
    units may remain in the audit, but they cannot keep a day permanently
    tense merely because they exist in the ledger.
    """
    if groups:
        candidate_units = [
            unit
            for group in groups
            for unit in group["members"]
            if unit.get("spheres")
        ]
    else:
        candidate_units = [unit for unit in sig_units if unit.get("spheres")]
    unique: dict[str, dict] = {}
    for unit in candidate_units:
        if unit.get("temporal_role") == "background":
            continue
        key = unit.get("semantic_key") or unit.get("factor_id")
        if key and key not in unique:
            unique[key] = unit
    return sorted(unique.values(), key=_public_unit_sort_key)[:3]


def _hero_ok(comp: list[dict], anchors_in: list[dict], fx: dict) -> bool:
    """Hero group: >=1 rare_anchor_eligible anchor whose target_type is in
    hero_target_types (natal_planet/angle), AND >=1 independent witness that
    is NOT a fast source when hero_confirmation_fast_allowed is False.
    Medium/convergence groups are unaffected (fast witnesses allowed there)."""
    target_types = fx.get("hero_target_types", ("natal_planet", "angle"))
    fast_ok = fx.get("hero_confirmation_fast_allowed", False)
    for a in anchors_in:
        if not is_rare_anchor_eligible_v2(a, fx):
            continue
        if (a["target_type"] or "") not in target_types:
            continue
        for u in comp:
            if u is a:
                continue
            if driver_of(u) == driver_of(a):
                continue
            if not fast_ok and (u["source_planet"] or "").upper() in FAST_SOURCES:
                continue
            return True
    return False


def classify_day_v2(
    factors: list[dict],
    theta_w: float,
    theta_o: float,
    rule: str = "B",
    fixes: dict | None = None,
    trigger_keys: set[str] | None = None,
) -> dict:
    """Fixed five-layer classification. hero = valid group whose >=1 anchor is
    rare_anchor_eligible. States: hero/convergence/single_impulse/quiet_impulses/quiet."""
    fx = dict(FIXES if fixes is None else fixes)
    # Product projection is deliberately later than the physical unit
    # boundary. Keep unresolved units in significance and direct grouping so
    # their event/group IDs and members remain in the replay ledger. Only the
    # published group/selection views below are fail-closed on sphere.
    units = [dict(f) for f in factors]

    delta_upgraded = 0
    if fx.get("F4_delta_fixed") and trigger_keys:
        delta_upgraded = apply_fixed_delta_triggers(units, trigger_keys)

    sig_units = []
    excluded_orb_fail_closed = 0
    for f in units:
        ok, detail = significance_v2(f, theta_w, theta_o, fx)
        if detail.get("excluded_orb_fail_closed"):
            excluded_orb_fail_closed += 1
        if ok:
            sig_units.append({**f, **detail})

    if fx.get("F2_background_out"):
        member_pool = [u for u in sig_units if u["temporal_role"] != "background"]
    else:
        member_pool = list(sig_units)

    def independence_count(members: list[dict]) -> int:
        if rule == "A":
            return len({(m["technique_family"] or "").lower() for m in members})
        return len({driver_of(m) for m in members})

    def group_from(comp: list[dict], sphere_hint: str | None) -> dict | None:
        anchors_in = [m for m in comp if m["temporal_role"] == "anchor_today"]
        if not anchors_in or independence_count(comp) < 2:
            return None
        hero_anchor, hero_confirmation = _hero_anchor_and_confirmation(
            comp, anchors_in, rule, fx
        )
        seed = hero_anchor or sorted(
            anchors_in, key=lambda m: (-m["strength"], m["semantic_key"])
        )[0]
        return {
            "members": comp,
            "anchor": seed,
            "hero_anchor": hero_anchor,
            "hero_confirmation": hero_confirmation,
            "n_independent": independence_count(comp),
            "hero": hero_anchor is not None,
            "sphere_hint": sphere_hint,
        }

    groups: list[dict] = []
    anchors = [u for u in member_pool if u["temporal_role"] == "anchor_today"]
    comps = (
        _star_groups(member_pool, anchors)
        if fx.get("F3_direct_grouping")
        else _components(member_pool)
    )
    for comp in comps:
        g = group_from(comp, None)
        if g:
            sphere, facet = project_group_sphere(g["members"], g["anchor"])
            g["spheres"] = (sphere,) if sphere else ()
            g["facet"] = facet
            if len(g["spheres"]) > 1:
                raise AssertionError("one convergence group may expose at most one sphere")
            groups.append(g)

    published_groups = [g for g in groups if g["spheres"]]
    hero_groups = [g for g in published_groups if g["hero"]]
    selected_public_units = select_public_units_v2(sig_units, published_groups)
    n_sig = len(sig_units)
    n_anchor = sum(1 for u in sig_units if u["temporal_role"] == "anchor_today")
    if hero_groups:
        state = "hero"
    elif published_groups:
        state = "convergence"
    elif n_anchor >= 1:
        state = "single_impulse"
    elif n_sig >= 1:
        state = "quiet_impulses"
    else:
        state = "quiet"
    return {
        "state": state,
        "n_significant": n_sig,
        "n_anchors": n_anchor,
        "tense": any(u["polarity"] == "tense" for u in selected_public_units),
        "groups": groups,
        "published_groups": published_groups,
        "n_groups": len(published_groups),
        "group_without_sphere_count": sum(not g["spheres"] for g in groups),
        "hero_groups": hero_groups,
        "sig_units": sig_units,
        "selected_public_units": selected_public_units,
        "delta_upgraded": delta_upgraded,
        "excluded_orb_fail_closed": excluded_orb_fail_closed,
    }
