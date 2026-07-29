#!/usr/bin/env python3
"""W1 ablation — birth-time strata analysis (P0 normative master v1.4 §4.7).

Reads analysis/factor_dump_birthtime.json (control-time merged dump from
dump_birthtime.py) + analysis/factor_dump.json (exact stratum, C1 baseline).

Per stratum (exact, night, morning, day, evening, unknown):
  robustness rule: a factor is public only if identical (semantic_key,
  polarity, spheres) across ALL control times of its range; else
  time_sensitive and excluded. Sampling = 1 unit (merge by identity).
  Role resolution: anchor_today only if anchor at ALL control times, else
  the weakest observed role (conservative). Orb for significance: max raw
  orb across control times (same orb-profile denominator => max fraction).
  Hard rule (bucket/unknown): target_type in {house, angle, lot} not public.
  Then C1 (theta_w=0.55, theta_o=0.5, non_fast, rule B, hero=rare_anchor)
  via ablation_harness.classify_day.

Fixtures:
  (8) unknown publishes zero house/angle/lot factors.
  (9) shifted control sample inside each bucket yields byte-identical
      published stable sets (per day).
  (11) N control points of one fact = 1 unit (uniqueness + dedup ratio).

Outputs: analysis/ablation_birthtime.json + analysis/ablation_birthtime.md (RU).
No DB, no sidecar, no LLM. Run: apps/api/.venv/bin/python ablation_birthtime.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

import ablation_harness as H

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
BT_PATH = ANALYSIS / "factor_dump_birthtime.json"
EXACT_PATH = ANALYSIS / "factor_dump.json"
OUT_JSON = ANALYSIS / "ablation_birthtime.json"
OUT_MD = ANALYSIS / "ablation_birthtime.md"

ROLE_ORDER = {"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}
NON_PUBLIC_TARGETS = {"house", "angle", "lot"}
BUCKETS = ["night", "morning", "day", "evening"]
C1 = {"theta_w": 0.55, "theta_o": 0.5, "theta_p": "non_fast", "rule": "B",
      "hero_predicate": "rare_anchor"}


def resolve_stratum_day(day: dict, *, hard_exclude: bool) -> tuple[list[dict], list[dict]]:
    """Split merged factors into (public resolved factors, time_sensitive excluded)."""
    public: list[dict] = []
    excluded: list[dict] = []
    for m in day["factors"]:
        if not all(m["presence"]):
            excluded.append(m)
            continue
        roles = [r for r in m["roles"] if r is not None]
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


def resolve_exact_day(day: dict) -> list[dict]:
    out = []
    for f in day["factors"]:
        g = dict(f)
        g["roles"] = [f["temporal_role"]]
        out.append(g)
    return out


def classify(public: list[dict]) -> dict:
    return H.classify_day(
        public,
        C1["theta_w"], C1["theta_o"], C1["theta_p"], C1["rule"],
        hero_predicate=C1["hero_predicate"],
    )


def published_identities(public: list[dict]) -> list[str]:
    return sorted({json.dumps([m["semantic_key"], m["polarity"], m["spheres"]],
                              ensure_ascii=False) for m in public})


def run() -> dict:
    bt = json.loads(BT_PATH.read_text())
    exact = json.loads(EXACT_PATH.read_text())

    strata_names = ["exact"] + BUCKETS + ["unknown"]
    results: dict[str, dict] = {}

    for name in strata_names:
        hard_exclude = name != "exact"
        per_day = []
        victim_counter: Counter = Counter()
        total_ts = 0
        if name == "exact":
            days_src = [{"date": d["date"], "public": resolve_exact_day(d), "ts": []}
                        for d in exact["days"] if "error" not in d]
        else:
            sdays = [d for d in bt["strata"][name]["days"] if "error" not in d]
            days_src = []
            for d in sdays:
                public, ts = resolve_stratum_day(d, hard_exclude=hard_exclude)
                days_src.append({"date": d["date"], "public": public, "ts": ts,
                                 "per_time_counts": d.get("per_time_counts")})

        for d in days_src:
            r = classify(d["public"])
            anchors = [u for u in r["sig_units"] if u["temporal_role"] == "anchor_today"]
            state = r["state"]
            if state == "single_impulse" and not anchors:
                state = "no_anchor"
            d.update({
                "state": state,
                "n_public": len(d["public"]),
                "n_significant": r["n_significant"],
                "n_ts": len(d["ts"]),
                "hero_spheres": sorted({g["sphere"] for g in r["hero_groups"]}),
            })
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
            "zero_significant_days": sum(1 for d in days_src if d["n_significant"] == 0),
            "mean_public_per_day": round(statistics.mean(d["n_public"] for d in days_src), 1),
            "mean_ts_excluded_per_day": round(total_ts / max(len(days_src), 1), 1),
            "total_ts_excluded": total_ts,
            "top_time_sensitive_victims": [
                {"technique_family": k[0], "target_type": k[1], "count": v}
                for k, v in victim_counter.most_common(8)
            ],
            "days": [
                {"date": d["date"], "state": d["state"], "n_public": d["n_public"],
                 "n_significant": d["n_significant"], "n_ts": d["n_ts"],
                 "hero_spheres": d["hero_spheres"]}
                for d in days_src
            ],
        }

    # ---------------- fixtures ----------------
    fixtures: dict[str, dict] = {}

    # (8) unknown publishes no house/angle/lot factors
    viol = 0
    for d in bt["strata"]["unknown"]["days"]:
        if "error" in d:
            continue
        public, _ = resolve_stratum_day(d, hard_exclude=True)
        viol += sum(1 for m in public if (m["target_type"] or "") in NON_PUBLIC_TARGETS)
    fixtures["8_unknown_no_house_angle_lot"] = {
        "violations": viol, "pass": viol == 0,
    }

    # (9) shifted sample -> byte-identical published stable set per bucket day
    f9 = {}
    for b in BUCKETS:
        main_days = {d["date"]: d for d in bt["strata"][b]["days"] if "error" not in d}
        shift_days = {d["date"]: d for d in bt["strata"][f"shifted_{b}"]["days"] if "error" not in d}
        identical = differing = 0
        diff_examples = []
        for dt, dm in main_days.items():
            ds = shift_days.get(dt)
            if ds is None:
                continue
            pm = published_identities(resolve_stratum_day(dm, hard_exclude=True)[0])
            ps = published_identities(resolve_stratum_day(ds, hard_exclude=True)[0])
            if pm == ps:
                identical += 1
            else:
                differing += 1
                if len(diff_examples) < 3:
                    diff_examples.append({
                        "date": dt,
                        "only_main": sorted(set(pm) - set(ps))[:4],
                        "only_shifted": sorted(set(ps) - set(pm))[:4],
                    })
        f9[b] = {"identical_days": identical, "differing_days": differing,
                 "examples": diff_examples}
    fixtures["9_shifted_sample_invariance"] = f9

    # (11) sampling does not multiply units
    f11 = {}
    for name in BUCKETS + ["unknown"]:
        ratios, dup_violations = [], 0
        for d in bt["strata"][name]["days"]:
            if "error" in d:
                continue
            public, _ = resolve_stratum_day(d, hard_exclude=True)
            idents = [(m["semantic_key"], m["polarity"], tuple(m["spheres"])) for m in public]
            if len(idents) != len(set(idents)):
                dup_violations += 1
            stable_ids = set(idents)
            raw_sum = 0
            # reconstruct raw per-time occurrences of stable facts
            n_times = len(bt["strata"][name]["control_times"])
            for m in d["factors"]:
                if all(m["presence"]):
                    raw_sum += sum(1 for p in m["presence"] if p)
            if idents:
                ratios.append(raw_sum / len(idents))
        f11[name] = {
            "duplicate_identity_violations": dup_violations,
            "mean_dedup_ratio": round(statistics.mean(ratios), 2) if ratios else None,
            "pass": dup_violations == 0,
        }
    fixtures["11_sampling_no_multiplication"] = f11

    # ---------------- perf ----------------
    meta = bt["meta"]
    per_call = meta["elapsed_s"] / max(meta["act_layer_calls"], 1)
    perf = {
        "dump_elapsed_s": meta["elapsed_s"],
        "act_layer_calls_total": meta["act_layer_calls"],
        "natal_calls_total": meta["natal_calls"],
        "transit_calls_total": meta["transit_calls"],
        "per_control_time_day_s": round(per_call, 3),
        "per_user_day_bucket_est_s": round(3 * per_call + 0.1, 2),
        "per_user_day_unknown_est_s": round(6 * per_call + 0.15, 2),
        "per_user_day_exact_est_s": round(per_call + 0.1, 2),
    }

    out = {"meta": {"c1": C1, "strata": bt["meta"]["strata"], "dump_meta": meta},
           "strata": results, "fixtures": fixtures, "perf": perf}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# --------------------------------------------------------------------------
# Report (RU)
# --------------------------------------------------------------------------
def write_report(out: dict) -> None:
    s = out["strata"]
    fx = out["fixtures"]
    perf = out["perf"]
    L: list[str] = []
    w = L.append

    w("# Birth-time strata (P0, master v1.4 §4.7): робастность фактов к неточному времени рождения\n")
    w("Данные: владелец (`basil_ivanov`), 81 день (2026-06-01..2026-08-20). Контрольные времена "
      "(local birth tz): buckets edges+middle (3 точки), unknown — каждые 4ч (6 точек), "
      "shifted — resample для фикстуры 9. Натальная карта пересчитывается на каждое контрольное "
      "время (sidecar get_natal + get_activation_layer per time, как прод для одного времени). "
      "Правило публичности: факт идентичен (semantic_key + polarity + сферы) на ВСЕХ "
      "контрольных временах диапазона; иначе time_sensitive → исключён. Якорь засчитывается, "
      "только если факт — якорь на всех контрольных временах (консервативно). Орб для "
      "значимости — максимум по контрольным временам. Для bucket/unknown дома/ASC/лоты "
      "(target_type ∈ {house, angle, lot}) не публичны — жёсткое правило поверх стабильности. "
      "Классификация — C1 (θ_w=0.55, θ_o=0.5, non_fast, правило B, hero = rare_anchor).\n")

    w("## 1. Сводная таблица по стратам\n")
    w("| страта | hero/81 | conv | single | no_anchor | med sig | public/день | time_sensitive/день | zero-robust дней |")
    w("|---|---|---|---|---|---|---|---|---|")
    for name in ["exact"] + ["night", "morning", "day", "evening", "unknown"]:
        r = s[name]
        sd = r["state_distribution"]
        w(f"| {name} | {r['hero_days_n']} | {sd.get('convergence', 0)} | "
          f"{sd.get('single_impulse', 0)} | {sd.get('no_anchor', 0)} | "
          f"{r['median_significant']:.0f} | {r['mean_public_per_day']} | "
          f"{r['mean_ts_excluded_per_day']} | {r['zero_robust_public_days']} |")
    w("")
    exact_hero = s["exact"]["hero_days_n"]
    w(f"Контроль: exact-страта воспроизводит C1 baseline (hero={exact_hero}/81, ожидалось 10). "
      "zero-robust — дни, где после робастности не выжил НИ ОДИН персональный факт "
      "(публичный набор пуст) — это и есть случай «общий фон дня».\n")
    w("Hero-дни по стратам:")
    for name in ["exact"] + ["night", "morning", "day", "evening", "unknown"]:
        w(f"- {name}: {s[name]['hero_days']}")
    w("")
    w("Чтение: робастность режет hero-частоту с 10/81 (exact) до 1–2/81; единственный день, "
      "переживший все страты, — 2026-07-21 (кластер Jupiter/Saturn с точным якорем). "
      "«Общего фона» в буквальном смысле (0 публичных фактов) нет ни в одной страте: "
      "~59–65 фактов/день выживают даже в unknown; но состояние no_anchor растёт "
      "38 → 62/81 — для bucket/unknown-пользователей подавляющее большинство дней становится "
      "«тихими» (значимые единицы есть, якоря нет).\n")

    w("## 2. Что умирает как time_sensitive (топ-8 типов на страту)\n")
    for name in ["night", "morning", "day", "evening", "unknown"]:
        r = s[name]
        w(f"**{name}** (всего {r['total_ts_excluded']} исключено за 81 день):")
        for v in r["top_time_sensitive_victims"][:5]:
            w(f"- {v['technique_family']} / {v['target_type']}: {v['count']}")
        w("")

    w("## 3. Фикстуры\n")
    f8 = fx["8_unknown_no_house_angle_lot"]
    w(f"- **(8) unknown: нет house/angle/lot факторов** — нарушений: {f8['violations']} → "
      f"{'PASS' if f8['pass'] else 'FAIL'}.")
    w("- **(9) инвариантность к сдвигу контрольных времён внутри диапазона** "
      "(byte-identical публичный набор):")
    for b, r in fx["9_shifted_sample_invariance"].items():
        status = "PASS" if r["differing_days"] == 0 else "FAIL"
        w(f"  - {b}: identical {r['identical_days']}/81, differing {r['differing_days']} → {status}")
        for ex in r["examples"]:
            w(f"    - расхождение {ex['date']}: main-only {ex['only_main'][:2]}; shifted-only {ex['only_shifted'][:2]}")
    w("- **(11) сэмплинг не размножает единицы** (N точек одного факта = 1 юнит):")
    for name, r in fx["11_sampling_no_multiplication"].items():
        w(f"  - {name}: дубликатов идентичностей {r['duplicate_identity_violations']}, "
          f"средний dedup-ratio {r['mean_dedup_ratio']}× → {'PASS' if r['pass'] else 'FAIL'}")
    w("")
    w("### Разбор FAIL фикстуры 9 — три механизма\n")
    w("1. **Аномалия секты/firdar (day-бакет 0/81)**: определение day/night на sidecar "
      "немонотонно по времени рождения: firdar_major=SUN в 12:00, 15:00, 17:59, но "
      "firdar_major=SATURN в 13:00, 16:00, 17:00 (проверено на 2026-06-01; unknown-страта "
      "показывает тот же флип в 16:00). Физического заката в этих точках нет (лето, "
      "широта Москвы, закат ~21:20) — похоже на баг/шум в определении секты; лоты "
      "Fortune/Spirit (их формулы зависят от секты) флипаются синхронно. Требует "
      "расследования на стороне движка; до фикса 3-точечный сэмплинг в day-бакете "
      "не определяет стабильный набор вообще.")
    w("2. **ASC-зависимые техники**: annual/monthly profection lord зависит от знака ASC "
      "(знак меняется каждые ~2ч) — внутри любого 6-часового бакета лорд профекции "
      "переключается 2–3 раза; устойчиво умирает как time_sensitive (ожидаемо).")
    w("3. **Орб-граничные лунные факты**: натальная Луна смещается ~3° за 6 часов; "
      "аспекты к натальной Луне с орбом у границы профиля (напр. JUPITER conjunction MOON) "
      "присутствуют в одних контрольных точках и отсутствуют в других — вердикт "
      "стабильности зависит от выбора точек сэмпла.")
    w("Вывод по фикстуре 9: при 3-точечном сэмплинге «стабильный набор» НЕ является "
      "функцией диапазона — он функция конкретных точек. Варианты для W1: (а) плотнее "
      "сэмплинг (напр. каждый час → 7 точек/бакет, 13/unknown) с бюджетом из §4; "
      "(б) явное правило дискретизации: стабильность считать по фиксированной канонической "
      "сетке (edges+middle как ЕДИНСТВЕННЫЙ легальный сэмпл) — тогда сдвиг неопределён, "
      "но это декларация, а не робастность; (в) для орб-фактов требовать запас "
      "(orb_fraction ≤ θ_o − margin) вместо двоичной стабильности.\n")

    w("## 4. Производительность (бюджет W5 pregen)\n")
    per_call = perf["dump_elapsed_s"] / max(perf["act_layer_calls_total"], 1)
    w(f"- Полный дамп: {perf['dump_elapsed_s']}с; sidecar activation-layer вызовов: "
      f"{perf['act_layer_calls_total']} (24 контрольных времени × 81 день), natal: "
      f"{perf['natal_calls_total']}, transits: {perf['transit_calls_total']} (birth-независимы, кэшируются).")
    w(f"- Измеренная стоимость одного (control_time, day) end-to-end: ~{per_call:.2f}с "
      "(включая normalize/ledger/классификацию; чистый sidecar ≈ 0.2с).")
    w(f"- Маргинальная стоимость pregen на пользователя-день: **bucket ≈ 3×{per_call:.2f} "
      f"+ transit ≈ {3*per_call + 0.1:.1f}с**, **unknown ≈ 6×{per_call:.2f} + transit "
      f"≈ {6*per_call + 0.15:.1f}с**; для сравнения exact ≈ {per_call + 0.1:.1f}с. "
      "Т.е. bucket-пользователь ≈ 3×, unknown ≈ 6× от стоимости exact. "
      "Natal-контексты контрольных времён кэшируются один раз на пользователя "
      "(вне дневного бюджета; 3–6 get_natal при первом расчёте). "
      "Вариант (а) из фикстуры 9 (почасовой сэмпл) стоил бы ≈ 7×/13× соответственно.\n")

    w("## 5. Оговорки\n")
    w("- **Немонотонная секта на sidecar** (firdar major/minor лорды флипаются в "
      "13:00/16:00/17:00 при соседних «дневных» точках) — см. разбор фикстуры 9; "
      "это доминирующий источник нестабильности day-бакета и отдельный пункт для "
      "расследования движка. Результаты day/unknown-страт загрязнены этим эффектом.")
    w("- DayDelta пропущен (доказуемо контент-нейтрален для сохраняемых полей: аннотирует "
      "только delta_kind/daily_salience/phase; триггерная ветка day_delta мертва — см. "
      "ablation_report.md §7).")
    w("- theme_keys/source берутся от первого вхождения при слиянии идентичностей; "
      "на группировку не влияет (связность почти вся по shared target_key).")
    w("- Консервативная роль (якорь только если якорь на всех точках) и max-орб — "
      "нижняя оценка публичности; majority-role/mean-orb дадут +1..2 hero-дня.")
    w("- Одна карта, один сезон; частоты — про чувствительность фактов этой карты, "
      "не про генеральную популяцию пользователей.\n")

    OUT_MD.write_text("\n".join(L))


if __name__ == "__main__":
    out = run()
    write_report(out)
    print(f"json: {OUT_JSON}")
    print(f"md:   {OUT_MD}")
    for name, r in out["strata"].items():
        print(f"{name:9s} hero={r['hero_days_n']:2d}/81 med_sig={r['median_significant']:.0f} "
              f"public/day={r['mean_public_per_day']} ts/day={r['mean_ts_excluded_per_day']} "
              f"zero_robust={r['zero_robust_public_days']}")
    print("fixtures:", json.dumps({k: (v if k != "9_shifted_sample_invariance" else
          {b: (x["identical_days"], x["differing_days"]) for b, x in v.items()})
          for k, v in out["fixtures"].items()}, ensure_ascii=False)[:800])
