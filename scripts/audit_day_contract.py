#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_DAY_CONTRACT — one-command day contract check.
# ROLE: Fetches /api/day/{date} for a user and validates the new day contract
#       (valence assessments, breakdown, versions, relative status) with
#       invariant exit codes. Replaces manual curl inspection.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-DAY-CONTRACT
# purpose: Print the day payload per the new contract and assert invariants.
# owns:
#   - scripts/audit_day_contract.py
# inputs: --tg-id, --date, --api (default http://127.0.0.1:8000), --freeze PATH.
# outputs: human-readable contract dump, invariant report, exit 0/1; optional
#          frozen fixture JSON for regression tests.
# dependencies: scripts/generate-telegram-test-initdata.py, urllib, json.
# side_effects: HTTP calls to the API; optional fixture write.
# emitted_logs: none.
# invariants checked (exit 1 on any failure):
#   - counts == 12 rows and verdict counts sum to 12;
#   - dayStatusBreakdown present and rule consistent with day status;
#   - not all 12 (support,tension) pairs identical (map-to-all regression);
#   - every row carries assessment (when --expect-valence);
#   - relativeStatus present with sane baseline in valence scale;
#   - details (when present) have story+advice, no banned astro jargon;
#   - meta.payloadVersion present.
# failure_policy: exit 2 on transport/auth failure.
# END_MODULE_CONTRACT

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from collections import Counter

BANNED_JARGON = ("транзит", "аспект", "орб", "натал", "планет", "профекц", "фирдар")


def fail(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(2)


def init_data(tg_id: int, username: str) -> str:
    out = subprocess.run(
        ["python3", "scripts/generate-telegram-test-initdata.py", f"--user-id={tg_id}", f"--username={username}"],
        capture_output=True, text=True, cwd=_repo_root(),
    )
    if out.returncode != 0:
        fail(f"initData generation failed: {out.stderr[:200]}")
    for line in out.stdout.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            return line
    fail("initData parse failed")


def _repo_root() -> str:
    import os
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch_day(api: str, tg_id: int, username: str, day: str) -> dict:
    raw = init_data(tg_id, username)
    req = urllib.request.Request(
        f"{api}/api/auth/telegram",
        data=json.dumps({"initData": raw}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except Exception as exc:  # noqa: BLE001
        fail(f"auth failed: {exc}")
    cookie = resp.headers.get("Set-Cookie", "").split(";")[0]
    req2 = urllib.request.Request(f"{api}/api/day/{day}", headers={"Cookie": cookie})
    try:
        return json.load(urllib.request.urlopen(req2, timeout=240))
    except Exception as exc:  # noqa: BLE001
        fail(f"day fetch failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day contract audit: print + invariant check")
    parser.add_argument("--tg-id", type=int, required=True)
    parser.add_argument("--username", default="basil_ivanov")
    parser.add_argument("--date", required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--expect-valence", action="store_true", default=True)
    parser.add_argument("--freeze", default=None, help="write sanitized payload JSON to this path")
    args = parser.parse_args()

    d = fetch_day(args.api, args.tg_id, args.username, args.date)
    rows = (d.get("concreteAdvice") or {}).get("rows") or []
    audit = (d.get("v2") or {}).get("audit") or {}
    breakdown = audit.get("dayStatusBreakdown")
    rel = d.get("relativeStatus")
    meta = d.get("meta") or {}
    focus = d.get("focus") or {}

    print(f"== DAY {args.date} ==")
    print(f"versions: scoring={audit.get('scoringVersion')} payload={meta.get('payloadVersion')} valence={audit.get('valenceVersion')} content={meta.get('contentVersion')}")
    print(f"dayStatus: {d.get('dayStatus')}")
    if focus:
        conv = focus.get("convergence") or {}
        events = focus.get("events") or []
        print(f"focus: state={focus.get('state')} contentState={focus.get('contentState')} convTheme={conv.get('themeKey')} convFactors={conv.get('independentFactorCount')}")
        print(f"focus events ({len(events)}):")
        for ev in events:
            occurs = ev.get("occursAt") or ev.get("occurs_at") or "null"
            print(f"  - {ev.get('id'):35s} kind={ev.get('kind'):6s} time={occurs} title={ev.get('humanTitle')!r}")
    else:
        print("focus: MISSING")
    if breakdown:
        print(
            "breakdown: support={supportScore:.3f} tension={tensionScore:.3f} rule={rule} "
            "factors={factorCount} effective={effectiveFactorCount} dup={duplicateFactorCount}".format(**breakdown)
        )
        fam = breakdown.get("familyCounts") or {}
        if fam:
            print("familyCounts: " + " ".join(f"{k}={v}" for k, v in fam.items()))
    else:
        print("breakdown: MISSING")
    if rel:
        bl = rel.get("baseline") or {}
        print(
            f"relativeStatus: mode={rel.get('mode')} status={rel.get('status')} label={rel.get('label')!r} "
            f"zS={rel.get('zSupport')} zT={rel.get('zTension')} days={bl.get('days')} "
            f"supMean={bl.get('supportMean')} tenMean={bl.get('tensionMean')}"
        )
    else:
        print("relativeStatus: MISSING")

    print("\nspheres:")
    for r in rows:
        a = (r.get("assessment") or {}).get("assessment") or {}
        det = r.get("details") or {}
        print(
            f"  {r['key']:15s} {r['verdict']:8s} sup={a.get('supportScore', 0):5.2f} ten={a.get('tensionScore', 0):5.2f} "
            f"bal={a.get('balance', 0):+5.2f} rule={a.get('verdictRule', '?'):22s} conf={a.get('confidence', '?'):6s} "
            f"details={'yes' if det else 'no'}"
        )

    # ---------------- invariants ----------------
    problems: list[str] = []

    counts = Counter(r["verdict"] for r in rows)
    if len(rows) != 12 or sum(counts.values()) != 12:
        problems.append(f"counts broken: rows={len(rows)} sum={sum(counts.values())}")

    if not breakdown:
        problems.append("dayStatusBreakdown missing")
    else:
        status = d.get("dayStatus")
        sup, ten = breakdown.get("supportScore", 0), breakdown.get("tensionScore", 0)
        if status == "tense" and not (ten >= 1.0 and ten > sup * 1.3):
            problems.append(f"status tense but breakdown inconsistent: sup={sup} ten={ten}")
        if status == "supportive" and not (sup >= 1.0 and sup > ten * 1.3):
            problems.append(f"status supportive but breakdown inconsistent: sup={sup} ten={ten}")
        if status == "steady" and not breakdown.get("rule"):
            problems.append("steady status with empty rule")

    pairs = {(round((r.get("assessment") or {}).get("assessment", {}).get("supportScore", 0), 3),
              round((r.get("assessment") or {}).get("assessment", {}).get("tensionScore", 0), 3)) for r in rows}
    if len(rows) == 12 and len(pairs) == 1:
        problems.append("all 12 spheres have identical support/tension (map-to-all regression)")

    if args.expect_valence and any(r.get("assessment") is None for r in rows):
        problems.append("some rows miss assessment while valence expected")

    if not rel:
        problems.append("relativeStatus missing")
    else:
        bl = rel.get("baseline") or {}
        if rel.get("mode") == "relative" and (bl.get("days", 0) < 5 or bl.get("supportStd", 0) <= 0):
            problems.append(f"relative mode with broken baseline: {bl}")
        for m in (rel.get("supportMarker"), rel.get("tensionMarker")):
            if m is None or not (0.0 <= m <= 1.0):
                problems.append(f"marker out of [0,1]: {m}")

    for r in rows:
        det = r.get("details")
        if not det:
            continue
        if not (det.get("story") or "").strip() or not (det.get("advice") or "").strip():
            problems.append(f"{r['key']}: details without story/advice")
        hay = " ".join([det.get("story", ""), det.get("advice", ""), *(det.get("why") or [])]).lower()
        hit = next((w for w in BANNED_JARGON if w in hay), None)
        if hit:
            problems.append(f"{r['key']}: banned jargon '{hit}' in details")
        if len(det.get("why") or []) > 2:
            problems.append(f"{r['key']}: more than 2 why lines")

    if not meta.get("payloadVersion"):
        problems.append("meta.payloadVersion missing")

    # Sanitized Focus invariants (§6.2, §8.2 amendment)
    if not focus:
        problems.append("focus section missing")
    else:
        st = focus.get("state")
        cst = focus.get("contentState")
        evs = focus.get("events") or []
        if st not in ("convergence_today", "single_impulses", "background_only", "no_accent", "unavailable"):
            problems.append(f"invalid focus.state: {st}")
        if len(evs) > 3:
            problems.append(f"focus.events count exceeds cap 3: {len(evs)}")
        for ev in evs:
            if not ev.get("id") or not str(ev.get("id")).startswith("ev:"):
                problems.append(f"invalid focus event id format: {ev.get('id')}")
            src_ids = ev.get("sourceActivationIds") or ev.get("source_activation_ids") or []
            if not src_ids:
                problems.append(f"focus event missing sourceActivationIds: {ev.get('id')}")

    print("\n== INVARIANTS ==")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        print(f"\nRESULT: FAIL ({len(problems)} invariant violations)")
        sys.exit(1)
    print("  all invariants pass")
    print("\nRESULT: OK")

    if args.freeze:
        with open(args.freeze, "w") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        print(f"frozen -> {args.freeze}")


if __name__ == "__main__":
    main()
