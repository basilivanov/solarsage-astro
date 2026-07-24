# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LLM_ELECTION
# ROLE: Unit tests for LLM election narrative validation
# DEPENDENCIES: pytest, app.schemas.election, app.services.llm.election
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-LLM-ELECTION
# purpose: Test validate_election_narrative schema and date boundary enforcement.
# owns:
#   - apps/api/tests/test_llm_election.py
# inputs: narrative dicts
# outputs: pytest assertions
# END_MODULE_CONTRACT: M-TEST-LLM-ELECTION

import pytest
from app.schemas.election import validate_election_narrative


def test_validate_election_narrative_valid() -> None:
    data = {
        "hero_reason": "Причина 1",
        "hero_personal": "Персональная 1",
        "hero_plain": "Простыми словами 1",
        "hero_hours": "Лучшие часы 1",
        "day_notes": [
            {"date": "2026-08-01", "note": "Заметка 1"},
            {"date": "2026-08-02", "note": "Заметка 2"},
        ],
        "avoid_notes": [
            {"date": "2026-08-05", "note": "Избегать 1"},
        ],
    }

    res = validate_election_narrative(
        data,
        expected_best_dates=["2026-08-01", "2026-08-02"],
        expected_avoid_dates=["2026-08-05"],
    )
    assert res.hero_reason == "Причина 1"
    assert len(res.day_notes) == 2


def test_validate_election_narrative_mismatched_dates() -> None:
    data = {
        "hero_reason": "Причина 1",
        "hero_personal": "Персональная 1",
        "hero_plain": "Простыми словами 1",
        "hero_hours": "Лучшие часы 1",
        "day_notes": [
            {"date": "2026-08-01", "note": "Заметка 1"},
        ],
        "avoid_notes": [],
    }

    with pytest.raises(ValueError, match="day_notes dates"):
        validate_election_narrative(
            data,
            expected_best_dates=["2026-08-01", "2026-08-02"],
            expected_avoid_dates=[],
        )
