#!/usr/bin/env python3
"""Compare physical signatures: baseline vs candidate replay (spheres/facets rework).

Usage: python3 docs/work/2026-08-06_spheres-and-facets-rework/compare_signatures.py \
  --baseline /var/tmp/spheres-baseline/physical_signatures.jsonl \
  --candidate /var/tmp/spheres-candidate/physical_signatures.jsonl

Invariant (master TZ 00, §10.5): on identical physical inputs these fields must
match byte-for-byte: group ids + members, hero anchor/confirmation, hero
evidence level, group polarity, dayTone, state.
Allowed delta: sphere/facet names, selected top-N composition, selected_spheres,
labels.

Documented exemption (2026-08-08, full-corpus run): `canonical_event_ids` may
ADD event ids in the candidate, provided every added id is listed in the
candidate row's own `unmapped_event_ids` and no id is ever removed. Rationale:
candidate `classify_day_v2` deliberately keeps unresolved (unmapped) units in
the physical replay ledger ("Keep unresolved units in significance and direct
grouping... Only the published group/selection views are fail-closed on
sphere"), while the pre-projection baseline dropped them at the unit boundary.
On the full corpus this surfaces as exactly two added ids —
act:firdar_major__PERIOD_LORD__SOUTH_NODE (15420 days) and
act:firdar_major__PERIOD_LORD__NORTH_NODE_TRUE (11859 days) — with zero
deletions and zero changes to groups/tone/state/hero. Any other canonical-id
delta is a FAIL.

Memory note: streaming fingerprint compare (~0.5GB RSS), NOT a full in-memory
load — the naive dict-of-rows version needed ~9GB for 2×525600 rows and was
OOM-killed on the 8GB dev host (2026-08-08, twice). Per-row sha256 fingerprints
are compared first; days whose canonical-id fingerprint differs get a targeted
second pass validating the exemption above.
Exit 0 = physical parity holds (exemption allowed); exit 1 = mismatch (stop).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

PHYSICAL_FIELDS = (
    "group_ids",
    "hero_anchor_ids",
    "hero_confirmation_ids",
    "hero_evidence_level",
    "dayTone",
    "state",
)


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def group_physical(row: dict) -> dict[str, tuple]:
    """Per-group physical identity: id, sorted member event ids, polarity."""
    result: dict[str, tuple] = {}
    for group in row.get("groups", []):
        gid = group.get("group_id", "")
        members = tuple(sorted(group.get("member_event_ids", []) or group.get("members", []) or []))
        result[gid] = (members, group.get("polarity"))
    return result


def row_fingerprint(row: dict) -> tuple[str, str, str, str, str]:
    """(phys_hash, events_hash, sphere_hash, selection_hash, unmapped_hash)."""
    phys = {field: row.get(field) for field in PHYSICAL_FIELDS}
    phys["groups_physical"] = {
        gid: [list(members), polarity] for gid, (members, polarity) in group_physical(row).items()
    }
    sphere_sig = [g.get("spheres") for g in row.get("groups", [])]
    return (
        _digest(phys),
        _digest(sorted(row.get("canonical_event_ids", []))),
        _digest(sphere_sig),
        _digest(row.get("selected_group_ids")),
        _digest(sorted(row.get("unmapped_event_ids", []) or [])),
    )


def load_fingerprints(path: str) -> dict[tuple[str, str, str], tuple[str, str, str, str, str]]:
    rows: dict[tuple[str, str, str], tuple[str, str, str, str, str]] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = (row["chart_id"], row["birth_mode"], row["target_date"])
            rows[key] = row_fingerprint(row)
    return rows


def fetch_event_sets(
    path: str, wanted: set[tuple[str, str, str]]
) -> dict[tuple[str, str, str], tuple[set[str], set[str]]]:
    """Second-pass fetch of (canonical_event_ids, unmapped_event_ids) for given days."""
    found: dict[tuple[str, str, str], tuple[set[str], set[str]]] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not wanted:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = (row["chart_id"], row["birth_mode"], row["target_date"])
            if key in wanted:
                found[key] = (
                    set(row.get("canonical_event_ids", [])),
                    set(row.get("unmapped_event_ids", []) or []),
                )
                wanted.discard(key)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()

    baseline = load_fingerprints(args.baseline)
    candidate = load_fingerprints(args.candidate)

    only_baseline = sorted(set(baseline) - set(candidate))
    only_candidate = sorted(set(candidate) - set(baseline))
    common = sorted(set(baseline) & set(candidate))

    physical_mismatch_keys: list[tuple[str, str, str]] = []
    event_diff_keys: list[tuple[str, str, str]] = []
    sphere_changes = 0
    selection_changes = 0

    for key in common:
        base_phys, base_events, base_sphere, base_sel, _ = baseline[key]
        cand_phys, cand_events, cand_sphere, cand_sel, _ = candidate[key]
        if base_phys != cand_phys:
            physical_mismatch_keys.append(key)
        if base_events != cand_events:
            event_diff_keys.append(key)
        if base_sphere != cand_sphere:
            sphere_changes += 1
        if base_sel != cand_sel:
            selection_changes += 1

    print(f"days compared: {len(common)}")
    print(f"only in baseline: {len(only_baseline)}  only in candidate: {len(only_candidate)}")
    print(f"physical mismatches (groups/tone/state/hero): {len(physical_mismatch_keys)}")
    print(f"canonical_event_ids diff days: {len(event_diff_keys)}")
    print(f"allowed-delta days: sphere/projection changes={sphere_changes}, selection changes={selection_changes}")

    fail = False
    if only_baseline or only_candidate:
        print("FAIL: day sets differ")
        fail = True
    if physical_mismatch_keys:
        print("FAIL: physical fields changed — product projection touched the formula (forbidden)")
        for key in physical_mismatch_keys[:5]:
            print("MISMATCH:", json.dumps({"key": key}, ensure_ascii=False)[:400])
        fail = True

    exempted_days = 0
    if event_diff_keys:
        wanted = set(event_diff_keys)
        base_sets = fetch_event_sets(args.baseline, set(wanted))
        cand_sets = fetch_event_sets(args.candidate, set(wanted))
        from collections import Counter

        added_ids: Counter[str] = Counter()
        violations: list[dict] = []
        for key in event_diff_keys:
            base_events, _ = base_sets.get(key, (set(), set()))
            cand_events, cand_unmapped = cand_sets.get(key, (set(), set()))
            removed = base_events - cand_events
            added = cand_events - base_events
            added_ids.update(added)
            if removed or not added <= cand_unmapped:
                violations.append(
                    {
                        "key": key,
                        "removed": sorted(removed)[:3],
                        "added_not_unmapped": sorted(added - cand_unmapped)[:3],
                    }
                )
        if violations:
            print(f"FAIL: {len(violations)} days violate the unmapped-additions exemption")
            for v in violations[:5]:
                print("VIOLATION:", json.dumps(v, ensure_ascii=False)[:400])
            fail = True
        else:
            exempted_days = len(event_diff_keys)
            print(f"exemption applied: {exempted_days} days, additions only, all in candidate unmapped_event_ids")
            for event_id, count in added_ids.most_common():
                print(f"  +{event_id}: {count} days")

    if fail:
        return 1
    if exempted_days:
        print("PASS: physical parity baseline==candidate (with documented unmapped-ledger exemption)")
    else:
        print("PASS: physical parity baseline==candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
