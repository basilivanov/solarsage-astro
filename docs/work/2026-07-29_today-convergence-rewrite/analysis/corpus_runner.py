#!/usr/bin/env python3
"""W1 corpus runner — parallel replay over synthetic charts (diagnostic only).

Design (per owner redirect):
  - Work unit: (chart, mode, date). Checkpoints at CHART-DAY granularity
    (atomic tmp+rename), so a kill loses at most the in-flight chart-day.
    Resume skips existing ok checkpoints; error checkpoints are retried.
  - Deterministic sharding: charts sorted by chart_id, worker i takes
    charts with index % workers == i.
  - Per-worker process: one keep-alive httpx client to the sidecar
    (default the FIXED sidecar on 127.0.0.1:18099; 18091 is never touched).
  - Day pipeline per (chart, control_time, date) mirrors dump_birthtime_v2:
    sidecar /v1/natal (cached per chart+time) -> /v1/transits (cached per
    date+tz across charts) -> normalize_day (local, apps/api) -> DayDelta ->
    filter_day_scored_signals -> /v1/activation-layer -> build_factor_ledger
    -> normalize_factors -> merged control-time publicity (canonical orb
    margin 3h/4h, geometric sect from sidecar firdar debug altitude, hard
    rule no house/angle/lot for bucket/unknown) -> classify_day_v2 (all
    v1.5+T1 fixes incl. hero_confirmation/hero_target_types).
  - Failure log: run_dir/failures.jsonl, one JSON line per failed chart-day.
  - Aggregation (subcommand aggregate): state distribution, hero rate,
    impulse counts, tense streaks on SELECTED (public significant) units,
    hero sphere distribution, latency stats.

Run:  apps/api/.venv/bin/python corpus_runner.py run --charts a,b --from D --to D \
        --workers 4 --run-dir RUN_DIR
      apps/api/.venv/bin/python corpus_runner.py aggregate --run-dir RUN_DIR
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import date, timedelta
from multiprocessing import Pool
from pathlib import Path

ANALYSIS = Path("/opt/solarsage-astro/docs/work/2026-07-29_today-convergence-rewrite/analysis")
sys.path.insert(0, str(ANALYSIS))
sys.path.insert(0, "/opt/solarsage-astro/apps/api")

import ablation_harness as H  # noqa: E402

BUCKET_GRIDS = {
    "night": ["00:00", "03:00", "05:59"],
    "morning": ["06:00", "09:00", "11:59"],
    "day": ["12:00", "15:00", "17:59"],
    "evening": ["18:00", "21:00", "23:59"],
}
UNKNOWN_GRID = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"]
CANON_GAP = {"bucket": 3.0, "unknown": 4.0}
NON_PUBLIC_TARGETS = {"house", "angle", "lot"}
ROLE_ORDER = {"anchor_today": 0, "supporting": 1, "background": 2, "unrelated": 3}
SPEED_DEG_H = {
    "MOON": 0.55, "MERCURY": 0.059, "VENUS": 0.049, "SUN": 0.041,
    "MARS": 0.026, "JUPITER": 0.010, "SATURN": 0.0050, "URANUS": 0.0017,
    "NEPTUNE": 0.0014, "PLUTO": 0.0010,
}
ALL_ON = dict(H.FIXES)


# ---------------------------------------------------------------------------
# Worker-side day pipeline (per-process caches + one sidecar client)
# ---------------------------------------------------------------------------
class Worker:
    def __init__(self, sidecar_url: str) -> None:
        import httpx

        self.http = httpx.Client(base_url=sidecar_url, timeout=120.0)
        self.natal_cache: dict[str, dict] = {}
        self.transits_cache: dict[tuple[str, str], dict] = {}
        self.signals_cache: dict[tuple[str, str], list] = {}
        self.timings: Counter = Counter()
        self.call_counts: Counter = Counter()
        self._norm = None
        self._setup_api()

    def _setup_api(self) -> None:
        from app.services.normalization_service import NormalizationService

        self._norm = NormalizationService()

    def _post(self, path: str, payload: dict, kind: str) -> dict:
        t0 = time.monotonic()
        r = self.http.post(path, json=payload)
        r.raise_for_status()
        self.timings[kind] += time.monotonic() - t0
        self.call_counts[kind] += 1
        return r.json()

    def natal(self, chart: dict, birth_time: str) -> dict:
        key = f"{chart['chart_id']}|{birth_time}"
        if key not in self.natal_cache:
            resp = self._post("/v1/natal", {
                "birth_date": chart["birth_date"],
                "birth_time": birth_time,
                "birth_lat": chart["birth_lat"],
                "birth_lon": chart["birth_lon"],
                "birth_tz": chart["birth_tz"],
                "house_system": chart.get("house_system", "PLACIDUS"),
            }, "natal_ms")
            self.natal_cache[key] = resp
        return self.natal_cache[key]

    def transits(self, d: date, tz: str) -> dict:
        key = (d.isoformat(), tz)
        if key not in self.transits_cache:
            self.transits_cache[key] = self._post("/v1/transits", {
                "target_date": key[0], "target_time": "12:00", "target_tz": tz,
            }, "transits_ms")
        return self.transits_cache[key]

    def activation_layer(self, chart: dict, birth_time: str, d: date) -> dict:
        payload = {
            "birth": {
                "date": chart["birth_date"], "time": birth_time,
                "lat": chart["birth_lat"], "lon": chart["birth_lon"],
                "tz": chart["birth_tz"],
            },
            "target": {"date": d.isoformat(), "time": "12:00", "tz": chart.get("current_tz") or chart["birth_tz"]},
            "house_system": chart.get("house_system", "PLACIDUS"),
        }
        if chart.get("current_lat") is not None and chart.get("current_lon") is not None and chart.get("current_tz"):
            payload["current_location"] = {
                "lat": chart["current_lat"], "lon": chart["current_lon"], "tz": chart["current_tz"],
            }
        return self._post("/v1/activation-layer", payload, "act_layer_ms")

    def signals(self, natal_ctx: dict, d: date, tz: str) -> list:
        key = (f"{id(natal_ctx)}", d.isoformat())
        if key not in self.signals_cache:
            self.signals_cache[key] = self._norm.normalize_day(natal_ctx, self.transits(d, tz))
        return self.signals_cache[key]

    def day_factors(self, chart: dict, natal_ctx: dict, birth_time: str, d: date) -> tuple[list[dict], set[str], float | None]:
        """Factor records + corrected delta triggers + sun altitude (sect) for one control time/day."""
        from app.services.day_delta_service import DayDeltaService
        from app.services.day_factor_ledger import build_factor_ledger
        from app.services.day_scoring_signals import filter_day_scored_signals
        from app.services.today_focus_builder import normalize_factors
        from dump_factors import act_sem_key, signal_sem_key, strict_product_spheres

        tz = chart.get("current_tz") or chart["birth_tz"]
        t0 = time.monotonic()
        signals_raw = self.signals(natal_ctx, d, tz)
        try:
            y_signals = self.signals(natal_ctx, d - timedelta(days=1), tz)
            signals = DayDeltaService(y_signals, signals_raw).compute_deltas()
        except Exception:
            signals = signals_raw
        day_signals = filter_day_scored_signals(signals)
        sig_orb = {}
        for s in day_signals:
            k = signal_sem_key(s)
            if k:
                sig_orb.setdefault(k, getattr(s, "orb", None))
        trig = {
            k for s in signals
            if getattr(s, "delta_kind", None) in ("new_today", "peak_today")
            for k in [signal_sem_key(s)]
            if k
        }

        layer = self.activation_layer(chart, birth_time, d)
        acts = layer.get("activations") or layer.get("activationLayer", {}).get("activations") or []
        sun_alt = None
        for a in acts:
            dbg = a.get("debug") or {}
            if a.get("technique") == "firdar_major" and dbg.get("sun_altitude_deg") is not None:
                sun_alt = float(dbg["sun_altitude_deg"])
                break

        ledger = build_factor_ledger(day_signals, acts)
        ledger_by_id = {f.factor_id: f for f in ledger.factors}
        acts_by_sem: dict[str, list] = {}
        acts_by_id: dict[str, object] = {}
        for act in acts:
            act_id = act.get("id") or act.get("activation_id") or act.get("activationId")
            if act_id:
                acts_by_id[str(act_id)] = act
            sem = act_sem_key(act)
            if sem:
                acts_by_sem.setdefault(sem, []).append(act)

        class _Layer:
            activations = acts

        today_factors = normalize_factors(
            ledger=ledger, activation_layer=_Layer(), day_delta=None,
            target_date=d, tz_info=tz,
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
                orb = matched[0].get("orb")
            if orb is None and sig_orb.get(sem_key) is not None:
                orb = sig_orb[sem_key]
            recs.append({
                "semantic_key": sem_key,
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
                "spheres": strict_product_spheres(lf.technical_spheres if lf else [], f.source_key, f.target_key),
            })
        self.timings["pipeline_local_ms"] += time.monotonic() - t0
        return recs, trig, sun_alt


# ---------------------------------------------------------------------------
# Control-time merge + publicity (canonical margin, geo-sect, hard rule)
# ---------------------------------------------------------------------------
def merge_public(per_time: list[tuple[list[dict], set[str], float | None]], *,
                 gap_h: float, hard_exclude: bool) -> tuple[list[dict], int]:
    times_n = len(per_time)
    sect_flags = [alt is not None and alt > 0.0 for _r, _t, alt in per_time]
    sect_stable = all(f == sect_flags[0] for f in sect_flags) if per_time else True

    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for ti, (recs, _trig, _alt) in enumerate(per_time):
        for r in recs:
            ident = (r["semantic_key"], r["polarity"], tuple(r["spheres"]))
            if ident not in merged:
                m = {k: v for k, v in r.items() if k not in ("temporal_role", "orb", "strength")}
                m["presence"] = [False] * times_n
                m["roles"] = [None] * times_n
                m["orbs"] = [None] * times_n
                m["strengths"] = [None] * times_n
                merged[ident] = m
                order.append(ident)
            m = merged[ident]
            m["presence"][ti] = True
            m["roles"][ti] = r["temporal_role"]
            m["orbs"][ti] = r["orb"]
            m["strengths"][ti] = r["strength"]

    public: list[dict] = []
    n_ts = 0
    for ident in order:
        m = merged[ident]
        if not all(m["presence"]):
            n_ts += 1
            continue
        if not sect_stable and (m["technique_family"] or "").lower() == "firdar":
            n_ts += 1
            continue
        aspect = (m["aspect_type"] or "").upper() or None
        if aspect is not None and gap_h > 0.0:
            src = (m["source_planet"] or "").upper()
            denom = H.ORB_PROFILE.get(src)
            if denom is None:
                n_ts += 1
                continue
            ratios = [(o / denom) if o is not None else None for o in m["orbs"]]
            margin = SPEED_DEG_H.get((m["target_key"] or "").upper(), 0.55) * gap_h / denom
            if any(r is None for r in ratios) or max(ratios) + margin > 0.5:
                n_ts += 1
                continue
        roles = []
        for i in range(times_n):
            r = m["roles"][i]
            if m["semantic_key"] in per_time[i][1]:
                r = "anchor_today"
            roles.append(r)
        role = "anchor_today" if all(r == "anchor_today" for r in roles) else max(
            roles, key=lambda r: ROLE_ORDER.get(r, 3))
        orbs = [o for o in m["orbs"] if o is not None]
        f = dict(m)
        f["temporal_role"] = role
        f["orb"] = max(orbs) if orbs else None
        f["strength"] = max(s for s in m["strengths"] if s is not None)
        if hard_exclude and (f["target_type"] or "") in NON_PUBLIC_TARGETS:
            n_ts += 1
            continue
        public.append(f)
    return public, n_ts


def control_times(chart: dict, mode: str) -> list[str]:
    if mode == "exact":
        return [chart["birth_time"]]
    if mode == "bucket":
        return BUCKET_GRIDS[chart["birth_time_bucket"]]
    return UNKNOWN_GRID


def run_chart_day(worker: Worker, chart: dict, mode: str, d: date) -> dict:
    t0 = time.monotonic()
    times = control_times(chart, mode)
    per_time = []
    natal_by_time: dict[str, dict] = {}
    for t in times:
        if t not in natal_by_time:
            natal_by_time[t] = worker.natal(chart, t)
        recs, trig, alt = worker.day_factors(chart, natal_by_time[t], t, d)
        per_time.append((recs, trig, alt))
    gap_h = 0.0 if mode == "exact" else CANON_GAP["unknown" if mode == "unknown" else "bucket"]
    public, n_ts = merge_public(per_time, gap_h=gap_h, hard_exclude=(mode != "exact"))
    r = H.classify_day_v2(public, 0.55, 0.5, "B", fixes=ALL_ON, trigger_keys=None)
    state = r["state"]
    if state == "single_impulse" and r.get("n_anchors", 0) == 0:
        state = "quiet_impulses"
    hero_spheres = sorted({s for g in r["hero_groups"] for s in g.get("spheres", ())})
    return {
        "status": "ok",
        "state": state,
        "n_public": len(public),
        "n_significant": r["n_significant"],
        "n_ts_excluded": n_ts,
        "tense": any(u["polarity"] == "tense" for u in r["sig_units"]),
        "hero_spheres": hero_spheres,
        "elapsed_s": round(time.monotonic() - t0, 3),
    }


# ---------------------------------------------------------------------------
# Checkpoint IO + worker entry
# ---------------------------------------------------------------------------
def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False))
    os.replace(tmp, path)


def _checkpoint_path(run_dir: Path, chart_id: str, mode: str, d: date) -> Path:
    return run_dir / "checkpoints" / chart_id / mode / f"{d.isoformat()}.json"


def _log_failure(run_dir: Path, entry: dict) -> None:
    path = run_dir / "failures.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


_WORKER: Worker | None = None


def _init_worker(sidecar_url: str) -> None:
    global _WORKER
    _WORKER = Worker(sidecar_url)


def _process_chart(task: dict) -> dict:
    chart, mode_dates, run_dir = task["chart"], task["mode_dates"], Path(task["run_dir"])
    assert _WORKER is not None
    timings0 = dict(_WORKER.timings)
    calls0 = dict(_WORKER.call_counts)
    done = failed = skipped = 0
    for mode, dates in mode_dates.items():
        for d in dates:
            cp = _checkpoint_path(run_dir, chart["chart_id"], mode, d)
            if cp.exists():
                try:
                    if json.loads(cp.read_text()).get("status") == "ok":
                        skipped += 1
                        continue
                except Exception:
                    pass
            t0 = time.monotonic()
            try:
                rec = run_chart_day(_WORKER, chart, mode, d)
                rec.update({"chart_id": chart["chart_id"], "mode": mode, "date": d.isoformat()})
                done += 1
            except Exception as exc:  # noqa: BLE001
                rec = {"chart_id": chart["chart_id"], "mode": mode, "date": d.isoformat(),
                       "status": "error", "error_type": type(exc).__name__,
                       "error": str(exc)[:300]}
                failed += 1
                _log_failure(run_dir, {**rec, "worker": os.getpid()})
            _atomic_write(cp, rec)
    return {
        "chart_id": chart["chart_id"], "done": done, "failed": failed, "skipped": skipped,
        "elapsed_s": round(time.monotonic() - t0 if (done or failed) else 0.0, 2),
        "timings": {k: _WORKER.timings.get(k, 0.0) - timings0.get(k, 0.0)
                    for k in set(_WORKER.timings) | set(timings0)},
        "call_counts": {k: _WORKER.call_counts.get(k, 0) - calls0.get(k, 0)
                        for k in set(_WORKER.call_counts) | set(calls0)},
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def aggregate(run_dir: Path) -> dict:
    cps = sorted(run_dir.glob("checkpoints/*/*/*.json"))
    recs = []
    for cp in cps:
        try:
            recs.append(json.loads(cp.read_text()))
        except Exception:
            continue
    ok = [r for r in recs if r.get("status") == "ok"]
    errors = [r for r in recs if r.get("status") == "error"]
    modes: dict[str, dict] = {}
    for mode in sorted({r["mode"] for r in ok}):
        rows = [r for r in ok if r["mode"] == mode]
        states = Counter(r["state"] for r in rows)
        sig = [r["n_significant"] for r in rows]
        pub = [r["n_public"] for r in rows]
        ts = [r["n_ts_excluded"] for r in rows]
        hero_days = sum(1 for r in rows if r["state"] == "hero")
        # tense streaks on selected (public significant) units, per chart
        max_streaks = []
        by_chart: dict[str, list] = {}
        for r in rows:
            by_chart.setdefault(r["chart_id"], []).append(r)
        for chart_rows in by_chart.values():
            chart_rows.sort(key=lambda r: r["date"])
            cur = best = 0
            for r in chart_rows:
                cur = cur + 1 if r["tense"] else 0
                best = max(best, cur)
            max_streaks.append(best)
        spheres = Counter(s for r in rows for s in r["hero_spheres"])
        modes[mode] = {
            "chart_days": len(rows),
            "charts": len(by_chart),
            "state_distribution": dict(states),
            "hero_rate": round(hero_days / max(len(rows), 1), 4),
            "median_significant": statistics.median(sig),
            "p90_significant": round(H.percentile(sig, 0.9), 1),
            "median_public": statistics.median(pub),
            "median_ts_excluded": statistics.median(ts),
            "tense_day_share": round(sum(1 for r in rows if r["tense"]) / max(len(rows), 1), 3),
            "tense_streak_max_over_charts": max(max_streaks) if max_streaks else 0,
            "tense_streak_median_over_charts": statistics.median(max_streaks) if max_streaks else 0,
            "hero_sphere_distribution": dict(spheres),
        }
    return {
        "checkpoints_ok": len(ok),
        "checkpoints_error": len(errors),
        "error_types": dict(Counter(r.get("error_type") for r in errors)),
        "modes": modes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _daterange(a: date, b: date) -> list[date]:
    out = []
    while a <= b:
        out.append(a)
        a += timedelta(days=1)
    return out


def cmd_run(args: argparse.Namespace) -> int:
    manifest = json.loads(Path(args.manifest).read_text())
    charts = manifest["charts"]
    if args.charts:
        wanted = set(args.charts.split(","))
        charts = [c for c in charts if c["chart_id"] in wanted]
    charts = sorted(charts, key=lambda c: c["chart_id"])
    if not charts:
        print("no charts selected")
        return 1
    dates = _daterange(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to))
    modes = args.modes.split(",")
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for i, chart in enumerate(charts):
        if i % args.workers != (args.shard or 0) and args.shards:
            continue
        tasks.append({
            "chart": chart,
            "mode_dates": {m: dates for m in modes},
            "run_dir": str(run_dir),
        })
    print(f"[run] charts={len(tasks)} days={len(dates)} modes={modes} workers={args.workers} run_dir={run_dir}")

    t0 = time.monotonic()
    results = []
    if args.workers <= 1:
        _init_worker(args.sidecar_url)
        for t in tasks:
            r = _process_chart(t)
            results.append(r)
            print(f"  [chart] {r['chart_id']}: done={r['done']} failed={r['failed']} skipped={r['skipped']}")
    else:
        with Pool(args.workers, initializer=_init_worker, initargs=(args.sidecar_url,)) as pool:
            for r in pool.imap_unordered(_process_chart, tasks):
                results.append(r)
                print(f"  [chart] {r['chart_id']}: done={r['done']} failed={r['failed']} skipped={r['skipped']}")
    wall = time.monotonic() - t0

    agg = aggregate(run_dir)
    agg["run"] = {
        "wall_s": round(wall, 1),
        "workers": args.workers,
        "charts": len(tasks),
        "days": len(dates),
        "modes": modes,
        "sidecar_url": args.sidecar_url,
        "worker_timings_sum_s": {k: round(v, 1) for k, v in
                                Counter({k2: sum(r["timings"].get(k2, 0.0) for r in results)
                                         for k2 in {k for r in results for k in r["timings"]}}).items()},
        "call_counts": {k: int(v) for k, v in
                        Counter({k2: sum(r["call_counts"].get(k2, 0) for r in results)
                                 for k2 in {k for r in results for k in r["call_counts"]}}).items()},
    }
    (run_dir / "aggregate.json").write_text(json.dumps(agg, ensure_ascii=False, indent=1))
    print(f"[run] wall={wall:.1f}s ok={agg['checkpoints_ok']} errors={agg['checkpoints_error']} -> {run_dir/'aggregate.json'}")
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    agg = aggregate(Path(args.run_dir))
    print(json.dumps(agg, ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="W1 corpus replay runner")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--manifest", default=str(ANALYSIS / "corpus_manifest.v1.json"))
    pr.add_argument("--charts", default=None, help="comma-separated chart_id subset")
    pr.add_argument("--from", dest="date_from", required=True)
    pr.add_argument("--to", dest="date_to", required=True)
    pr.add_argument("--modes", default="exact,bucket,unknown")
    pr.add_argument("--workers", type=int, default=1)
    pr.add_argument("--shards", type=int, default=0, help="total shards (0 = in-process workers only)")
    pr.add_argument("--shard", type=int, default=0, help="this shard index (for multi-host)")
    pr.add_argument("--sidecar-url", default="http://127.0.0.1:18099")
    pr.add_argument("--run-dir", required=True)
    pa = sub.add_parser("aggregate")
    pa.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    if args.cmd == "run":
        return cmd_run(args)
    return cmd_aggregate(args)


if __name__ == "__main__":
    sys.exit(main())
