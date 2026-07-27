# ############################################################################
# AI_HEADER: TEST_FROZEN_DAY_CONTRACT — regression canaries from frozen live days.
# ROLE: Replays frozen /api/day payloads (audit-day-freeze artifacts) through
#       the core day-contract invariants so future waves catch regressions.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-FROZEN-DAY-CONTRACT
# purpose: Assert core day-contract invariants on every frozen fixture.
# owns:
#   - apps/api/tests/test_frozen_day_contract.py
# inputs: apps/api/tests/fixtures/day_valence/frozen-*.json
# outputs: pytest assertions per fixture.
# dependencies: json, pathlib, collections.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - counts == 12 and verdict counts sum to 12;
#   - dayStatusBreakdown present and consistent with dayStatus;
#   - not all 12 (support,tension) pairs identical (map-to-all regression);
#   - relativeStatus sane; details (when present) have story+advice, no jargon;
#   - fixtures with no files are skipped, not failed.
# failure_policy: test failure on invariant violation.
# END_MODULE_CONTRACT

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "day_valence"
BANNED_JARGON = ("транзит", "аспект", "орб", "натал", "планет", "профекц", "фирдар")


def _frozen_files() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("frozen-*.json"))


def _check(payload: dict, name: str) -> None:
    rows = (payload.get("concreteAdvice") or {}).get("rows") or []
    audit = (payload.get("v2") or {}).get("audit") or {}
    breakdown = audit.get("dayStatusBreakdown")
    rel = payload.get("relativeStatus")

    counts = Counter(r["verdict"] for r in rows)
    assert len(rows) == 12 and sum(counts.values()) == 12, f"{name}: counts broken {len(rows)}/{sum(counts.values())}"

    assert breakdown, f"{name}: dayStatusBreakdown missing"
    status = payload.get("dayStatus")
    sup, ten = breakdown.get("supportScore", 0), breakdown.get("tensionScore", 0)
    if status == "tense":
        assert ten >= 1.0 and ten > sup * 1.3, f"{name}: tense inconsistent sup={sup} ten={ten}"
    elif status == "supportive":
        assert sup >= 1.0 and sup > ten * 1.3, f"{name}: supportive inconsistent sup={sup} ten={ten}"

    pairs = {
        (
            round((r.get("assessment") or {}).get("assessment", {}).get("supportScore", 0), 3),
            round((r.get("assessment") or {}).get("assessment", {}).get("tensionScore", 0), 3),
        )
        for r in rows
    }
    assert len(pairs) > 1, f"{name}: all 12 spheres identical (map-to-all regression)"

    assert rel, f"{name}: relativeStatus missing"
    bl = rel.get("baseline") or {}
    if rel.get("mode") == "relative":
        assert bl.get("days", 0) >= 5 and bl.get("supportStd", 0) > 0, f"{name}: broken baseline {bl}"
    for m in (rel.get("supportMarker"), rel.get("tensionMarker")):
        assert m is not None and 0.0 <= m <= 1.0, f"{name}: marker out of range {m}"

    for r in rows:
        det = r.get("details")
        if not det:
            continue
        assert (det.get("story") or "").strip() and (det.get("advice") or "").strip(), f"{name}/{r['key']}: details without story/advice"
        hay = " ".join([det.get("story", ""), det.get("advice", ""), *(det.get("why") or [])]).lower()
        hit = next((w for w in BANNED_JARGON if w in hay), None)
        assert hit is None, f"{name}/{r['key']}: banned jargon '{hit}' in details"
        assert len(det.get("why") or []) <= 2, f"{name}/{r['key']}: more than 2 why lines"


@pytest.mark.parametrize("fixture", _frozen_files(), ids=lambda p: p.name)
def test_frozen_day_contract(fixture: Path) -> None:
    payload = json.loads(fixture.read_text())
    _check(payload, fixture.name)
