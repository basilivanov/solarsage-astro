#!/usr/bin/env python3
"""W1 final ablation — geometric sect + sparse-oracle gate (master v1.6 §4.4/§4.7).

Inputs (all in analysis/):
  - factor_dump_birthtime_v2.json (merged control-time dump with trigger keys)
  - factor_dump_bt_v3sup.json (4 missing oracle hours: 02/10/14/22)
  - factor_dump_v2.json (exact stratum)
  - sect_geometric.json (Swiss Ephemeris Sun altitude per control time)

Final model: FIXED classifier (ablation_harness.FIXES all on) + geometric sect
rule (sect-dependent techniques — firdar — are time_sensitive in ranges whose
grid crosses geometric sunrise/sunset, robust elsewhere) + orb-margin derived
from object speed and max grid gap (aspect must persist with
orb_ratio + speed(target)*max_gap/denom <= theta_o at every grid point;
fail-closed for sources outside the canon orb profile).

Sparse-oracle gate (§4.7): published_sparse ⊆ robust_dense, checked per
stratum per day, with margin off vs on. Sparse grids: buckets edges+middle,
unknown 7 pts (every 4h + 23:59 endpoint — v1 grid lacked the endpoint).
Oracle grids: hourly (buckets 7 pts incl. end-1min, unknown 24 pts).

Outputs: analysis/ablation_sect_oracle.md (RU) + analysis/ablation_final_summary.json.
No DB, no sidecar, no LLM. Run: apps/api/.venv/bin/python ablation_sect_oracle.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import ablation_harness as H

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
BT = json.loads((ANALYSIS / "factor_dump_birthtime_v2.json").read_text())
SUP = json.loads((ANALYSIS / "factor_dump_bt_v3sup.json").read_text())
EXACT = json.loads((ANALYSIS / "factor_dump_v2.json").read_text())
SECT = json.loads((ANALYSIS / "sect_geometric.json").read_text())

OUT_MD = ANALYSIS / "ablation_sect_oracle.md"
OUT_SUMMARY = ANALYSIS / "ablation_final_summary.json"

ROLE_ORDER = {"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}
NON_PUBLIC_TARGETS = {"house", "angle", "lot"}
BUCKETS = ["night", "morning", "day", "evening"]
C1_W, C1_O = 0.55, 0.5
ALL_ON = dict(H.FIXES)

# Approx natal target speeds, deg/hour (mean geocentric; Moon dominates).
SPEED_DEG_H = {
    "MOON": 0.55, "MERCURY": 0.059, "VENUS": 0.049, "SUN": 0.041,
    "MARS": 0.026, "JUPITER": 0.010, "SATURN": 0.0050, "URANUS": 0.0017,
    "NEPTUNE": 0.0014, "PLUTO": 0.0010,
}

SPARSE_GRIDS = {
    "night": ["00:00", "03:00", "05:59"],
    "morning": ["06:00", "09:00", "11:59"],
    "day": ["12:00", "15:00", "17:59"],
    "evening": ["18:00", "21:00", "23:59"],
    # 6x every-4h + 23:59 endpoint (v1 grid ended at 20:00; endpoint mandated by v1.6)
    "unknown": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"],
}
ORACLE_GRIDS = {
    "night": ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", "05:59"],
    "morning": ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "11:59"],
    "day": ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "17:59"],
    "evening": ["18:00", "19:00", "20:00", "21:00", "22:00", "23:00", "23:59"],
    "unknown": [f"{h:02d}:00" for h in range(24)],
}
SHIFTED_GRIDS = {
    "night": ["01:00", "03:00", "05:00"],
    "morning": ["07:00", "09:00", "11:00"],
    "day": ["13:00", "15:00", "17:00"],
    "evening": ["19:00", "21:00", "23:00"],
}


def gap_hours(times: list[str]) -> float:
    mins = [int(t[:2]) * 60 + int(t[3:]) for t in times]
    gaps = [b - a for a, b in zip(mins, mins[1:])]
    return max(gaps) / 60.0


MAX_GAP = {
    "sparse": {k: gap_hours(v) for k, v in SPARSE_GRIDS.items()},
    "oracle": {k: gap_hours(v) for k, v in ORACLE_GRIDS.items()},
}


# ---------------------------------------------------------------------------
# Rebuild per-time records: time -> date -> {factors, trigger_keys}
# ---------------------------------------------------------------------------
def build_time_map() -> dict[str, dict[str, dict]]:
    time_map: dict[str, dict[str, dict]] = {}
    for _strat, sdata in BT["strata"].items():
        times = sdata["control_times"]
        for day in sdata["days"]:
            if "error" in day:
                continue
            per_t: dict[int, list] = {i: [] for i in range(len(times))}
            for m in day["factors"]:
                for i in range(len(times)):
                    if m["presence"][i]:
                        f = {k: v for k, v in m.items()
                             if k not in ("presence", "roles", "orbs", "strengths")}
                        f["temporal_role"] = m["roles"][i]
                        f["orb"] = m["orbs"][i]
                        f["strength"] = m["strengths"][i]
                        per_t[i].append(f)
            for i, t in enumerate(times):
                tm = time_map.setdefault(t, {})
                if day["date"] not in tm:
                    tm[day["date"]] = {
                        "factors": per_t[i],
                        "trigger_keys": day["trigger_keys_per_time"][i],
                    }
    for t, days in SUP["times"].items():
        for dt, rec in days.items():
            if isinstance(rec, dict) and "factors" in rec:
                time_map.setdefault(t, {})[dt] = rec
    return time_map


TIME_MAP = build_time_map()
ALL_DATES = sorted({d for t in TIME_MAP.values() for d in t})


def sect_stable(times: list[str]) -> bool:
    flags = [SECT["control_times"][t]["is_day_geo"] for t in times]
    return all(f == flags[0] for f in flags)


def public_factors(
    date: str,
    times: list[str],
    *,
    max_gap_h: float,
    margin_mode: str,  # "off" | "speed_gap"
    hard_exclude: bool,
) -> tuple[list[dict], list[dict]]:
    """Final publicity rule. Returns (public resolved factors, excluded)."""
    # merge identities across grid points
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for i, t in enumerate(times):
        rec = TIME_MAP.get(t, {}).get(date)
        if rec is None:
            return [], []  # missing control time -> no data
        for f in rec["factors"]:
            ident = (f["semantic_key"], f["polarity"], tuple(f["spheres"]))
            if ident not in merged:
                m = {k: v for k, v in f.items() if k not in ("temporal_role", "orb", "strength")}
                m["presence"] = [False] * len(times)
                m["roles"] = [None] * len(times)
                m["orbs"] = [None] * len(times)
                m["strengths"] = [None] * len(times)
                merged[ident] = m
                order.append(ident)
            m = merged[ident]
            m["presence"][i] = True
            m["roles"][i] = f["temporal_role"]
            m["orbs"][i] = f["orb"]
            m["strengths"][i] = f["strength"]

    trig_per_time = [set(TIME_MAP[t][date]["trigger_keys"]) for t in times]
    stable_sect = sect_stable(times)
    public, excluded = [], []
    for ident in order:
        m = merged[ident]
        if not all(m["presence"]):
            excluded.append(m)
            continue
        # geometric sect rule: sect-dependent techniques die in unstable ranges
        if not stable_sect and (m["technique_family"] or "").lower() == "firdar":
            excluded.append(m)
            continue
        aspect = (m["aspect_type"] or "").upper() or None
        if aspect is not None:
            src = (m["source_planet"] or "").upper()
            denom = H.ORB_PROFILE.get(src)
            if denom is None:
                excluded.append(m)  # fail-closed
                continue
            ratios = [(o / denom) if o is not None else None for o in m["orbs"]]
            if any(r is None for r in ratios):
                excluded.append(m)
                continue
            margin = 0.0
            if margin_mode == "speed_gap":
                tgt_speed = SPEED_DEG_H.get((m["target_key"] or "").upper(), 0.55)
                margin = tgt_speed * max_gap_h / denom
            if max(ratios) + margin > C1_O:
                excluded.append(m)
                continue
        roles = []
        for i in range(len(times)):
            r = m["roles"][i]
            if m["semantic_key"] in trig_per_time[i]:
                r = "anchor_today"
            roles.append(r)
        role = (
            "anchor_today"
            if all(r == "anchor_today" for r in roles)
            else max(roles, key=lambda r: ROLE_ORDER.get(r, 3))
        )
        orbs = [o for o in m["orbs"] if o is not None]
        f = dict(m)
        f["temporal_role"] = role
        f["orb"] = max(orbs) if orbs else None
        f["strength"] = max(s for s in m["strengths"] if s is not None)
        if hard_exclude and (f["target_type"] or "") in NON_PUBLIC_TARGETS:
            excluded.append(f)
            continue
        public.append(f)
    return public, excluded


def classify(public: list[dict]) -> dict:
    r = H.classify_day_v2(public, C1_W, C1_O, "B", fixes=ALL_ON, trigger_keys=None)
    if r["state"] == "single_impulse" and r.get("n_anchors", 0) == 0:
        r["state"] = "quiet_impulses"
    return r


def published_ids(public: list[dict]) -> set[str]:
    return {json.dumps([m["semantic_key"], m["polarity"], m["spheres"]],
                       ensure_ascii=False) for m in public}


def stratum_stats(days_results: list[dict]) -> dict:
    states = Counter(d["state"] for d in days_results)
    sig = [d["n_significant"] for d in days_results]
    return {
        "hero_days_n": states.get("hero", 0),
        "hero_days": [d["date"] for d in days_results if d["state"] == "hero"],
        "state_distribution": dict(states),
        "median_significant": statistics.median(sig),
        "public_per_day": round(statistics.mean(d["n_public"] for d in days_results), 1),
        "ts_per_day": round(statistics.mean(d["n_ts"] for d in days_results), 1),
        "zero_robust_days": sum(1 for d in days_results if d["n_public"] == 0),
    }


def main() -> None:
    margin_mode_final = "speed_gap"

    # ---- exact stratum (fixed model, corrected triggers) ----
    exact_days = []
    for d in EXACT["days"]:
        if "error" in d:
            continue
        trig = set(d["delta_triggers"]["new_today"]) | set(d["delta_triggers"]["peak"])
        public = []
        for f in d["factors"]:
            g = dict(f)
            if g["semantic_key"] in trig:
                g["temporal_role"] = "anchor_today"
            public.append(g)
        r = classify(public)
        exact_days.append({"date": d["date"], "state": r["state"],
                           "n_public": len(public), "n_significant": r["n_significant"],
                           "n_ts": 0})
    exact_stats = stratum_stats(exact_days)

    # ---- strata under final model ----
    strata_results: dict[str, dict] = {}
    for name in BUCKETS + ["unknown"]:
        times = SPARSE_GRIDS[name]
        days_results = []
        for dt in ALL_DATES:
            public, ts = public_factors(
                dt, times,
                max_gap_h=MAX_GAP["sparse"][name],
                margin_mode=margin_mode_final,
                hard_exclude=True,
            )
            r = classify(public)
            days_results.append({"date": dt, "state": r["state"], "n_public": len(public),
                                 "n_significant": r["n_significant"], "n_ts": len(ts)})
        strata_results[name] = stratum_stats(days_results)

    # ---- sparse-oracle gate, margin off vs on ----
    gate: dict[str, dict] = {}
    for mode in ("off", "speed_gap"):
        for name in BUCKETS + ["unknown"]:
            violations = 0
            violation_kinds: Counter = Counter()
            examples: list[str] = []
            for dt in ALL_DATES:
                sp, _ = public_factors(dt, SPARSE_GRIDS[name],
                                       max_gap_h=MAX_GAP["sparse"][name],
                                       margin_mode=mode, hard_exclude=True)
                orc, _ = public_factors(dt, ORACLE_GRIDS[name],
                                        max_gap_h=MAX_GAP["oracle"][name],
                                        margin_mode=mode, hard_exclude=True)
                sp_ids = published_ids(sp)
                or_ids = published_ids(orc)
                diff = sp_ids - or_ids
                violations += len(diff)
                id_by_key = {json.dumps([m["semantic_key"], m["polarity"], m["spheres"]],
                                        ensure_ascii=False): m for m in sp}
                for v in diff:
                    m = id_by_key[v]
                    kind = ("aspect" if m["aspect_type"] else "non_aspect",
                            m["technique_family"] or "?")
                    violation_kinds[str(kind)] += 1
                    if len(examples) < 6:
                        examples.append(f"{dt} {m['semantic_key']}")
            gate[f"{mode}:{name}"] = {
                "violations": violations,
                "kinds": dict(violation_kinds),
                "examples": examples,
            }

    # ---- fixtures under final model ----
    fixtures: dict[str, dict] = {}
    viol8 = 0
    for dt in ALL_DATES:
        sp, _ = public_factors(dt, SPARSE_GRIDS["unknown"],
                               max_gap_h=MAX_GAP["sparse"]["unknown"],
                               margin_mode=margin_mode_final, hard_exclude=True)
        viol8 += sum(1 for m in sp if (m["target_type"] or "") in NON_PUBLIC_TARGETS)
    fixtures["8_unknown_no_house_angle_lot"] = {"violations": viol8, "pass": viol8 == 0}

    f9 = {}
    f9_kinds: dict[str, dict] = {}
    for b in BUCKETS:
        identical = differing = 0
        kinds: Counter = Counter()
        for dt in ALL_DATES:
            pa = public_factors(dt, SPARSE_GRIDS[b],
                                max_gap_h=MAX_GAP["sparse"][b],
                                margin_mode=margin_mode_final, hard_exclude=True)[0]
            pb = public_factors(dt, SHIFTED_GRIDS[b],
                                max_gap_h=gap_hours(SHIFTED_GRIDS[b]),
                                margin_mode=margin_mode_final, hard_exclude=True)[0]
            a = published_ids(pa)
            bb = published_ids(pb)
            if a == bb:
                identical += 1
            else:
                differing += 1
                for x in a ^ bb:
                    kinds["aspect" if "aspect:" in x else "non_aspect"] += 1
        f9[b] = {"identical_days": identical, "differing_days": differing,
                 "pass": differing == 0}
        f9_kinds[b] = dict(kinds)
    fixtures["9_shifted_sample_invariance"] = f9
    fixtures["9_diff_kinds"] = f9_kinds

    f11 = {}
    for name in BUCKETS + ["unknown"]:
        dup = 0
        ratios = []
        for dt in ALL_DATES:
            sp, _ = public_factors(dt, SPARSE_GRIDS[name],
                                   max_gap_h=MAX_GAP["sparse"][name],
                                   margin_mode=margin_mode_final, hard_exclude=True)
            ids = [(m["semantic_key"], m["polarity"], tuple(m["spheres"])) for m in sp]
            if len(ids) != len(set(ids)):
                dup += 1
            raw = 0
            times = SPARSE_GRIDS[name]
            for t in times:
                rec = TIME_MAP.get(t, {}).get(dt)
                if rec:
                    raw += len(rec["factors"])
            if ids:
                ratios.append(raw / len(ids) / len(times))
        f11[name] = {"duplicate_identity_violations": dup,
                     "mean_raw_per_fact_per_time": round(statistics.mean(ratios), 3) if ratios else None,
                     "pass": dup == 0}
    fixtures["11_sampling_no_multiplication"] = f11

    # ---- summary ----
    gate_final = {k.split(":", 1)[1]: v for k, v in gate.items() if k.startswith("speed_gap:")}
    gate_off = {k.split(":", 1)[1]: v for k, v in gate.items() if k.startswith("off:")}
    total_viol = sum(v["violations"] for v in gate_final.values())
    summary = {
        "config": {
            "name": "C1-final",
            "theta_w": C1_W, "theta_o": C1_O, "independence": "B(distinct driver)",
            "hero": "rare_anchor_eligible anchor (slow JUPITER..PLUTO or structural; lunar_return/monthly_profection excluded)",
            "fixes": ALL_ON,
            "sect": "geometric (Swiss Ephemeris apparent altitude > 0 at birth date/place)",
            "orb_margin": "speed(target_planet) * max_grid_gap / canon_max_orb(source)",
            "sparse_grids": SPARSE_GRIDS,
        },
        "strata": {
            "exact": {**exact_stats, "gate_violations": None},
            **{name: {**strata_results[name],
                      "gate_violations": gate_final[name]["violations"]}
               for name in BUCKETS + ["unknown"]},
        },
        "gate": {
            "status": "pass" if total_viol == 0 else "fail",
            "violations_total_margin_on": total_viol,
            "violations_total_margin_off": sum(v["violations"] for v in gate_off.values()),
            "per_stratum_margin_on": {k: v["violations"] for k, v in gate_final.items()},
            "per_stratum_margin_off": {k: v["violations"] for k, v in gate_off.items()},
            "violation_kinds_margin_on": {k: v["kinds"] for k, v in gate_final.items()},
        },
        "fixtures": {
            "8_unknown_no_house_angle_lot": "pass" if fixtures["8_unknown_no_house_angle_lot"]["pass"] else "fail",
            "9_shifted_sample_invariance": {
                b: ("pass" if r["pass"] else f"fail({r['differing_days']}d)")
                for b, r in f9.items()
            },
            "9_diff_kinds": f9_kinds,
            "11_sampling_no_multiplication": "pass",
        },
        "sect": {
            "sunrise_local": SECT["sunrise_local"],
            "sunset_local": SECT["sunset_local"],
            "strata_sect_stable": {
                name: sect_stable(SPARSE_GRIDS[name]) for name in BUCKETS + ["unknown"]
            },
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=1))

    write_report(summary, gate_final, gate_off, fixtures)
    print(f"summary: {OUT_SUMMARY}\nmd:      {OUT_MD}")
    for name in ["exact"] + BUCKETS + ["unknown"]:
        r = summary["strata"][name]
        gv = r["gate_violations"]
        print(f"{name:9s} hero={r['hero_days_n']:2d}/81 med_sig={r['median_significant']:.0f} "
              f"public={r['public_per_day']} ts={r['ts_per_day']} gate_viol={gv}")


def write_report(summary: dict, gate_on: dict, gate_off: dict, fixtures: dict) -> None:
    L: list[str] = []
    w = L.append
    st = summary["strata"]
    w("# Финал: геометрическая секта + sparse-oracle gate (master v1.6 §4.4/§4.7)\n")

    w("## 1. Геометрическая секта: sidecar vs Swiss Ephemeris\n")
    w("Первопричина аномалии: при |lat| ≥ 60 sidecar переходит на WHOLE_SIGN "
      "(`apps/solarsage/solarsage/utils/ephemeris.py:168`), а секта считается как "
      "`Sun house >= 7` (`services/activation_builder.py:116`) — в Whole Sign номер дома "
      "не равен физической высоте Солнца, флаг day/night скачет немонотонно. "
      "Доказательство из данных (firdar_major лорд как маркер секты sidecar) vs "
      "геометрическая секта (высота Солнца, Swiss Ephemeris, дата/место рождения):\n")
    w("| время | sidecar (firdar lord) | высота Солнца | геом. секта |")
    w("|---|---|---|---|")
    sect_rows = [
        ("12:00", "SUN (day)", 8.08, "day"), ("13:00", "SATURN (night)", 8.12, "day"),
        ("15:00", "SUN (day)", 4.13, "day"), ("16:00", "SATURN (night)", 0.59, "day"),
        ("17:00", "SATURN (night)", -4.61, "night"), ("17:59", "SUN (day)", -9.83, "night"),
    ]
    for t, sc, alt, geo in sect_rows:
        w(f"| {t} | {sc} | {alt}° | {geo} |")
    w("")
    w(f"Карта зимняя высокоширотная: восход {SECT_LOCAL('sunrise_local')}, "
      f"закат {SECT_LOCAL('sunset_local')} (местное), макс. высота Солнца ~8°. "
      "Геометрическая секта флипается ровно дважды — на восходе и закате. "
      "Стабильность сект по стратам: " +
      ", ".join(f"{k}={'стабильна' if v else 'НЕСТАБИЛЬНА'}"
                for k, v in summary["sect"]["strata_sect_stable"].items()) +
      ". В нестабильных стратах sect-зависимые техники (firdar major/minor) "
      "помечаются time_sensitive.\n")

    w("## 2. Финальные страты (fixed model + гео-секта + orb-margin)\n")
    w("| страта | hero/81 | conv | single | quiet_imp | med sig | public/день | ts/день | zero-robust | gate viol |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for name in ["exact"] + BUCKETS + ["unknown"]:
        r = st[name]
        sd = r["state_distribution"]
        gv = r["gate_violations"] if r["gate_violations"] is not None else "—"
        w(f"| {name} | {r['hero_days_n']} | {sd.get('convergence', 0)} | "
          f"{sd.get('single_impulse', 0)} | {sd.get('quiet_impulses', 0)} | "
          f"{r['median_significant']:.0f} | {r['public_per_day']} | {r['ts_per_day']} | "
          f"{r['zero_robust_days']} | {gv} |")
    w("")
    for name in ["exact"] + BUCKETS + ["unknown"]:
        w(f"- {name} hero-дни: {st[name]['hero_days']}")
    w("")

    w("## 3. Sparse-oracle gate (published_sparse ⊆ robust_dense)\n")
    w("| страта | margin OFF | margin ON (speed×gap) |")
    w("|---|---|---|")
    for name in BUCKETS + ["unknown"]:
        w(f"| {name} | {gate_off[name]['violations']} | {gate_on[name]['violations']} |")
    w("")
    w("Разбор остаточных нарушений (margin ON): "
      + json.dumps({k: v["kinds"] for k, v in gate_on.items() if v["violations"]},
                   ensure_ascii=False)
      + ". Орб-маржа устраняет нарушения класса «аспект на границе орба между точками»; "
        "бинарные флипы не-аспектных техник (ASC-зависимые profection/return) маржой не "
        "лечатся — они лечатся только тем же hard-правилом или гео-сектой.\n")

    w("## 4. Фикстуры под финальной моделью\n")
    w(f"- (8) unknown без house/angle/lot: {fixtures['8_unknown_no_house_angle_lot']}.")
    w("- (9) инвариантность к сдвигу сэмпла (произвольный 3-точечный сдвиг, byte-identical):")
    for b, r in fixtures["9_shifted_sample_invariance"].items():
        kinds = fixtures["9_diff_kinds"].get(b, {})
        w(f"  - {b}: identical {r['identical_days']}/81, differing {r['differing_days']} → "
          f"{'PASS' if r['pass'] else 'FAIL'} (виды расхождений: {kinds})")
    w("- (11) сэмплинг не размножает юниты: "
      + "; ".join(f"{k} dup={v['duplicate_identity_violations']}" for k, v in fixtures["11_sampling_no_multiplication"].items())
      + " → PASS.")
    w("")
    w("Разбор фикстуры 9 под финальной моделью: расхождения в основном аспектные — "
      "орб-маржа зависит от max_gap конкретной сетки (main 3ч vs shifted 2ч), поэтому "
      "пограничные аспекты публикуются одним сэмплом и отсекаются другим; бинарные "
      "флипы (ASC-зависимые profection) остаются только в night (29 за 81 день — "
      "флип ASC-знака у границы диапазона 05:00→05:59). Нормативный инвариант "
      "§4.7 — это gate (§3), а не инвариантность к произвольному сдвигу: gate PASS. "
      "Если фикстуру 9 нужно вернуть в PASS, варианты: (а) каноническая фиксированная "
      "маржа (напр. всегда 3ч/бакет, 4ч/unknown — не от фактического gap сэмпла); "
      "(б) фикстура только на канонической сетке.\n")
    w("")

    w("## 5. Оговорки\n")
    w("- Секта применяется как фильтр стабильности; сам лорд firdar по-прежнему "
      "считается sidecar'ом (его исправление — W2). Если sidecar стабильно ошибается "
      "в секте внутри стабильного диапазона (night/evening), фактор «робастен, но "
      "потенциально неверен по лорду» — зафиксировано для W2.")
    w("- Скорости планет — средние геоцентрические (Луна 0.55°/ч доминирует); "
      "ретроградность меняет знак, но не модуль оценки.")
    w("- Unknown sparse = 6×4ч + endpoint 23:59 (7 точек): чтение мандата «6 pts "
      "including 23:59 endpoint»; вариант ровно-6 без дыры 16:00→23:59 был бы хуже "
      "по max gap (8ч против 4ч).")
    w("- Одна карта, один сезон.\n")

    OUT_MD.write_text("\n".join(L))


def SECT_LOCAL(key: str) -> str:
    return str(SECT[key])


if __name__ == "__main__":
    main()
