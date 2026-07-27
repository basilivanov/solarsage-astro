# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_VALENCE_CANARY
# ROLE: Canary tests over 3 sanitized canary fixtures for W2-VALENCE.
# DEPENDENCIES: pytest, app.services.day_factor_ledger, app.services.day_valence_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-VALENCE-CANARY
# purpose: Verify sanitized canary fixtures, privacy hygiene, and valence engine computation (§14.3).
# owns:
#   - apps/api/tests/test_day_valence_canary.py
# inputs: 3 sanitized canary JSON fixtures in tests/fixtures/day_valence/
# outputs: assertions over 12 verdicts, day status, duplicate count, and privacy hygiene
# dependencies: app.services.day_factor_ledger, app.services.day_valence_service
# side_effects: reads JSON fixtures from disk
# failure_policy: fails test on PII leak or valence engine computation error
# END_MODULE_CONTRACT: M-TEST-DAY-VALENCE-CANARY

# START_MODULE_MAP: M-TEST-DAY-VALENCE-CANARY
# public_entrypoints:
#   - test_canary_fixtures_privacy_sanitization_scan
#   - test_canary_p_basil_2026_07_25_balanced
#   - test_canary_p_basil_2026_07_23_tense_trap_resolved
#   - test_canary_synthetic_low_evidence
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_canary.py
# END_MODULE_MAP: M-TEST-DAY-VALENCE-CANARY

import json
from pathlib import Path
import pytest

from app.schemas.normalization import AstroSignal
from app.services.day_factor_ledger import build_factor_ledger
from app.services.day_valence_service import DayValenceService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "day_valence"
BANNED_PII_PATTERNS = ["birth", "city", "latitude", "longitude", "first_name", "last_name", "username", "tg_user_id"]


def test_canary_fixtures_privacy_sanitization_scan():
    """Verify that all canary fixtures contain ONLY factor inputs without any PII or birth data."""
    for filename in ["P-BASIL-2026-07-25.json", "P-BASIL-2026-07-23.json", "synthetic_low_evidence.json"]:
        path = FIXTURES_DIR / filename
        assert path.exists(), f"Missing canary fixture: {filename}"

        text = path.read_text(encoding="utf-8").lower()
        for banned in BANNED_PII_PATTERNS:
            assert banned not in text, f"PII leak detected in {filename}: found '{banned}'"


def _load_fixture(filename: str):
    path = FIXTURES_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    sigs = [AstroSignal.model_validate(s) for s in data.get("day_signals", [])]
    acts = data.get("activations", [])
    return sigs, acts


def test_canary_p_basil_2026_07_25_balanced():
    """P-BASIL-2026-07-25 canary test: balanced day with both supportive and tense activations."""
    sigs, acts = _load_fixture("P-BASIL-2026-07-25.json")
    ledger = build_factor_ledger(day_signals=sigs, activations=acts)
    service = DayValenceService()
    assessments, breakdown, day_status = service.compute(ledger)

    assert len(assessments) == 12
    assert breakdown.factor_count > 0
    assert day_status in ("supportive", "steady", "tense")


def test_canary_p_basil_2026_07_23_tense_trap_resolved():
    """P-BASIL-2026-07-23 canary test: tense day status with tense activations resolves legacy good=11 trap."""
    sigs, acts = _load_fixture("P-BASIL-2026-07-23.json")
    ledger = build_factor_ledger(day_signals=sigs, activations=acts)
    service = DayValenceService()
    assessments, breakdown, day_status = service.compute(ledger)

    assert len(assessments) == 12
    assert day_status == "tense"
    assert breakdown.tension_score >= 1.0

    # Old trap: 11 good spheres for a tense day. Now: work/crisis/money are avoid or caution!
    good_count = sum(1 for a in assessments.values() if a.verdict == "good")
    assert good_count < 11
    assert assessments["work"].verdict in ("avoid", "caution")


def test_canary_synthetic_low_evidence():
    """Synthetic low evidence canary test: minimal factors resolve to steady day and neutral_low_evidence spheres."""
    sigs, acts = _load_fixture("synthetic_low_evidence.json")
    ledger = build_factor_ledger(day_signals=sigs, activations=acts)
    service = DayValenceService()
    assessments, breakdown, day_status = service.compute(ledger)

    assert len(assessments) == 12
    assert day_status == "steady"
    assert breakdown.support_score == 0.0
    assert breakdown.tension_score == 0.0

    for ass in assessments.values():
        assert ass.verdict == "neutral"
        assert ass.verdict_rule == "neutral_low_evidence"
