#!/usr/bin/env python3
"""Compare physical signatures: baseline vs candidate replay (spheres/facets rework).

Usage: python3 docs/work/2026-08-06_spheres-and-facets-rework/compare_signatures.py \
  --baseline /var/tmp/spheres-baseline/physical_signatures.jsonl \
  --candidate /var/tmp/spheres-candidate/physical_signatures.jsonl

Invariant (master TZ 00, §10.5): on identical physical inputs these fields must
match byte-for-byte: canonical_event_ids, group ids + members, driver keys,
hero anchor/confirmation, hero evidence level, group polarity, dayTone, state.
Allowed delta: sphere/facet names, selected top-N composition where the old
diversity gate dropped a signal, selected_spheres, labels.
Exit 0 = physical parity holds; exit 1 = mismatch (stop, per TZ).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

PHYSICAL_FIELDS = (
    "canonical_event_ids",
    "group_ids",
    "hero_anchor_ids",
    "hero_confirmation_ids",
    "hero_evidence_level",
    "dayTone",
    "state",
)


def load(path: str) -> dict[tuple[str, str, str], dict]:
    rows: dict[tuple[str, str, str], dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            key = (row["chart_id"], row["birth_mode"], row["target_date"])
            rows[key] = row
    return rows


def group_physical(row: dict) -> dict[str, tuple]:
    """Per-group physical identity: id, sorted member event ids, polarity."""
    result: dict[str, tuple] = {}
    for group in row.get("groups", []):
        gid = group.get("group_id", "")
        members = tuple(sorted(group.get("member_event_ids", []) or group.get("members", []) or []))
        result[gid] = (members, group.get("polarity"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()

    baseline = load(args.baseline)
    candidate = load(args.candidate)

    only_baseline = sorted(set(baseline) - set(candidate))
    only_candidate = sorted(set(candidate) - set(baseline))
    common = sorted(set(baseline) & set(candidate))

    mismatches: Counter[str] = Counter()
    mismatch_examples: list[dict] = []
    sphere_changes = 0
    selection_changes = 0

    for key in common:
        base = baseline[key]
        cand = candidate[key]
        for field in PHYSICAL_FIELDS:
            if base.get(field) != cand.get(field):
                mismatches[field] += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append(
                        {"key": key, "field": field, "baseline": base.get(field), "candidate": cand.get(field)}
                    )
        base_groups = group_physical(base)
        cand_groups = group_physical(cand)
        if set(base_groups) != set(cand_groups):
            mismatches["group_id_set"] += 1
        else:
            for gid in base_groups:
                if base_groups[gid] != cand_groups[gid]:
                    mismatches["group_members_or_polarity"] += 1
                    break
        # allowed delta accounting (diagnostic, not a failure)
        base_spheres = [g.get("spheres") for g in base.get("groups", [])]
        cand_spheres = [g.get("spheres") for g in cand.get("groups", [])]
        if base_spheres != cand_spheres:
            sphere_changes += 1
        if base.get("selected_group_ids") != cand.get("selected_group_ids"):
            selection_changes += 1

    total_mismatch = sum(mismatches.values())
    print(f"days compared: {len(common)}")
    print(f"only in baseline: {len(only_baseline)}  only in candidate: {len(only_candidate)}")
    print(f"physical mismatches: {total_mismatch}  {dict(mismatches)}")
    print(f"allowed-delta days: sphere/projection changes={sphere_changes}, selection changes={selection_changes}")
    for example in mismatch_examples:
        print("MISMATCH:", json.dumps(example, ensure_ascii=False)[:400])

    if only_baseline or only_candidate:
        print("FAIL: day sets differ")
        return 1
    if total_mismatch:
        print("FAIL: physical fields changed — product projection touched the formula (forbidden)")
        return 1
    print("PASS: physical parity baseline==candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
