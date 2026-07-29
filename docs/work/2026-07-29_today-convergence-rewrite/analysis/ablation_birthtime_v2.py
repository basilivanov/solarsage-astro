#!/usr/bin/env python3
"""W1 ablation v2 — birth-time strata under the FIXED model (master v1.5).

Reads analysis/factor_dump_birthtime_v2.json (control-time merged dump with
per-time corrected DayDelta trigger keys) + analysis/factor_dump_v2.json
(exact stratum). Applies the fully fixed model (ablation_harness.FIXES all on:
three-tier eligibility, background out of groups, direct star grouping,
corrected delta triggers, sphere no fan-out, event_class whitelist_timelord,
orb fail-closed, rare narrowed) and the ORB-MARGIN stability rule:
  aspect factor is public iff present at ALL grid points of its range AND
  orb_ratio <= theta_o at EVERY grid point (fail-closed when the source has
  no canon max_orb); non-aspect factors: presence at all points.
Roles: corrected triggers upgrade roles per control time BEFORE resolution;
anchor only if anchor at every point. Bucket/unknown hard rule unchanged
(target_type in {house, angle, lot} not public).

Outputs: analysis/ablation_birthtime_v2.json + analysis/ablation_birthtime_v2.md.
No DB, no sidecar, no LLM. Run: apps/api/.venv/bin/python ablation_birthtime_v2.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import ablation_harness as H

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
BT = json.loads((ANALYSIS / "factor_dump_birthtime_v2.json").read_text())
EXACT = json.loads((ANALYSIS / "factor_dump_v2.json").read_text())
OUT_JSON = ANALYSIS / "ablation_birthtime_v2.json"
OUT_MD = ANALYSIS / "ablation_birthtime_v2.md"

ROLE_ORDER = {"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}
NON_PUBLIC_TARGETS = {"house", "angle", "lot"}
BUCKETS = ["night", "morning", "day", "evening"]
C1_W, C1_O = 0.55, 0.5
ALL_ON = dict(H.FIXES)  # all fixes enabled by default


def triggers_exact(day: dict) -> set[str]:
    tr = day.get("delta_triggers") or {}
    return set(tr.get("new_today", [])) | set(tr.get("peak", []))


def resolve_day_v2(day: dict, *, hard_exclude: bool) -> tuple[list[dict], list[dict]]:
    """Orb-margin publicity + per-time trigger upgrades + role resolution."""
    times_n = len(day["trigger_keys_per_time"])
    public: list[dict] = []
    excluded: list[dict] = []
    for m in day["factors"]:
        if not all(m["presence"]):
            excluded.append(m)
            continue
        # orb-margin: every point must satisfy orb_ratio <= C1_O (fail-closed)
        aspect = (m["aspect_type"] or "").upper() or None
        if aspect is not None:
            src = (m["source_planet"] or "").upper()
            denom = H.ORB_PROFILE.get(src)
            if denom is None:
                excluded.append(m)  # fail-closed: no canon max_orb for source
                continue
            ratios = [(o / denom) if o is not None else None for o in m["orbs"]]
            if any(r is None or r > C1_O for r in ratios):
                excluded.append(m)
                continue
        # per-time role with corrected triggers
        roles = []
        for i in range(times_n):
            r = m["roles"][i]
            if m["semantic_key"] in day["trigger_keys_per_time"][i]:
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


def resolve_exact(day: dict) -> list[dict]:
    trig = triggers_exact(day)
    out = []
    for f in day["factors"]:
        g = dict(f)
        if g["semantic_key"] in trig:
            g["temporal_role"] = "anchor_today"
        out.append(g)
    return out


def norm_state(r: dict) -> str:
    if r["state"] == "single_impulse" and r.get("n_anchors", 0) == 0:
        return "quiet_impulses"
    return r["state"]


def run() -> dict:
    results: dict[str, dict] = {}
    for name in ["exact"] + BUCKETS + ["unknown"]:
        hard_exclude = name != "exact"
        days_src = []
        victim_counter: Counter = Counter()
        total_ts = 0
        if name == "exact":
            for d in EXACT["days"]:
                if "error" in d:
                    continue
                days_src.append({"date": d["date"], "public": resolve_exact(d), "ts": []})
        else:
            for d in BT["strata"][name]["days"]:
                if "error" in d:
                    continue
                public, ts = resolve_day_v2(d, hard_exclude=hard_exclude)
                days_src.append({"date": d["date"], "public": public, "ts": ts,
                                 "per_time_counts": d.get("per_time_counts")})
        for d in days_src:
            r = H.classify_day_v2(d["public"], C1_W, C1_O, "B",
                                  fixes=ALL_ON, trigger_keys=None)
            d["state"] = norm_state(r)
            d["n_public"] = len(d["public"])
            d["n_significant"] = r["n_significant"]
            d["n_ts"] = len(d["ts"])
            total_ts += len(d["ts"])
            for m in d["ts"]:
                victim_counter[(m["technique_family"] or "?", m["target_type"] or "?")] += 1
        sig_counts = [d["n_significant"] for d in days_src]
        state_dist = Counter(d["state"] for d in days_src)
        results[name] = {
            "n_days": len(days_src),
            "hero_days_n": state_dist.get("hero", 0),
            "hero_days": [d["date"] for d in days_src if d["state"] == "hero"],
            "state_distribution": dict(state_dist),
            "median_significant": statistics.median(sig_counts),
            "zero_robust_public_days": sum(1 for d in days_src if d["n_public"] == 0),
            "mean_public_per_day": round(statistics.mean(d["n_public"] for d in days_src), 1),
            "mean_ts_excluded_per_day": round(total_ts / max(len(days_src), 1), 1),
            "total_ts_excluded": total_ts,
            "top_time_sensitive_victims": [
                {"technique_family": k[0], "target_type": k[1], "count": v}
                for k, v in victim_counter.most_common(6)
            ],
        }

    # ---- fixtures ----
    fixtures: dict[str, dict] = {}
    viol = 0
    for d in BT["strata"]["unknown"]["days"]:
        if "error" not in d:
            public, _ = resolve_day_v2(d, hard_exclude=True)
            viol += sum(1 for m in public if (m["target_type"] or "") in NON_PUBLIC_TARGETS)
    fixtures["8_unknown_no_house_angle_lot"] = {"violations": viol, "pass": viol == 0}

    def published_ids(public: list[dict]) -> list[str]:
        return sorted({json.dumps([m["semantic_key"], m["polarity"], m["spheres"]],
                                  ensure_ascii=False) for m in public})

    f9 = {}
    for b in BUCKETS:
        main_days = {d["date"]: d for d in BT["strata"][b]["days"] if "error" not in d}
        shift_days = {d["date"]: d for d in BT["strata"][f"shifted_{b}"]["days"] if "error" not in d}
        identical = differing = 0
        for dt, dm in main_days.items():
            ds = shift_days.get(dt)
            if ds is None:
                continue
            if published_ids(resolve_day_v2(dm, hard_exclude=True)[0]) == published_ids(
                resolve_day_v2(ds, hard_exclude=True)[0]
            ):
                identical += 1
            else:
                differing += 1
        f9[b] = {"identical_days": identical, "differing_days": differing,
                 "pass": differing == 0}
    fixtures["9_shifted_sample_invariance"] = f9

    f11 = {}
    for name in BUCKETS + ["unknown"]:
        ratios, dup = [], 0
        for d in BT["strata"][name]["days"]:
            if "error" in d:
                continue
            public, _ = resolve_day_v2(d, hard_exclude=True)
            ids = [(m["semantic_key"], m["polarity"], tuple(m["spheres"])) for m in public]
            if len(ids) != len(set(ids)):
                dup += 1
            raw = sum(sum(1 for p in m["presence"] if p) for m in d["factors"] if all(m["presence"]))
            if ids:
                ratios.append(raw / len(ids))
        f11[name] = {"duplicate_identity_violations": dup,
                     "mean_dedup_ratio": round(statistics.mean(ratios), 2) if ratios else None,
                     "pass": dup == 0}
    fixtures["11_sampling_no_multiplication"] = f11

    meta = BT["meta"]
    perf = {
        "dump_elapsed_s": meta["elapsed_s"],
        "act_layer_calls_total": meta["act_layer_calls"],
        "per_control_time_day_s": round(meta["elapsed_s"] / max(meta["act_layer_calls"], 1), 3),
    }

    out = {"meta": {"c1": {"theta_w": C1_W, "theta_o": C1_O}, "fixes": ALL_ON,
                    "dump_meta": meta},
           "strata": results, "fixtures": fixtures, "perf": perf}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def write_report(out: dict) -> None:
    s, fx, perf = out["strata"], out["fixtures"], out["perf"]
    L: list[str] = []
    w = L.append
    w("# Birth-time strata v2 (master v1.5): фиксированная модель + orb-margin\n")
    w("Модель: все фиксы F1–F8 включены; стабильность — ORB-MARGIN (аспект публичен, "
      "если присутствует на всех точках сетки И orb_ratio ≤ θ_o на КАЖДОЙ точке; "
      "fail-closed для источников вне orb-профиля канона). DayDelta-триггеры "
      "применяются по скорректированному контракту на каждом контрольном времени. "
      "Жёсткое правило bucket/unknown (без house/angle/lot) сохранено. Точка C1: "
      "θ_w=0.55, θ_o=0.5, правило B, hero = rare_anchor.\n")

    w("## 1. Сводная таблица (v2) и сравнение с v1\n")
    w("| страта | hero v2 | conv | single | quiet_imp | med sig | public/день | ts/день | zero-robust | hero v1 |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    v1_hero = {"exact": 10, "night": 2, "morning": 2, "day": 2, "evening": 1, "unknown": 1}
    for name in ["exact"] + BUCKETS + ["unknown"]:
        r = s[name]
        sd = r["state_distribution"]
        w(f"| {name} | {r['hero_days_n']} | {sd.get('convergence', 0)} | "
          f"{sd.get('single_impulse', 0)} | {sd.get('quiet_impulses', 0)} | "
          f"{r['median_significant']:.0f} | {r['mean_public_per_day']} | "
          f"{r['mean_ts_excluded_per_day']} | {r['zero_robust_public_days']} | {v1_hero[name]} |")
    w("")
    for name in ["exact"] + BUCKETS + ["unknown"]:
        w(f"- {name} hero-дни: {s[name]['hero_days']}")
    w("")

    w("## 2. time_sensitive жертвы (топ-6 на страту)\n")
    for name in BUCKETS + ["unknown"]:
        r = s[name]
        w(f"**{name}** (всего {r['total_ts_excluded']}): "
          + "; ".join(f"{v['technique_family']}/{v['target_type']}: {v['count']}"
                      for v in r["top_time_sensitive_victims"]))
    w("")

    w("## 3. Фикстуры\n")
    f8 = fx["8_unknown_no_house_angle_lot"]
    w(f"- (8) unknown без house/angle/lot: нарушений {f8['violations']} → "
      f"{'PASS' if f8['pass'] else 'FAIL'}.")
    w("- (9) инвариантность к сдвигу сэмпла (orb-margin правило):")
    for b, r in fx["9_shifted_sample_invariance"].items():
        w(f"  - {b}: identical {r['identical_days']}/81, differing {r['differing_days']} → "
          f"{'PASS' if r['pass'] else 'FAIL'}")
    w("- (11) сэмплинг не размножает юниты:")
    for name, r in fx["11_sampling_no_multiplication"].items():
        w(f"  - {name}: дубликатов {r['duplicate_identity_violations']}, "
          f"dedup-ratio {r['mean_dedup_ratio']}× → {'PASS' if r['pass'] else 'FAIL'}")
    w("")
    w("Примечание к фикстуре 9: orb-margin устраняет расхождения класса «орб-граничный "
      "аспект к натальной Луне» (пункт 3 разбора v1), но НЕ расхождения от секты/firdar "
      "(немонотонный day/night на sidecar — engine-баг из v1-отчёта) и ASC-зависимых "
      "профекций: они остаются сэмпл-зависимыми при 3-точечной сетке.\n")

    w("## 4. Производительность\n")
    per_call = perf["per_control_time_day_s"]
    w(f"- Дамп v2: {perf['dump_elapsed_s']}с, {perf['act_layer_calls_total']} act-layer вызовов, "
      f"~{per_call:.2f}с на (время, день). Pregen: bucket ≈ {3*per_call+0.1:.1f}с/польз-день, "
      f"unknown ≈ {6*per_call+0.15:.1f}с (exact ≈ {per_call+0.1:.1f}с).\n")

    w("## 5. Оговорки\n")
    w("- Те же, что в v1-стратах (секта sidecar, консервативная роль/max-орб, одна карта), "
      "плюс: orb-margin делает публичность зависимой от θ_o — смена порога значимости "
      "меняет и стабильный набор (задокументировать в каноне).")
    w("- DayDelta вчерашних сигналов считается по тому же контрольному времени — "
      "контракт «вчера/сегодня» согласован внутри каждой точки сетки.\n")

    OUT_MD.write_text("\n".join(L))


if __name__ == "__main__":
    out = run()
    write_report(out)
    print(f"json: {OUT_JSON}\nmd:   {OUT_MD}")
    for name, r in out["strata"].items():
        print(f"{name:9s} hero={r['hero_days_n']:2d}/81 med_sig={r['median_significant']:.0f} "
              f"public/day={r['mean_public_per_day']} ts/day={r['mean_ts_excluded_per_day']} "
              f"zero={r['zero_robust_public_days']}")
