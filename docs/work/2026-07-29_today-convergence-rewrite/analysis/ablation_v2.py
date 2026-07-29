#!/usr/bin/env python3
"""W1 ablation v2 — fixed five-layer model (master v1.5): per-fix ablation,
31-config sweep, C1 comparison, sphere distribution, tense streaks.

Reads analysis/factor_dump_v2.json (corrected DayDelta trigger sets included).
Writes analysis/ablation_grid_v2.json + analysis/ablation_report_v2.md (RU).
Imports v1 primitives from ablation_harness (left intact) + the v2 FIXES section.
No DB, no sidecar, no LLM. Run: apps/api/.venv/bin/python ablation_v2.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import ablation_harness as H

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
DUMP = json.loads((ANALYSIS / "factor_dump_v2.json").read_text())
DAYS = [d for d in DUMP["days"] if "error" not in d]
OUT_JSON = ANALYSIS / "ablation_grid_v2.json"
OUT_MD = ANALYSIS / "ablation_report_v2.md"

C1_W, C1_O = 0.55, 0.5


def fixes(**over):
    base = {
        "F1_three_tier": False, "F2_background_out": False, "F3_direct_grouping": False,
        "F4_delta_fixed": False, "F5_sphere_no_fanout": False,
        "F6_event_class": "auto", "F7_orb_fail_closed": False, "F8_rare_narrowed": False,
    }
    base.update(over)
    return base


ALL_ON = fixes(**{
    "F1_three_tier": True, "F2_background_out": True, "F3_direct_grouping": True,
    "F4_delta_fixed": True, "F5_sphere_no_fanout": True,
    "F6_event_class": "whitelist_timelord", "F7_orb_fail_closed": True,
    "F8_rare_narrowed": True,
})


def triggers_of(day: dict) -> set[str]:
    tr = day.get("delta_triggers") or {}
    return set(tr.get("new_today", [])) | set(tr.get("peak", []))


def run_v1_baseline():
    out = []
    for day in DAYS:
        r = H.classify_day(day["factors"], C1_W, C1_O, "non_fast", "B",
                           hero_predicate="rare_anchor")
        out.append({"date": day["date"], "result": r})
    return out


def run_v2(fx, prefilter_fast=False):
    out = []
    for day in DAYS:
        factors = day["factors"]
        if prefilter_fast:
            # legacy non_fast significance exclusion (theta_p as exclusion, pre-F1)
            factors = [
                f for f in factors
                if not (
                    (f["technique_family"] or "").lower() == "transit"
                    and (f["source_planet"] or "").upper() in H.FAST_SOURCES
                )
            ]
        tk = triggers_of(day) if fx.get("F4_delta_fixed") else None
        r = H.classify_day_v2(factors, C1_W, C1_O, "B", fixes=fx, trigger_keys=tk)
        out.append({"date": day["date"], "result": r})
    return out


def _norm_state(r: dict) -> str:
    """Unify v1/v2 day states: single_impulse requires >=1 significant anchor;
    days with significant units but no anchor are quiet_impulses."""
    st = r["state"]
    if st == "single_impulse":
        n_anch = r.get("n_anchors")
        if n_anch is None:
            n_anch = sum(1 for u in r.get("sig_units", []) if u["temporal_role"] == "anchor_today")
        if n_anch == 0:
            return "quiet_impulses"
    return st


def state_stats(rows) -> dict:
    states = Counter(_norm_state(r["result"]) for r in rows)
    sig = [r["result"]["n_significant"] for r in rows]
    return {
        "hero": states.get("hero", 0),
        "convergence": states.get("convergence", 0),
        "single_impulse": states.get("single_impulse", 0),
        "quiet_impulses": states.get("quiet_impulses", 0),
        "quiet": states.get("quiet", 0),
        "med_sig": statistics.median(sig),
        "p90_sig": round(H.percentile(sig, 0.9), 1),
        "hero_days": [r["date"] for r in rows if r["result"]["state"] == "hero"],
        "delta_upgraded_total": sum(r["result"].get("delta_upgraded", 0) for r in rows),
        "excluded_orb_fail_closed_total": sum(
            r["result"].get("excluded_orb_fail_closed", 0) for r in rows
        ),
    }


def tense_streaks(rows) -> dict:
    flags = [r["result"]["tense"] for r in rows]
    runs, cur = [], 0
    for f in flags:
        if f:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return {
        "tense_days": sum(flags),
        "max_streak": max(runs) if runs else 0,
        "median_streak": statistics.median(runs) if runs else 0,
        "n_streaks": len(runs),
    }


def hero_sphere_counts(rows, mode: str) -> Counter:
    c = Counter()
    for r in rows:
        for g in r["result"]["hero_groups"]:
            if mode == "v1":
                c[g["sphere"]] += 1
            else:
                for s in g.get("spheres", ()):  # primary + optional secondary
                    c[s] += 1
    return c


def main() -> None:
    # ---------- 1. per-fix cumulative ablation at the C1 point ----------
    chain: list[tuple[str, dict]] = [("baseline v1 (C1, rare_anchor, non_fast)", None)]
    chain_rows = [state_stats(run_v1_baseline())]

    steps = [
        ("+F1 three-tier (fast = impulse/evidence)", fixes(F1_three_tier=True)),
        ("+F2 background out of groups", fixes(F1_three_tier=True, F2_background_out=True)),
        ("+F3 direct star grouping", fixes(F1_three_tier=True, F2_background_out=True,
                                           F3_direct_grouping=True)),
        ("+F4 corrected DayDelta triggers", fixes(F1_three_tier=True, F2_background_out=True,
                                                  F3_direct_grouping=True, F4_delta_fixed=True)),
        ("+F5 sphere no fan-out", fixes(F1_three_tier=True, F2_background_out=True,
                                        F3_direct_grouping=True, F4_delta_fixed=True,
                                        F5_sphere_no_fanout=True)),
        ("+F6 event_class=whitelist_timelord", fixes(F1_three_tier=True, F2_background_out=True,
                                                     F3_direct_grouping=True, F4_delta_fixed=True,
                                                     F5_sphere_no_fanout=True,
                                                     F6_event_class="whitelist_timelord")),
        ("+F7 orb fail-closed", fixes(F1_three_tier=True, F2_background_out=True,
                                      F3_direct_grouping=True, F4_delta_fixed=True,
                                      F5_sphere_no_fanout=True,
                                      F6_event_class="whitelist_timelord",
                                      F7_orb_fail_closed=True)),
        ("+F8 rare narrowed (all fixes)", dict(ALL_ON)),
    ]
    for name, fx in steps:
        chain.append((name, fx))
        chain_rows.append(state_stats(run_v2(fx)))

    # ---------- 2. 20-config sweep under the fully fixed model ----------
    sweep: list[dict] = []
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            rows = []
            for day in DAYS:
                r = H.classify_day_v2(day["factors"], tw, to, "B",
                                      fixes=ALL_ON, trigger_keys=triggers_of(day))
                rows.append({"date": day["date"], "result": r})
            st = state_stats(rows)
            st["name"] = f"w{tw}_o{to}_fixed_B"
            st["tense"] = tense_streaks(rows)
            sweep.append(st)
    # theta_p collapse check (D7): source-exclusion axis removed by F1
    collapse_rows = run_v2(ALL_ON)
    collapse = {tp: state_stats(collapse_rows)["hero"] for tp in ("any", "non_moon", "non_fast")}
    # rule A vs B
    rule_a = []
    for day in DAYS:
        r = H.classify_day_v2(day["factors"], C1_W, C1_O, "A",
                              fixes=ALL_ON, trigger_keys=triggers_of(day))
        rule_a.append({"date": day["date"], "result": r})
    rule_a_stats = state_stats(rule_a)
    # sanity V0 under fixed model
    sanity_rows = []
    for day in DAYS:
        facs = [
            f for f in day["factors"]
            if f["aspect_type"]
            and (f["source_planet"] or "").upper() in H.SLOW_SOURCES
            and (f["target_type"] or "") in ("natal_planet", "angle")
        ]
        r = H.classify_day_v2(facs, 0.85, 1.0, "B", fixes=ALL_ON,
                              trigger_keys=triggers_of(day))
        sanity_rows.append({"date": day["date"], "result": r})
    sanity_stats = state_stats(sanity_rows)

    # ---------- 3. F6 event_class options at C1 ----------
    f6_rows = {}
    for mode in ("auto", "whitelist_timelord", "strength_0.5", "strength_0.7"):
        fx = dict(ALL_ON, F6_event_class=mode)
        f6_rows[mode] = state_stats(run_v2(fx))

    # ---------- 4. F3 verification: star vs components (rest fixed) ----------
    f3_off = state_stats(run_v2(dict(ALL_ON, F3_direct_grouping=False)))
    f3_on = state_stats(run_v2(ALL_ON))

    # ---------- 5. sphere distribution before/after ----------
    v1_rows = run_v1_baseline()
    v2_rows = run_v2(ALL_ON)
    spheres_before = hero_sphere_counts(v1_rows, "v1")
    spheres_after = hero_sphere_counts(v2_rows, "v2")

    # ---------- 6. tense streaks on public units (fixed C1) ----------
    tense_fixed = tense_streaks(v2_rows)
    tense_baseline = tense_streaks(v1_rows)

    out = {
        "meta": {"c1": {"theta_w": C1_W, "theta_o": C1_O, "rule": "B"},
                 "fixes": ALL_ON, "n_days": len(DAYS)},
        "fix_chain": [{"step": name, **row} for (name, _), row in zip(chain, chain_rows)],
        "sweep_fixed": sweep,
        "theta_p_collapse_check": collapse,
        "rule_A_fixed": rule_a_stats,
        "sanity_V0_fixed": sanity_stats,
        "f6_options": f6_rows,
        "f3_verification": {"components": f3_off, "star": f3_on},
        "sphere_distribution": {"before_v1": dict(spheres_before),
                                "after_v2": dict(spheres_after)},
        "tense_streaks": {"baseline_v1": tense_baseline, "fixed_v2": tense_fixed},
        "c1_fixed_days": [
            {"date": r["date"], "state": r["result"]["state"],
             "n_significant": r["result"]["n_significant"],
             "n_anchors": r["result"]["n_anchors"],
             "delta_upgraded": r["result"]["delta_upgraded"],
             "hero_groups": [
                 {"spheres": g.get("spheres"), "n_independent": g["n_independent"],
                  "members": [
                      {"semantic_key": m["semantic_key"], "role": m["temporal_role"],
                       "driver": H.driver_of(m),
                       "orb_fraction": (round(m["orb_fraction"], 3)
                                        if m.get("orb_fraction") is not None else None),
                       "polarity": m["polarity"],
                       "rare_anchor": H.is_rare_anchor_eligible_v2(m, ALL_ON)}
                      for m in g["members"]]}
                 for g in r["result"]["hero_groups"]]}
            for r in v2_rows
        ],
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    write_report(out)
    print(f"json: {OUT_JSON}\nmd:   {OUT_MD}")
    for row in out["fix_chain"]:
        print(f"{row['step']:42s} hero={row['hero']:2d} conv={row['convergence']:2d} "
              f"single={row['single_impulse']:2d} med={row['med_sig']:.0f} p90={row['p90_sig']:.0f}")


# --------------------------------------------------------------------------
def write_report(out: dict) -> None:
    L: list[str] = []
    w = L.append
    fc = out["fix_chain"]
    base, final = fc[0], fc[-1]
    sw = {r["name"]: r for r in out["sweep_fixed"]}
    sp_b, sp_a = out["sphere_distribution"]["before_v1"], out["sphere_distribution"]["after_v2"]

    w("# Ablation v2 (master v1.5): исправленная пятислойная модель — ландшафт и C1\n")
    w("Данные: владелец (`basil_ivanov`), 81 день, `factor_dump_v2.json` (12817 факторов + "
      "скорректированные DayDelta-триггеры по семантической идентичности). Фиксы F1–F8 "
      "реализованы как флаги `FIXES` в `ablation_harness.py` (v1-функции не тронуты, "
      "v1-артефакты воспроизводимы). Точка C1: θ_w=0.55, θ_o=0.5, правило B.\n")

    w("## 1. Фикс-лист → before/after (кумулятивно, точка C1)\n")
    w("| шаг | hero/81 | conv | single | quiet_imp | quiet | med sig | p90 sig |")
    w("|---|---|---|---|---|---|---|---|")
    for r in fc:
        w(f"| {r['step']} | {r['hero']} | {r['convergence']} | {r['single_impulse']} | "
          f"{r['quiet_impulses']} | {r['quiet']} | {r['med_sig']:.0f} | {r['p90_sig']:.0f} |")
    w("")
    f4 = fc[4]
    w(f"Замеры по шагам: F1 возвращает быстрые источники в импульсы/свидетели "
      f"(med sig {fc[0]['med_sig']:.0f} → {fc[1]['med_sig']:.0f}/день). "
      f"F4 добавляет anchor_today: {f4['delta_upgraded_total']} апгрейдов роли за 81 день "
      f"(hero {fc[3]['hero']} → {f4['hero']}). "
      f"F7 исключает fail-closed: {final['excluded_orb_fail_closed_total']} юнитов "
      f"(SOLAR/PROGRESSED вне orb-профиля). F3 (star вместо components): hero "
      f"{out['f3_verification']['components']['hero']} → {out['f3_verification']['star']['hero']} "
      f"(проверка ревьюера «без изменений»).\n")

    w("## 2. Обновлённый ландшафт (все фиксы включены)\n")
    w("| config | hero | conv | single | quiet_imp | med sig | p90 | tense max/med |")
    w("|---|---|---|---|---|---|---|---|")
    for tw in (0.25, 0.30, 0.40, 0.55, 0.85):
        for to in (0.3, 0.5, 0.7, 1.0):
            r = sw[f"w{tw}_o{to}_fixed_B"]
            w(f"| {r['name']} | {r['hero']} | {r['convergence']} | {r['single_impulse']} | "
              f"{r['quiet_impulses']} | {r['med_sig']:.0f} | {r['p90_sig']:.0f} | "
              f"{r['tense']['max_streak']}/{r['tense']['median_streak']:.0f} |")
    w("")
    w(f"Коллапс оси θ_p (D7): hero при any/non_moon/non_fast = "
      f"{out['theta_p_collapse_check']} — после F1 ось исключения источников упразднена, "
      f"быстрые источники фильтруются только из rare_anchor-тира. "
      f"Правило A вместо B: hero {out['rule_A_fixed']['hero']} "
      f"(B: {final['hero']}). Sanity V0 (slow+major+planet/angle) под фиксированной "
      f"моделью: hero {out['sanity_V0_fixed']['hero']}/81 {out['sanity_V0_fixed']['hero_days']} "
      f"(v1 давал 4/81, ревьюер ≈9/81).\n")

    w("## 3. C1: baseline vs fixed\n")
    w("| метрика | baseline v1 | fixed v2 |")
    w("|---|---|---|")
    for label, key in (("hero/81", "hero"), ("convergence", "convergence"),
                       ("single_impulse", "single_impulse"), ("quiet_impulses", "quiet_impulses"),
                       ("med sig", "med_sig"), ("p90 sig", "p90_sig")):
        w(f"| {label} | {base[key]} | {final[key]} |")
    w(f"| hero-дни | {base['hero_days']} | {final['hero_days']} |")
    w("")

    w("## 4. F6: пороги event_class для не-аспектных юнитов (точка C1)\n")
    w("| режим | hero | conv | med sig | p90 sig |")
    w("|---|---|---|---|---|")
    for mode, r in out["f6_options"].items():
        w(f"| {mode} | {r['hero']} | {r['convergence']} | {r['med_sig']:.0f} | {r['p90_sig']:.0f} |")
    w("")

    w("## 5. Tense streaks на публичных юнитах\n")
    tb, tf = out["tense_streaks"]["baseline_v1"], out["tense_streaks"]["fixed_v2"]
    w(f"- baseline v1 (все единицы): tense-дней {tb['tense_days']}/81, max streak {tb['max_streak']}, "
      f"медиана streak {tb['median_streak']:.0f}.")
    w(f"- fixed v2 (только публичные значимые): tense-дней {tf['tense_days']}/81, "
      f"max streak {tf['max_streak']}, медиана streak {tf['median_streak']:.0f}, "
      f"серий {tf['n_streaks']}.\n")

    w("## 6. Распределение hero-групп по сферам: fan-out до/после\n")
    w("| сфера | v1 (per-sphere fan-out) | v2 (primary+secondary) |")
    w("|---|---|---|")
    for s in sorted(set(sp_b) | set(sp_a), key=lambda s: -(sp_b.get(s, 0) + sp_a.get(s, 0))):
        w(f"| {s} | {sp_b.get(s, 0)} | {sp_a.get(s, 0)} |")
    w("")
    tot_b, tot_a = sum(sp_b.values()), sum(sp_a.values())
    sh_b = sp_b.get("decisions", 0) / max(tot_b, 1)
    sh_a = sp_a.get("decisions", 0) / max(tot_a, 1)
    w(f"Доля `decisions`: {sh_b:.0%} → {sh_a:.0%}. Текущая планетная карта "
      "(PLANET_TO_PRODUCT_MAP) раздаёт `decisions` шести планетам из десяти: "
      "SUN [work, decisions], MARS [work, sport, decisions], JUPITER [work, money, decisions], "
      "SATURN [work, decisions, documents], URANUS [decisions, travel], PLUTO [decisions, work] — "
      "это и есть причина catch-all.\n")
    w("Предлагаемая ревизия карты (кандидат в канон W1, ≤2 сферы на планету, "
      "decisions только для «планет суждения»):\n")
    w("| планета | сейчас | предложение |")
    w("|---|---|---|")
    w("| SUN | work, decisions | work |")
    w("| MARS | work, sport, decisions | sport, work |")
    w("| VENUS | money, relationships, shopping | без изменений |")
    w("| MERCURY | documents, communication, study | без изменений |")
    w("| JUPITER | work, money, decisions | money, work |")
    w("| SATURN | work, decisions, documents | decisions, documents |")
    w("| MOON | relationships, health | без изменений |")
    w("| URANUS | decisions, travel | travel, creativity |")
    w("| NEPTUNE | creativity, health | без изменений |")
    w("| PLUTO | decisions, work | decisions |")
    w("")
    w("При такой карте decisions получают только SATURN и PLUTO; остальные сферы "
      "распределяются по профильным планетам. Числа выше (после F5) уже не fan-out'ятся "
      "по 3–4 сферам, но доля decisions останется высокой, пока карта не пересмотрена.\n")

    w("## 7. Оговорки\n")
    w("- F4 симулирует исправленный контракт DayDelta (sem-identity); прод-фикс — W2. "
      "Апгрейд роли возможен только для фактов, чей semantic_key формата aspect:*; "
      "time-lord активации триггерами не покрываются (их sem_key не signal-формата).")
    w("- F5 проецирует группу по большинству голосов членов; при равенстве — сфера якоря "
      "(канонический порядок), затем канонический порядок. Secondary требует ≥2 голосов.")
    w("- Консервативности: orb = max по контрольным временам (страты), anchor только если "
      "якорь везде — как в v1-стратах.")
    w("- Одна карта, один сезон.\n")

    OUT_MD.write_text("\n".join(L))


if __name__ == "__main__":
    main()
