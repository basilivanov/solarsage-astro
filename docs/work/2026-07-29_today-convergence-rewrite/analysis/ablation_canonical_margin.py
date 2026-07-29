#!/usr/bin/env python3
"""W1 addendum — canonical fixed orb-margin (master §4.7): margin_gap is a canon
constant (3h per bucket, 4h for unknown), NOT a function of the probing grid.

Recomputes, reusing existing dumps (no sidecar):
  1. Fixture 9 (main vs shifted 3-pt probes, byte-identical published sets)
     with BOTH probes using the canonical margin.
  2. Sparse-oracle gate with canonical margin on sparse and the bare rule
     (margin=0, i.e. dense-truth) on the oracle.
  3. Residual classification for fixture-9 diffs:
     (a) grid artifacts — fact IS oracle-robust (dense-stable at bare theta_o)
         but the two probes disagree (must be 0 after canonical margin);
     (b) genuinely range-sensitive — fact is NOT oracle-robust; legitimate
         time_sensitive. We verify whether it is consistently excluded in
         BOTH probes (no diff) or missed by one probe (diff, sampling miss —
         the production gate on the canonical grid still catches it).
  4. Strata frequencies sanity check (canonical gap == actual sparse gap, so
     production strata numbers must be unchanged).

Updates ablation_final_summary.json in place and appends a section to
ablation_sect_oracle.md. No DB, no sidecar, no LLM.
Run: apps/api/.venv/bin/python ablation_canonical_margin.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import ablation_sect_oracle as SO

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
SUMMARY_PATH = ANALYSIS / "ablation_final_summary.json"
MD_PATH = ANALYSIS / "ablation_sect_oracle.md"

BUCKETS = ["night", "morning", "day", "evening"]
CANON_GAP = {**{b: 3.0 for b in BUCKETS}, "unknown": 4.0}


def canon_public(dt: str, times: list[str], *, with_margin: bool) -> list[dict]:
    strat = "unknown" if len(times) > 4 or times == SO.SPARSE_GRIDS["unknown"] else None
    # derive stratum's canonical gap from the grid's home stratum
    return SO.public_factors(
        dt, times,
        max_gap_h=_canon_gap_for(times),
        margin_mode="speed_gap" if with_margin else "off",
        hard_exclude=True,
    )[0]


def _canon_gap_for(times: list[str]) -> float:
    for name, grid in SO.SPARSE_GRIDS.items():
        if times == grid:
            return CANON_GAP[name]
    for name, grid in SO.SHIFTED_GRIDS.items():
        if times == grid:
            return CANON_GAP[name]
    for name, grid in SO.ORACLE_GRIDS.items():
        if times == grid:
            return CANON_GAP[name]
    raise ValueError(f"unknown grid: {times}")


def oracle_robust_ids(dt: str, strat: str) -> set[str]:
    """Dense-truth robust set: presence + bare theta_o at all hourly points,
    geo-sect + hard rules applied (margin=0)."""
    pub = SO.public_factors(
        dt, SO.ORACLE_GRIDS[strat],
        max_gap_h=CANON_GAP[strat],  # ignored when margin off
        margin_mode="off",
        hard_exclude=True,
    )[0]
    return SO.published_ids(pub)


def main() -> None:
    # ---------- 1. fixture 9 with canonical margin on both probes ----------
    f9: dict[str, dict] = {}
    residual_a: dict[str, list] = {}   # grid artifacts (oracle-robust, probes disagree)
    residual_b_missed: dict[str, list] = {}  # range-sensitive, missed by ONE probe
    for b in BUCKETS:
        identical = differing = 0
        kinds: Counter = Counter()
        res_a, res_b = [], []
        for dt in SO.ALL_DATES:
            main_ids = SO.published_ids(canon_public(dt, SO.SPARSE_GRIDS[b], with_margin=True))
            shift_ids = SO.published_ids(canon_public(dt, SO.SHIFTED_GRIDS[b], with_margin=True))
            if main_ids == shift_ids:
                identical += 1
                continue
            differing += 1
            or_ids = oracle_robust_ids(dt, b)
            for x in sorted(main_ids ^ shift_ids):
                kinds["aspect" if "aspect:" in x else "non_aspect"] += 1
                sem = json.loads(x)[0]
                if x in or_ids:
                    res_a.append(f"{dt} {sem}")
                else:
                    res_b.append(f"{dt} {sem}")
        f9[b] = {"identical_days": identical, "differing_days": differing,
                 "pass": differing == 0, "diff_kinds": dict(kinds),
                 "residual_grid_artifacts": len(res_a),
                 "residual_range_sensitive_missed_by_one_probe": len(res_b)}
        residual_a[b] = res_a[:8]
        residual_b_missed[b] = res_b[:8]

    # ---------- 2. gate with canonical margin on sparse, bare rule on oracle ----------
    gate: dict[str, dict] = {}
    for name in BUCKETS + ["unknown"]:
        violations = 0
        examples: list[str] = []
        for dt in SO.ALL_DATES:
            sp_ids = SO.published_ids(canon_public(dt, SO.SPARSE_GRIDS[name], with_margin=True))
            or_ids = oracle_robust_ids(dt, name)
            diff = sp_ids - or_ids
            violations += len(diff)
            examples.extend(f"{dt} {json.loads(x)[0]}" for x in sorted(diff)[:3])
        gate[name] = {"violations": violations, "examples": examples[:6]}

    # ---------- 3. strata sanity: canonical gap == actual sparse gap ----------
    strata_check: dict[str, dict] = {}
    for name in BUCKETS + ["unknown"]:
        changed = 0
        for dt in SO.ALL_DATES:
            old_ids = SO.published_ids(SO.public_factors(
                dt, SO.SPARSE_GRIDS[name],
                max_gap_h=SO.MAX_GAP["sparse"][name],
                margin_mode="speed_gap", hard_exclude=True)[0])
            new_ids = SO.published_ids(canon_public(dt, SO.SPARSE_GRIDS[name], with_margin=True))
            if old_ids != new_ids:
                changed += 1
        strata_check[name] = {"days_with_changed_public_set": changed}

    # ---------- 4. update summary json ----------
    summary = json.loads(SUMMARY_PATH.read_text())
    summary["config"]["orb_margin"] = (
        "CANONICAL FIXED: speed(target_planet) * canonical_gap / canon_max_orb(source); "
        "canonical_gap = 3h (every bucket) / 4h (unknown), independent of probing grid"
    )
    summary["gate"] = {
        "status": "pass" if sum(v["violations"] for v in gate.values()) == 0 else "fail",
        "margin_rule": "sparse: canonical margin; oracle: bare theta_o (dense truth)",
        "violations_total": sum(v["violations"] for v in gate.values()),
        "per_stratum": {k: v["violations"] for k, v in gate.items()},
        "examples": {k: v["examples"] for k, v in gate.items() if v["violations"]},
    }
    summary["fixtures"]["9_shifted_sample_invariance"] = {
        b: ("pass" if r["pass"] else f"fail({r['differing_days']}d)") for b, r in f9.items()
    }
    summary["fixtures"]["9_detail"] = f9
    summary["fixtures"]["9_residual_samples"] = {
        "grid_artifacts": residual_a, "range_sensitive_missed": residual_b_missed,
    }
    summary["strata_margin_canonicalization_check"] = strata_check
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=1))

    # ---------- 5. append MD section ----------
    L: list[str] = []
    w = L.append
    w("\n## 6. Каноническая фиксированная маржа (§4.7) — fixture 9 и gate заново\n")
    w("Правило заменено: margin = speed(target) × CANONICAL_GAP / canon_max_orb(source), "
      "CANONICAL_GAP = 3ч для любого бакета, 4ч для unknown — константа канона, не функция "
      "сетки пробования. Gate пересчитан в семантике «sparse с канонической маржой ⊆ "
      "oracle с голым θ_o (dense-truth)»: маржа живёт в правиле публикации (доказательство "
      "устойчивости по всему диапазону), oracle проверяет фактическую истину на почасовой сетке.\n")
    w("| бакет | identical/81 | differing | grid artifacts (a) | range-sensitive missed (b) |")
    w("|---|---|---|---|---|")
    for b in BUCKETS:
        r = f9[b]
        w(f"| {b} | {r['identical_days']} | {r['differing_days']} | "
          f"{r['residual_grid_artifacts']} | {r['residual_range_sensitive_missed_by_one_probe']} |")
    w("")
    w(f"Gate: {summary['gate']['status'].upper()} "
      f"(violations total = {summary['gate']['violations_total']}, "
      f"per stratum = {summary['gate']['per_stratum']}).")
    w("Санити страт: канонический gap совпадает с фактическим gap продовой sparse-сетки "
      f"(3ч/4ч), поэтому продовые частоты страт не изменились: "
      f"{json.dumps({k: v['days_with_changed_public_set'] for k, v in strata_check.items()})} "
      "(дней с изменившимся публичным набором).\n")
    w("Классификация резидуалов fixture 9:\n")
    w("- **(a) grid artifacts** — факт oracle-робастен (устойчив на почасовой сетке при голом "
      "θ_o), но пробы разошлись: после канонической маржи таких быть не должно; фактическое "
      "число — в таблице. Механизм ненулевого остатка: маржа — достаточный (консервативный) "
      "тест; в полосе (θ_o − m, θ_o] вердикт зависит от того, попала ли точка пробы в "
      "область максимума кривой орба.")
    w("- **(b) genuinely range-sensitive** — факт НЕ oracle-робастен (флип внутри диапазона, "
      "напр. monthly profection у границы 05:00→05:59 в night). Легитимный time_sensitive: "
      "на канонической продовой сетке (с точкой 05:59) исключается всегда; сдвинутая проба "
      "может пропустить флип (последняя точка 05:00) — это дефект произвольной пробы, "
      "а не канонической сетки; production-gate его ловит.\n")

    with MD_PATH.open("a") as fh:
        fh.write("\n".join(L))

    print(json.dumps({
        "fixture9": {b: {k: v for k, v in r.items() if k != "diff_kinds"} for b, r in f9.items()},
        "gate": summary["gate"]["status"],
        "strata_check": strata_check,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
